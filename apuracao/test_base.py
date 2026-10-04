import pytest

from apuracao.adaptador2022 import Apuracao2022
from apuracao.adaptador2026 import Apuracao2026
from apuracao.base import Apuracao
from apuracao.modelo import Contexto


@pytest.mark.parametrize("classe,ano,eleicao", [(Apuracao2022, 2022, 544), (Apuracao2026, 2026, 6257)])
def test_adaptadores_compartilham_contrato(classe, ano, eleicao):
    assert isinstance(classe(Contexto(ano, 1, eleicao, 1, "br")), Apuracao)


def test_erro_2022_tem_contexto(dados_2022):
    dados_2022["dg"] = "inválida"
    with pytest.raises(ValueError, match="dg/hg.*544.*br"):
        Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
