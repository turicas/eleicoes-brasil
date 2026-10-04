import json

import pytest

from apuracao.cli import cria_parser, executar, main
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada


class ColetaSimulada:
    def __init__(self, dados):
        self.dados = dados
        self.urls = []
        self.resultados = {}

    def buscar_json(self, url):
        self.urls.append(url)
        if url.endswith("ele-c.json"):
            return {
                "f": "o",
                "arq": [],
                "pl": [
                    {
                        "c": "ele2026",
                        "dt": "04/10/2026",
                        "e": [{"tp": "8", "t": "1", "cd": "6257", "abr": [{"cd": "br", "cp": [{"cd": "1"}]}]}],
                    }
                ],
            }
        raise AssertionError(url)

    def coletar(self, contexto, adaptador, url):
        self.urls.append(url)
        resultado = adaptador.ler(self.dados)
        self.resultados[contexto] = resultado
        return resultado

    def historico(self, contexto, adaptador):
        return [self.resultados[contexto]]


def test_cli_2022_publica_em_planilha_nova(dados_2022):
    coletor = ColetaSimulada(dados_2022)
    cliente = ClienteSimulado(PlanilhaSimulada())
    args = cria_parser().parse_args(["2022", "1", "presidente", "planilha-nova"])
    assert executar(args, coletor=coletor, client=cliente) == 0
    assert coletor.urls == [
        "https://resultados.tse.jus.br/oficial/ele2022/544/dados-simplificados/br/br-c0001-e000544-r.json"
    ]
    assert cliente.aberturas == ["planilha-nova"]
    assert {aba["properties"]["title"] for aba in cliente.planilha.abas.values()} == {"Presidente", "LinhaDoTempo"}


def test_impressao_nao_autentica_google(dados_2022, capsys):
    args = cria_parser().parse_args(["2022", "1", "presidente", "--print-only"])
    assert executar(args, coletor=ColetaSimulada(dados_2022)) == 0
    dados = json.loads(capsys.readouterr().out)
    assert dados[0]["contexto"] == {"ano": 2022, "turno": 1, "eleicao": 544, "cargo": 1, "abrangencia": "br"}
    assert dados[0]["candidatos"][0]["numero"] == "13"


def test_id_obrigatorio_sem_impressao(capsys):
    assert main(["2022", "1", "presidente"]) == 2
    assert "planilha" in capsys.readouterr().err


def test_interrupcao_retorna_130(monkeypatch):
    def interromper(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("apuracao.cli.executar", interromper)
    assert main(["2022", "1", "presidente", "--print-only"]) == 130


def test_erro_de_dados_retorna_1(monkeypatch, capsys):
    def falhar(*args, **kwargs):
        raise ValueError("Segundo turno ainda não publicado")

    monkeypatch.setattr("apuracao.cli.executar", falhar)
    assert main(["2026", "2", "presidente", "--print-only"]) == 1
    saida = capsys.readouterr()
    assert saida.out == ""
    assert "Segundo turno" in saida.err


def test_governador_impressao_filtra_uf(dados_2022, capsys):
    args = cria_parser().parse_args(["2022", "1", "governador", "--print-only", "--uf", "SP"])
    coletor = ColetaSimulada(dados_2022)
    assert executar(args, coletor=coletor) == 0
    dados = json.loads(capsys.readouterr().out)
    assert len(dados) == 1
    assert dados[0]["contexto"]["abrangencia"] == "sp"
    assert "sp-c0003-e000546-r.json" in coletor.urls[0]


def test_uf_inexistente_nao_silencia(dados_2022):
    args = cria_parser().parse_args(["2022", "2", "governador", "--print-only", "--uf", "RJ"])
    with pytest.raises(ValueError, match="RJ"):
        executar(args, coletor=ColetaSimulada(dados_2022))
