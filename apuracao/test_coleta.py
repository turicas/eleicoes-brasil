import json
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from apuracao.adaptador2022 import Apuracao2022
from apuracao.coleta import Coletor
from apuracao.modelo import Contexto

URL = "https://exemplo.invalid/br-c0001-e000544.json"
CONTEXTO = Contexto(2022, 1, 544, 1, "br")


def resposta(dados=None, status=200, conteudo=None, retry_after=None):
    resposta_http = requests.Response()
    resposta_http.status_code = status
    resposta_http.url = URL
    resposta_http._content = (conteudo if conteudo is not None else json.dumps(dados)).encode()
    if retry_after is not None:
        resposta_http.headers["Retry-After"] = retry_after
    return resposta_http


class SessaoFalsa:
    def __init__(self, *eventos):
        self.eventos = iter(eventos)
        self.chamadas = []

    def get(self, url, **kwargs):
        self.chamadas.append((url, kwargs))
        evento = next(self.eventos)
        if isinstance(evento, BaseException):
            raise evento
        return evento


class AdaptadorComGeracao(Apuracao2022):
    def ler(self, dados):
        return replace(super().ler(dados), geracao=dados.get("idg"))


def pasta(raiz, contexto=CONTEXTO):
    return raiz / str(contexto.ano) / f"turno-{contexto.turno}" / f"cargo-{contexto.cargo}" / contexto.abrangencia


def test_busca_timeout_decimal_e_headers_adiados(tmp_path, monkeypatch):
    sessao = SessaoFalsa(resposta(conteudo='{"numero": 1.25}'))
    headers = {"User-Agent": "sintético"}
    monkeypatch.setitem(sys.modules, "extractors", SimpleNamespace(DEFAULT_HEADERS=headers))
    monkeypatch.setattr(requests, "Session", lambda: sessao)
    coletor = Coletor(tmp_path, timeout=7)
    assert coletor.buscar_json(URL) == {"numero": Decimal("1.25")}
    assert sessao.chamadas == [(URL, {"timeout": (7, 7), "headers": headers})]


@pytest.mark.parametrize(
    "evento",
    [resposta(status=429), resposta(status=500), resposta(status=503), requests.Timeout(), requests.ConnectionError()],
)
def test_retry_recupera_sem_rede_ou_espera(tmp_path, evento):
    sessao = SessaoFalsa(evento, resposta({"ok": True}))
    esperas = []
    coletor = Coletor(tmp_path, session=sessao, sleep=esperas.append)
    assert coletor.buscar_json(URL) == {"ok": True}
    assert len(sessao.chamadas) == 2
    assert len(esperas) == 1
    assert 0 <= esperas[0] <= 60
    assert all(chamada[1]["timeout"] == (30, 30) for chamada in sessao.chamadas)


@pytest.mark.parametrize("retry_after,espera", [("120", 60), ("2", 2), ("-1", 0)])
def test_retry_after_limitado(tmp_path, retry_after, espera):
    esperas = []
    sessao = SessaoFalsa(resposta(status=429, retry_after=retry_after), resposta({}))
    assert Coletor(tmp_path, session=sessao, sleep=esperas.append).buscar_json(URL) == {}
    assert esperas == [espera]


@pytest.mark.parametrize("status,tentativas", [(404, 1), (403, 1), (500, 3), (429, 3)])
def test_http_error_preserva_resposta_e_limita_tentativas(tmp_path, status, tentativas):
    sessao = SessaoFalsa(*(resposta(status=status) for _ in range(3)))
    esperas = []
    with pytest.raises(requests.HTTPError) as erro:
        Coletor(tmp_path, session=sessao, sleep=esperas.append).buscar_json(URL)
    assert erro.value.response.status_code == status
    assert len(sessao.chamadas) == tentativas
    assert len(esperas) == tentativas - 1


@pytest.mark.parametrize("erro", [requests.Timeout, requests.ConnectionError])
def test_falha_de_transporte_limitada(tmp_path, erro):
    sessao = SessaoFalsa(*(erro("falha") for _ in range(2)))
    esperas = []
    with pytest.raises(erro):
        Coletor(tmp_path, session=sessao, tentativas=2, sleep=esperas.append).buscar_json(URL)
    assert len(sessao.chamadas) == 2
    assert len(esperas) == 1


@pytest.mark.parametrize("conteudo", ["{", "[]", "null"])
def test_json_invalido_informa_url_sem_retry(tmp_path, conteudo):
    sessao = SessaoFalsa(resposta(conteudo=conteudo))
    with pytest.raises(ValueError, match=URL):
        Coletor(tmp_path, session=sessao).buscar_json(URL)
    assert len(sessao.chamadas) == 1


def test_coleta_preserva_bruto_e_historico(tmp_path, dados_2022):
    dados = {**dados_2022, "extra": {"nome": "José", "decimal": Decimal("1.25")}, "idg": "123"}
    sessao = SessaoFalsa(resposta({**dados, "extra": {"nome": "José", "decimal": 1.25}}))
    coletor = Coletor(tmp_path / "nova", session=sessao)
    adaptador = AdaptadorComGeracao(CONTEXTO)
    resultado = coletor.coletar(CONTEXTO, adaptador, URL)
    arquivos = list(pasta(coletor.raiz).glob("*.json"))
    assert len(arquivos) == 1
    assert arquivos[0].name.startswith("br-c0001-e000544")
    assert "123" in arquivos[0].stem
    texto = arquivos[0].read_text()
    assert "José" in texto
    assert '\n  "dg"' in texto
    assert json.loads(texto) == {**dados, "extra": {"nome": "José", "decimal": "1.25"}}
    assert coletor.historico(CONTEXTO, adaptador) == [resultado]


