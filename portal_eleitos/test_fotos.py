"""Exportação retomável com artefatos sintéticos e sem acesso à rede."""

import hashlib
import json
import zipfile

import pytest

from portal_eleitos.fotos import executar_fotos, main


@pytest.fixture
def ambiente(tmp_path):
    documentos = tmp_path / "dados"
    documentos.mkdir()
    url = "https://resultados.tse.jus.br/oficial/ele2022/544/fotos/ac/100.jpeg"
    candidato = {"sequencial_tse": "100", "foto": {"fonte_tse": url}}
    cargo = {"fonte": {"eleicao": 544, "cargo": 7, "abrangencia": "AC"}, "eleitos": [candidato]}
    (documentos / "AC.json").write_text(json.dumps({"cargos": [cargo]}))
    (documentos / "BR.json").write_text(json.dumps({"cargos": []}))
    manifesto = documentos / "manifesto.json"
    manifesto.write_text(
        json.dumps(
            {
                "versao_schema": 1,
                "revisao": "teste",
                "territorios": {
                    "AC": "AC.json",
                    "BR": "BR.json",
                },
            }
        )
    )
    modelo = tmp_path / "modelo.onnx"
    modelo.write_bytes(b"modelo sintetico")
    chamadas = {"baixadas": 0, "processadas": 0}

    def baixar(url, destino, *, timeout):
        chamadas["baixadas"] += 1
        destino.write_bytes(b"original sintetico")

    def processar(original, destino_dir, modelo, **parametros):
        chamadas["processadas"] += 1
        conteudo = original.read_bytes() + json.dumps(parametros, sort_keys=True).encode()
        sha = hashlib.sha256(conteudo).hexdigest()
        pasta = destino_dir / "fotos"
        pasta.mkdir(exist_ok=True)
        (pasta / f"{sha}.webp").write_bytes(conteudo)
        return {
            "estado": "disponivel",
            "url": f"fotos/{sha}.webp",
            "sha256": sha,
            "largura": parametros["tamanho"],
            "altura": parametros["tamanho"],
            "formato": "webp",
            "local": {"rosto": {"x": 42}, "segredo": "somente-local"},
            "segredo": "nao-publicar",
        }

    return manifesto, tmp_path / "saida", modelo, chamadas, baixar, processar


def executar(ambiente, **kwargs):
    manifesto, saida, modelo, _, baixar, processar = ambiente
    return executar_fotos(manifesto, saida, modelo, baixador=baixar, processador=processar, **kwargs)


def test_retomada_mapa_zip_e_progresso(ambiente, capsys):
    resultado = executar(ambiente)
    foto = resultado["fotos"]["544:AC:100"]
    assert foto["estado"] == "disponivel"
    assert foto["fonte_tse"].endswith("100.jpeg")
    assert "local" not in foto and "segredo" not in foto
    assert executar(ambiente) == resultado
    assert ambiente[3] == {"baixadas": 1, "processadas": 1}
    saida = ambiente[1]
    assert json.loads((saida / "mapa-fotos.json").read_text()) == resultado
    registros = [json.loads(linha) for linha in (saida / "estado-fotos.jsonl").read_text().splitlines()]
    assert any(registro["etapa"] == "baixada" for registro in registros)
    assert any(registro.get("resultado", {}).get("local") for registro in registros)
    with zipfile.ZipFile(saida / "fotos.zip") as arquivo:
        assert set(arquivo.namelist()) == {foto["url"], "manifesto-fotos.json", "erros-fotos.json"}
        assert b"somente-local" not in arquivo.read("manifesto-fotos.json")
        assert b"nao-publicar" not in arquivo.read("manifesto-fotos.json")
    progresso = capsys.readouterr().err
    assert "1/1 (100%" in progresso and "/s" in progresso and "ETA" in progresso
    assert "ignoradas=1" in progresso and "falhas=0" in progresso


