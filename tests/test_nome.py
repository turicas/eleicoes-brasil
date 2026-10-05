import pytest


@pytest.mark.parametrize("nome", ["", " ", "'", ",", ".", "]"])
def test_fix_nome_vazio(nome):
    from extractors import fix_nome

    assert fix_nome(nome) == ""


def test_nome_bonito_none():
    from utils import nome_bonito

    assert nome_bonito(None) == ""
