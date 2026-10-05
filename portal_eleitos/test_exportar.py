import json

import pytest

from portal_eleitos.exportar import exportar


def fonte():
    return {
        "ano": 2026,
        "eleicao": 6259,
        "turno": 1,
        "cargo": 3,
        "uf": "AC",
        "url": "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/ac/ac-c0003-e006259-u.json",
    }


def bruto():
    return {
        "ele": "6259",
        "t": "1",
        "f": "o",
        "tpabr": "uf",
        "cdabr": "ac",
        "dg": "05/10/2026",
        "hg": "01:00:00",
        "idg": "1",
        "tf": "s",
        "and": "f",
        "dt": "05/10/2026",
        "ht": "00:59:00",
        "carg": [
            {
                "cd": "3",
                "nv": "1",
                "nmn": "Governador",
                "agr": [
                    {
                        "par": [
                            {
                                "n": "10",
                                "sg": "PA",
                                "nm": "Partido A",
                                "cand": [
                                    {
                                        "n": "10",
                                        "sqcand": "123",
                                        "nm": "Maria José",
                                        "nmu": "MARIA JOSÉ",
                                        "vap": "100",
                                        "st": "Eleito",
                                        "e": "s",
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        ],
    }


def ler_publicacao(path):
    manifesto = json.loads(path.read_text())
    documento = json.loads((path.parent / manifesto["territorios"]["AC"]).read_text())
    return manifesto, documento


def test_exporta_snapshot_manifesto_e_proveniencia(tmp_path):
    path = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    manifesto, documento = ler_publicacao(path)
    assert manifesto["versao_schema"] == 1
    assert documento["territorio"]["codigo"] == "AC"
    eleito = documento["cargos"][0]["eleitos"][0]
    assert eleito["nome"] == "Maria José"
    assert eleito["foto"]["estado"] == "pendente"
    assert documento["cargos"][0]["fonte"]["estado_coleta"] == "sucesso"
    assert list((tmp_path / "brutos").rglob("*.json"))
    assert "BR" in manifesto["territorios"]


def test_falha_inicial_nao_ativa_manifesto(tmp_path):
    def falhar(url):
        raise OSError("offline")

    with pytest.raises(ValueError, match="última versão"):
        exportar(2026, tmp_path, fontes=[fonte()], coletar=falhar)
    assert not (tmp_path / "publicacao" / "manifesto.json").exists()


def test_falha_reusa_ultimo_valido_sem_apagar_eleito(tmp_path):
    primeira = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    manifesto, anterior = ler_publicacao(primeira)
    antigo_path = primeira.parent / manifesto["territorios"]["AC"]
    antigo = antigo_path.read_bytes()

    def falhar(url):
        raise OSError("offline")

    segunda = exportar(2026, tmp_path, fontes=[fonte()], coletar=falhar)
    novo_manifesto, novo = ler_publicacao(segunda)
    assert novo_manifesto["revisao"] != manifesto["revisao"]
    assert novo["cargos"][0]["eleitos"] == anterior["cargos"][0]["eleitos"]
    assert novo["cargos"][0]["fonte"]["estado_coleta"] == "ultima-versao-valida"
    assert antigo_path.read_bytes() == antigo


def test_mapa_fotos_so_publico_e_validado(tmp_path):
    mapa = {
        "versao_schema": 1,
        "fotos": {
            "6259:AC:123": {
                "estado": "disponivel",
                "url": "fotos/" + "a" * 64 + ".webp",
                "sha256": "a" * 64,
                "largura": 320,
                "altura": 320,
                "formato": "webp",
            }
        },
    }
    arquivo = tmp_path / "mapa.json"
    arquivo.write_text(json.dumps(mapa))
    path = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto(), fotos=arquivo)
    _, documento = ler_publicacao(path)
    assert documento["cargos"][0]["eleitos"][0]["foto"]["estado"] == "disponivel"


def test_normalizacao_invalida_nao_substitui_manifesto(tmp_path):
    path = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    snapshot = path.read_bytes()
    with pytest.raises(ValueError):
        exportar(2026, tmp_path, fontes=[{**fonte(), "uf": "SP"}], coletar=lambda url: bruto())
    assert path.read_bytes() == snapshot


def test_segundo_turno_preserva_cargos_primeiro(tmp_path):
    path = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    dados = bruto()
    dados.update(ele="6260", t="2")
    job = {
        **fonte(),
        "eleicao": 6260,
        "turno": 2,
        "url": "https://resultados.tse.jus.br/oficial/ele2026/6260/dados/ac/ac-c0003-e006260-u.json",
    }
    path = exportar(2026, tmp_path, turno=2, fontes=[job], coletar=lambda url: dados)
    _, documento = ler_publicacao(path)
    assert documento["cargos"][0]["turno"] == 2


def test_segundo_turno_pendente_idempotente(tmp_path):
    exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    dados = bruto()
    dados.update(ele="6260", t="2", tf="n", **{"and": "p"})
    dados["carg"][0]["agr"][0]["par"][0]["cand"][0]["st"] = ""
    job = {**fonte(), "eleicao": 6260, "turno": 2}
    for _ in range(2):
        path = exportar(2026, tmp_path, turno=2, fontes=[job], coletar=lambda url: dados)
    _, doc = ler_publicacao(path)
    assert [(item["cargo"]["codigo"], item["turno"]) for item in doc["cargos"]] == [(3, 1), (3, 2)]


def test_resposta_mais_antiga_nao_apaga_eleitos(tmp_path):
    exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    dados = bruto()
    dados.update(hg="00:00:00", tf="n", **{"and": "p"})
    dados["carg"][0]["agr"][0]["par"][0]["cand"][0]["st"] = ""
    path = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: dados)
    _, doc = ler_publicacao(path)
    assert len(doc["cargos"][0]["eleitos"]) == 1
    assert doc["cargos"][0]["fonte"]["estado_coleta"] == "ultima-versao-valida"


def test_mapa_fotos_atualiza_sem_refazer_http(tmp_path):
    path = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    old, _ = ler_publicacao(path)
    photo = tmp_path / "mapa.json"
    photo.write_text(json.dumps({"versao_schema": 1, "fotos": {}}))
    from portal_eleitos.exportar import atualizar_fotos

    updated = atualizar_fotos(tmp_path, photo)
    manifest, doc = ler_publicacao(updated)
    assert manifest["revisao"] != old["revisao"]
    assert len(doc["cargos"][0]["eleitos"]) == 1


def test_validacao_uma_fonte_reusa_anterior(tmp_path):
    exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: bruto())
    dados = bruto()
    dados["tf"] = "valor inválido"
    path = exportar(2026, tmp_path, fontes=[fonte()], coletar=lambda url: dados)
    _, doc = ler_publicacao(path)
    assert len(doc["cargos"][0]["eleitos"]) == 1
    assert doc["cargos"][0]["fonte"]["estado_coleta"] == "ultima-versao-valida"
