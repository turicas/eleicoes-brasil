from dataclasses import replace
from decimal import Decimal

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import titulo_resultado
from apuracao.modelo import Contexto, Secoes
from apuracao.planilha import Planilha, TabelaPlanilha
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada


def test_titulo_2022_preserva_progresso(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    assert titulo_resultado(resultado) == "[50.00%] Apuração Eleições 2022 (atualizado: 2022-10-02 18:30:00-03:00)"


def test_titulo_2026_usa_totalizadas_nao_apuradas(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    resultado = replace(
        resultado, contexto=Contexto(2026, 1, 6257, 1, "br"), secoes=Secoes(100, 50, 60, Decimal("0.60"))
    )
    assert titulo_resultado(resultado).startswith("[60.00%] Apuração Eleições 2026")


def test_titulo_sem_denominador_nao_inventa_percentual(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    resultado = replace(resultado, secoes=Secoes(0, 0))
    assert titulo_resultado(resultado).startswith("Apuração Eleições 2022")


def test_titulo_e_valores_no_mesmo_lote():
    planilha = PlanilhaSimulada()
    publicador = Planilha(ClienteSimulado(planilha), "ID", 2026, 1, sleep=lambda espera: None)
    publicador.publicar([TabelaPlanilha("Presidente", [["Cabeçalho"], [1]])], titulo="Novo título")
    assert len(planilha.lotes) == 1
    assert planilha.titulo == "Novo título"
    assert "updateCells" in str(planilha.lotes[0])