@pytest.mark.parametrize("alteracao", ["qualidade", "modelo", "override", "variante"])
def test_invalida_variante_sem_baixar_original(ambiente, alteracao):
    resultado = executar(ambiente)
    kwargs = {}
    if alteracao == "qualidade":
        kwargs["qualidade"] = 80
    elif alteracao == "modelo":
        ambiente[2].write_bytes(b"outro modelo")
    elif alteracao == "override":
        arquivo = ambiente[1] / "overrides.json"
        arquivo.write_text(json.dumps({"544:AC:100": {"x": 1}}))
        kwargs["overrides"] = arquivo
    else:
        (ambiente[1] / resultado["fotos"]["544:AC:100"]["url"]).write_bytes(b"corrompida")
    executar(ambiente, **kwargs)
    assert ambiente[3] == {"baixadas": 1, "processadas": 2}


def test_original_corrompido_rebaixado_quando_reprocessa(ambiente):
    executar(ambiente)
    next((ambiente[1] / "originais").glob("*.jpg")).write_bytes(b"corrompido")
    executar(ambiente, tamanho=300)
    assert ambiente[3] == {"baixadas": 2, "processadas": 2}


def test_falha_conversao_preserva_download_para_retomada(ambiente):
    def falhar(*args, **kwargs):
        raise ValueError("imagem ilegível")

    manifesto, saida, modelo, _, baixar, _ = ambiente
    resultado = executar_fotos(manifesto, saida, modelo, baixador=baixar, processador=falhar)
    assert resultado["fotos"]["544:AC:100"]["estado"] == "erro"
    assert resultado["fotos"]["544:AC:100"]["url"] is None
    executar(ambiente)
    assert ambiente[3]["baixadas"] == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://resultados.tse.jus.br/oficial/ele2022/544/fotos/ac/100.jpeg",
        "https://resultados.tse.jus.br.evil.test/oficial/ele2022/544/fotos/ac/100.jpeg",
        "https://resultados.tse.jus.br/oficial/ele2022/544/fotos/ac/../100.jpeg",
        "https://resultados.tse.jus.br/oficial/ele2022/544/fotos/ac/100.jpeg?token=segredo",
        "https://resultados.tse.jus.br/oficial/ele2022/544/fotos/ac/200.jpeg",
    ],
)
def test_url_insegura_sem_download(ambiente, url):
    caminho = ambiente[0].parent / "AC.json"
    documento = json.loads(caminho.read_text())
    documento["cargos"][0]["eleitos"][0]["foto"]["fonte_tse"] = url
    caminho.write_text(json.dumps(documento))
    assert executar(ambiente)["fotos"]["544:AC:100"]["estado"] == "erro"
    assert ambiente[3]["baixadas"] == 0


def test_manifesto_traversal_rejeitado(ambiente):
    manifesto = ambiente[0]
    manifesto.write_text(json.dumps({"versao_schema": 1, "territorios": {"AC": "../fora.json"}}))
    with pytest.raises(ValueError, match="caminho"):
        executar(ambiente)
    assert ambiente[3]["baixadas"] == 0


def test_modelo_ausente_preflight(ambiente):
    ambiente[2].unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        executar(ambiente)
    assert ambiente[3]["baixadas"] == 0


def test_download_falha_bounded(ambiente):
    tentativas = []

    def falhar(url, destino, *, timeout):
        tentativas.append(url)
        destino.write_bytes(b"parcial")
        raise TimeoutError("sem conexão")

    manifesto, saida, modelo, _, _, processar = ambiente
    resultado = executar_fotos(manifesto, saida, modelo, baixador=falhar, processador=processar)
    assert len(tentativas) == 2
    assert resultado["fotos"]["544:AC:100"]["url"] is None
    assert not list((saida / "originais").glob("*.jpg"))
    assert not list((saida / "originais").glob(".foto-*"))


