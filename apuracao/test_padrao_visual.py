from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_resultado
from apuracao.modelo import Contexto
from apuracao.planilha import Planilha
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada


def test_publicacao_aplica_padrao_e_nao_aumenta_escritas(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    tabela = tabela_resultado(resultado, "SP")
    planilha = PlanilhaSimulada()
    publicador = Planilha(ClienteSimulado(planilha), "ID", 2022, 1)
    publicador.publicar([tabela])
    aba = next(iter(planilha.abas.values()))
    assert aba["formatos"][0, 0]["textFormat"]["bold"] is True
    assert aba["formatos"][1, 3]["numberFormat"]["pattern"] == "#,##0"
    indice = next(indice for indice, linha in enumerate(tabela.linhas) if linha and linha[0] == "Seções totalizadas")
    assert aba["formatos"][indice, 0]["backgroundColorStyle"]["rgbColor"]["red"] == 239 / 255
    assert aba["formatos"][indice, 4]["numberFormat"]["type"] != "PERCENT"
    assert aba["auto_resize"]["dimension"] == "COLUMNS"
    assert aba["formatos"][0, 0]["textFormat"]["fontFamily"] == "Source Code Pro"
    assert len(planilha.lotes) == 1
    assert aba["valores"][1, 3] == {"numberValue": 54}
    publicador.publicar([tabela])
    assert len(planilha.abas) == 1
    assert aba["valores"][1, 3] == {"numberValue": 54}
