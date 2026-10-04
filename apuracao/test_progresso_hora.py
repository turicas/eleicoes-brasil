from dataclasses import replace
from decimal import Decimal

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_historico, tabela_resultado
from apuracao.modelo import Contexto, Secoes


def test_percentual_uf_totalizadas_disponivel_em_resumo(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 546, 3, "sp")).ler(dados_2022)
    resultado = replace(
        resultado, contexto=Contexto(2026, 1, 6259, 3, "sp"), secoes=Secoes(100, 50, 60, Decimal("0.60"))
    )
    linha = next(
        linha for linha in tabela_resultado(resultado, "SP").linhas if linha and linha[0] == "Seções totalizadas"
    )
    assert linha == ["Seções totalizadas", 60, "Seções totais", 100, "% Seções totalizadas", 0.6]


def test_data_historico_e_numerica_preserva_dia(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    celula = tabela_historico([resultado]).linhas[1][0]
    assert isinstance(celula, float)
    assert celula == 44836 + 18.5 / 24
