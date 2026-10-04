from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_resultado
from apuracao.modelo import Contexto
from apuracao.planilha import Planilha, TabelaPlanilha
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada, aba


def test_atualizacao_existente_so_valores_sem_formatar(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    planilha = PlanilhaSimulada({1: aba("SP", 40, 6, 1)})
    publicador = Planilha(ClienteSimulado(planilha), "ID", 2022, 1)
    publicador.publicar([tabela_resultado(resultado, "SP")])
    pedidos = planilha.lotes[-1]["requests"]
    assert not any(
        {"repeatCell", "updateDimensionProperties", "autoResizeDimensions"}.intersection(pedido) for pedido in pedidos
    )


def test_reutiliza_metadados_em_ciclos_sem_erro():
    planilha = PlanilhaSimulada({1: aba("Dados", 10, 2, 1)})
    publicador = Planilha(ClienteSimulado(planilha), "ID", 2026, 1)
    publicador.publicar([TabelaPlanilha("Dados", [["Nome", "Valor"], ["A", 1]])])
    publicador.publicar([TabelaPlanilha("Dados", [["Nome", "Valor"], ["A", 2]])])
    assert len(planilha.leituras) == 1
    assert len(planilha.lotes) == 2


def test_estado_novo_da_aba_fica_no_cache():
    planilha = PlanilhaSimulada()
    publicador = Planilha(ClienteSimulado(planilha), "ID", 2026, 1)
    publicador.publicar([TabelaPlanilha("Dados", [["Nome"], ["A"]])])
    publicador.publicar([TabelaPlanilha("Dados", [["Nome"], ["B"], ["C"]])])
    assert len(planilha.abas) == 1
    assert len(planilha.leituras) == 1
    assert next(iter(planilha.abas.values()))["valores"][2, 0] == {"stringValue": "C"}
