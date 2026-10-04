from dataclasses import replace

import pytest

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_resultado
from apuracao.cor_aba import cor_resultado, pedido_cor
from apuracao.modelo import Contexto
from apuracao.planilha import Planilha
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada, aba


@pytest.fixture
def resultado(dados_2022):
    return Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)


@pytest.mark.parametrize("estado,cor", [("e", "verde"), ("s", "azul"), ("n", "preto"), (None, "preto")])
def test_estado_para_cor(resultado, estado, cor):
    assert cor_resultado(replace(resultado, matematicamente_definida=estado)) == cor


@pytest.mark.parametrize("situacao,cor", [("Eleito", "verde"), ("2º turno", "azul"), ("Não eleito", "preto")])
def test_finalizacao_sem_md(resultado, situacao, cor):
    candidatos = (replace(resultado.candidatos[0], situacao=situacao),)
    assert cor_resultado(replace(resultado, finalizada=True, candidatos=candidatos)) == cor


def test_soma_nao_inventa_definicao(resultado):
    assert cor_resultado(replace(resultado, origem="soma-ufs", matematicamente_definida="e")) is None


def test_cor_no_mesmo_lote_sem_formato_celular(resultado):
    remota = PlanilhaSimulada({1: aba("Presidente", 40, 6, 1)})
    publicador = Planilha(ClienteSimulado(remota), "ID", 2022, 1)
    publicador.publicar([tabela_resultado(replace(resultado, matematicamente_definida="s"), "Presidente")])
    assert remota.abas[1]["properties"]["tabColorStyle"] == {"rgbColor": {"red": 0, "green": 0, "blue": 1}}
    assert not any("repeatCell" in pedido for pedido in remota.lotes[0]["requests"])
    publicador.publicar([tabela_resultado(replace(resultado, matematicamente_definida="s"), "Presidente")])
    assert not any(
        pedido.get("updateSheetProperties", {}).get("fields") == "tabColorStyle"
        for pedido in remota.lotes[-1]["requests"]
    )


def test_preto_explicito_nao_sem_cor():
    assert pedido_cor(1, "preto")["updateSheetProperties"]["properties"]["tabColorStyle"] == {
        "rgbColor": {"red": 0, "green": 0, "blue": 0}
    }


def test_agregado_consulta_nacional_para_cor(resultado, tmp_path, monkeypatch):
    from apuracao.acompanhamento import RotinaApuracao

    class Coletor:
        def buscar_json(self, url):
            assert "/br/br-c0001-e006257-u.json" in url
            return {"fonte": "oficial"}

    oficial = replace(resultado, matematicamente_definida="s")
    monkeypatch.setattr(
        "apuracao.acompanhamento.Apuracao2026",
        lambda contexto: type("Leitor", (), {"ler": lambda self, dados: oficial})(),
    )
    rotina = RotinaApuracao(
        2026, 1, "presidente", "ID", tmp_path, coletor=Coletor(), planilha=object(), presidente_por_uf=True
    )
    agregado = replace(resultado, contexto=Contexto(2026, 1, 6257, 1, "br"), origem="soma-ufs")
    assert rotina._consultar_cor_presidente(agregado) == "azul"


def test_verde_bandeira():
    cor = pedido_cor(1, "verde")["updateSheetProperties"]["properties"]["tabColorStyle"]["rgbColor"]
    assert cor == {"red": 0, "green": 156 / 255, "blue": 59 / 255}