def test_validacao_nao_altera_saida_anterior(tmp_path, dados_2022):
    sessao = SessaoFalsa(resposta(dados_2022), resposta({**dados_2022, "sa": "inválido"}))
    coletor = Coletor(tmp_path, session=sessao)
    adaptador = Apuracao2022(CONTEXTO)
    anterior = coletor.coletar(CONTEXTO, adaptador, URL)
    arquivos = {arquivo: arquivo.read_bytes() for arquivo in tmp_path.rglob("*") if arquivo.is_file()}
    with pytest.raises(ValueError):
        coletor.coletar(CONTEXTO, adaptador, URL)
    assert {arquivo: arquivo.read_bytes() for arquivo in tmp_path.rglob("*") if arquivo.is_file()} == arquivos
    assert coletor.historico(CONTEXTO, adaptador) == [anterior]


def test_historico_ordena_e_deduplica_estados_repetidos(tmp_path, dados_2022):
    dados_tardios = {**dados_2022, "hg": "19:00:00", "idg": "2"}
    dados_anteriores = {**dados_2022, "idg": "1"}
    sessao = SessaoFalsa(
        resposta(dados_tardios), resposta(dados_anteriores), resposta(dados_anteriores), resposta(dados_tardios)
    )
    coletor = Coletor(tmp_path, session=sessao)
    adaptador = AdaptadorComGeracao(CONTEXTO)
    for indice in range(4):
        coletor.coletar(CONTEXTO, adaptador, f"https://exemplo.invalid/fonte-{indice}.json")
    historico = coletor.historico(CONTEXTO, adaptador)
    assert [resultado.geracao for resultado in historico] == ["1", "2"]
    assert len(list(pasta(tmp_path).glob("*.json"))) == 4
    assert len(coletor.historico(CONTEXTO, Apuracao2022(CONTEXTO))) == 2


def test_historico_json_invalido_informa_arquivo_e_recupera(tmp_path, dados_2022):
    coletor = Coletor(tmp_path, session=SessaoFalsa())
    adaptador = Apuracao2022(CONTEXTO)
    assert coletor.historico(CONTEXTO, adaptador) == []
    pasta(tmp_path).mkdir(parents=True)
    arquivo = pasta(tmp_path) / "fonte.json"
    arquivo.write_text("{")
    with pytest.raises(ValueError, match="fonte.json"):
        coletor.historico(CONTEXTO, adaptador)
    arquivo.write_text(json.dumps(dados_2022))
    assert coletor.historico(CONTEXTO, adaptador) == [adaptador.ler(dados_2022)]
    arquivo.write_text(json.dumps({**dados_2022, "sa": "inválido"}))
    with pytest.raises(ValueError, match="fonte.json"):
        coletor.historico(CONTEXTO, adaptador)


def test_historico_isola_contextos(tmp_path, dados_2022):
    coletor = Coletor(tmp_path, session=SessaoFalsa(resposta(dados_2022)))
    adaptador = Apuracao2022(CONTEXTO)
    resultado = coletor.coletar(CONTEXTO, adaptador, URL)
    for contexto in (
        replace(CONTEXTO, ano=2026),
        replace(CONTEXTO, turno=2),
        replace(CONTEXTO, cargo=3),
        replace(CONTEXTO, abrangencia="sp"),
    ):
        pasta(tmp_path, contexto).mkdir(parents=True)
        (pasta(tmp_path, contexto) / "corrompido.json").write_text("{")
    (pasta(tmp_path) / "arquivo-do-usuario.txt").write_text("preservar")
    assert coletor.historico(CONTEXTO, adaptador) == [resultado]


def test_interrupcao_remove_so_temporario_proprio(tmp_path, dados_2022, monkeypatch):
    coletor = Coletor(tmp_path, session=SessaoFalsa(resposta(dados_2022), resposta(dados_2022)))
    adaptador = Apuracao2022(CONTEXTO)
    anterior = coletor.coletar(CONTEXTO, adaptador, URL)
    arquivo_usuario = pasta(tmp_path) / "usuario.tmp"
    arquivo_usuario.write_text("não remover")
    anteriores = {arquivo: arquivo.read_bytes() for arquivo in pasta(tmp_path).iterdir()}
    temporarios = []

    def interromper(origem, destino):
        assert origem.parent == destino.parent
        assert origem not in anteriores
        assert json.loads(origem.read_text()) == dados_2022
        temporarios.append(origem)
        raise KeyboardInterrupt

    monkeypatch.setattr(Path, "replace", interromper)
    with pytest.raises(KeyboardInterrupt):
        coletor.coletar(CONTEXTO, adaptador, URL)
    assert len(temporarios) == 1
    assert not temporarios[0].exists()
    assert {arquivo: arquivo.read_bytes() for arquivo in pasta(tmp_path).iterdir()} == anteriores
    assert coletor.historico(CONTEXTO, adaptador) == [anterior]


def test_interrupcao_http_nao_retry(tmp_path):
    sessao = SessaoFalsa(KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        Coletor(tmp_path, session=sessao).buscar_json(URL)
    assert len(sessao.chamadas) == 1


@pytest.mark.parametrize("tentativas", [0, -1])
def test_tentativas_precisam_ser_positivas(tmp_path, tentativas):
    with pytest.raises(ValueError):
        Coletor(tmp_path, tentativas=tentativas)