def test_cli_interrupcao(ambiente, monkeypatch):
    def interromper(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("portal_eleitos.fotos.executar_fotos", interromper)
    assert main([str(ambiente[0]), str(ambiente[1]), str(ambiente[2])]) == 130


def test_nacional_e_cargo_sem_fonte(ambiente):
    caminho = ambiente[0].parent / "BR.json"
    caminho.write_text(
        json.dumps(
            {
                "cargos": [
                    {
                        "eleicao": 545,
                        "eleitos": [
                            {
                                "sequencial_tse": "200",
                                "foto": {
                                    "fonte_tse": "https://resultados.tse.jus.br/oficial/ele2022/545/fotos/br/200.jpeg"
                                },
                            },
                        ],
                    }
                ]
            }
        )
    )
    assert set(executar(ambiente)["fotos"]) == {"544:AC:100", "545:BR:200"}


def test_retomada_apos_linha_parcial(ambiente):
    resultado = executar(ambiente)
    estado = ambiente[1] / "estado-fotos.jsonl"
    with estado.open("a") as arquivo:
        arquivo.write('{"chave":')
    assert executar(ambiente) == resultado
    executar(ambiente, qualidade=80)
    assert ambiente[3] == {"baixadas": 1, "processadas": 2}


def test_original_symlink_nao_sobrescreve_destino(ambiente, tmp_path):
    executar(ambiente)
    original = next((ambiente[1] / "originais").glob("*.jpg"))
    externo = tmp_path / "externo.jpg"
    externo.write_bytes(b"nao sobrescrever")
    original.unlink()
    original.symlink_to(externo)
    mapa = executar(ambiente, qualidade=80)
    assert mapa["fotos"]["544:AC:100"]["estado"] == "erro"
    assert externo.read_bytes() == b"nao sobrescrever"
    assert ambiente[3]["baixadas"] == 1


def test_preflight_webp_antes_de_download(ambiente, monkeypatch):
    features = pytest.importorskip("PIL.features")
    monkeypatch.setattr(features, "check", lambda formato: False)
    manifesto, saida, modelo, chamadas, baixar, _ = ambiente
    with pytest.raises(RuntimeError, match="WebP"):
        executar_fotos(manifesto, saida, modelo, baixador=baixar)
    assert chamadas["baixadas"] == 0


def test_url_alterada_invalida_download(ambiente):
    executar(ambiente)
    caminho = ambiente[0].parent / "AC.json"
    documento = json.loads(caminho.read_text())
    foto = documento["cargos"][0]["eleitos"][0]["foto"]
    foto["fonte_tse"] = foto["fonte_tse"].replace("ele2022", "ele2026")
    caminho.write_text(json.dumps(documento))
    executar(ambiente)
    assert ambiente[3] == {"baixadas": 2, "processadas": 2}


def test_download_maximo_e_redirecionamento_sem_rede(tmp_path, monkeypatch):
    from portal_eleitos.fotos import MAX_BYTES, baixar_foto

    class Resposta:
        def __init__(self):
            self.headers = {"Content-Length": str(MAX_BYTES + 1)}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Opener:
        def open(self, requisicao, *, timeout):
            assert 0 < timeout <= 8
            return Resposta()

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    with pytest.raises(ValueError, match="10 MiB"):
        baixar_foto("https://resultados.tse.jus.br/oficial/ele2022/544/fotos/ac/100.jpeg", tmp_path / "temporario.jpg")


def test_processador_nao_pode_anunciar_variante_fora_da_saida(ambiente):
    def inseguro(*args, **kwargs):
        return {"estado": "disponivel", "url": "../segredo.webp", "sha256": "0" * 64}

    manifesto, saida, modelo, _, baixar, _ = ambiente
    mapa = executar_fotos(manifesto, saida, modelo, baixador=baixar, processador=inseguro)
    assert mapa["fotos"]["544:AC:100"]["estado"] == "erro"
    with zipfile.ZipFile(saida / "fotos.zip") as arquivo:
        assert set(arquivo.namelist()) == {"manifesto-fotos.json", "erros-fotos.json"}
