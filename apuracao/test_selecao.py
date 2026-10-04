from dataclasses import replace

import pytest

from apuracao.adaptador2022 import Apuracao2022
from apuracao.modelo import Contexto, Secoes
from apuracao.selecao import escolher_cobertura


@pytest.fixture
def nacional(dados_2022):
    base = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    return replace(base, contexto=Contexto(2026, 1, 6257, 1, "br"), secoes=Secoes(100, 50, 50))


def test_nacional_ganha_empate_e_maior_cobertura(nacional):
    soma = replace(nacional, origem="soma-ufs", secoes=Secoes(100, 40, 40))
    assert escolher_cobertura(nacional, soma) is nacional
    assert escolher_cobertura(nacional, replace(soma, secoes=nacional.secoes)) is nacional


def test_soma_ganha_por_secoes_nao_horario(nacional):
    soma = replace(nacional, origem="soma-ufs", secoes=Secoes(100, 60, 60))
    assert escolher_cobertura(nacional, soma) is soma


def test_falha_uma_fonte_aproveita_outra(nacional):
    assert escolher_cobertura(nacional, None) is nacional
    soma = replace(nacional, origem="soma-ufs")
    assert escolher_cobertura(None, soma) is soma
    with pytest.raises(ValueError, match="disponível"):
        escolher_cobertura(None, None)


def test_totais_incompativeis_nao_publicam_soma(nacional):
    soma = replace(nacional, origem="soma-ufs", secoes=Secoes(101, 60, 60))
    with pytest.raises(ValueError, match="[Tt]otal"):
        escolher_cobertura(nacional, soma)
