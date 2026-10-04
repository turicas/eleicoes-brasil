from dataclasses import replace

import pytest

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_historico
from apuracao.modelo import Contexto


def test_historico_2022_preserva_progresso_apurado(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    tabela = tabela_historico([resultado])
    assert tabela.linhas[0][1] == "% Seções apuradas"
    assert tabela.linhas[1][1] == 0.5


def test_historico_2022_total_zero_nao_inventa_percentual(dados_2022):
    dados_2022["s"] = dados_2022["sa"] = "0"
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    assert tabela_historico([resultado]).linhas[1][1] is None


@pytest.mark.parametrize("campo,valor", [("ele", "999"), ("t", "2"), ("f", "s")])
def test_metadados_2022_incompativeis(dados_2022, campo, valor):
    dados_2022[campo] = valor
    with pytest.raises(ValueError, match=campo):
        Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)


def test_historico_2026_nao_inventa_totalizadas(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    resultado = replace(resultado, contexto=Contexto(2026, 1, 6257, 1, "br"))
    assert tabela_historico([resultado]).linhas[0][1] == "% Seções totalizadas"
    assert tabela_historico([resultado]).linhas[1][1] is None
