from dataclasses import replace

import pytest

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_resultado
from apuracao.formatacao import pedidos_formatacao
from apuracao.modelo import Contexto, Eleitorado
from apuracao.test_formatacao import celulas


@pytest.mark.parametrize("total,apurado,restante", [(200, 100, 100), (200, 200, 0), (0, 0, 0)])
def test_eleitorado_restante_na_mesma_linha(dados_2022, total, apurado, restante):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    resultado = replace(resultado, eleitorado=Eleitorado(total, apurado))
    tabela = tabela_resultado(resultado, "Presidente")
    indice = next(
        indice for indice, linha in enumerate(tabela.linhas) if linha and linha[0] == "Eleitorado de seções apuradas"
    )
    assert tabela.linhas[indice] == [
        "Eleitorado de seções apuradas",
        apurado,
        "Eleitorado total",
        total,
        "Eleitorado que falta apurar",
        restante,
    ]
    formatos = celulas(pedidos_formatacao(1, "Presidente", tabela.linhas, len(tabela.linhas), 6))
    assert formatos[indice, 5]["numberFormat"] == {"type": "NUMBER", "pattern": "#,##0"}
    assert formatos[indice, 4]["textFormat"]["bold"] is True
    assert formatos[indice, 5]["horizontalAlignment"] == "RIGHT"
