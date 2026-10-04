from dataclasses import replace

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_resultado
from apuracao.modelo import Contexto


def test_resumo_agregado_usa_status_nacional_sem_mudar_votos(dados_2022):
    base = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    agregado = replace(base, origem="soma-ufs", matematicamente_definida=None, finalizada=None)
    oficial = replace(base, matematicamente_definida="s", finalizada=False)
    tabela = tabela_resultado(agregado, "Presidente", definicao_oficial=oficial)
    assert ["Matematicamente definida", "s"] in tabela.linhas
    assert ["Totalização final", False] in tabela.linhas
    assert ["Fonte da definição", "JSON nacional do TSE"] in tabela.linhas
    assert ["Atualização da definição", str(oficial.gerada_em)] in tabela.linhas
    assert tabela.cor_aba == "azul"
    assert tabela.linhas[1][3] == 54
    assert agregado.matematicamente_definida is None
