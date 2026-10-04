from dataclasses import replace
from datetime import timedelta

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import data_planilha, tabela_historico, titulo_resultado
from apuracao.modelo import Contexto


def test_agregados_mesma_fonte_maxima_tem_horas_de_coleta_distintas(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    primeiro = replace(
        resultado, origem="soma-ufs", geracao="ufs-1", capturada_em=resultado.gerada_em + timedelta(seconds=10)
    )
    segundo = replace(primeiro, geracao="ufs-2", capturada_em=resultado.gerada_em + timedelta(seconds=35))
    linhas = tabela_historico([segundo, primeiro]).linhas
    assert linhas[1][0] == data_planilha(primeiro.capturada_em)
    assert linhas[2][0] == data_planilha(segundo.capturada_em)
    assert linhas[1][0] != linhas[2][0]
    assert "coletado:" in titulo_resultado(primeiro)


def test_oficial_continua_hora_da_fonte(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    assert tabela_historico([resultado]).linhas[1][0] == data_planilha(resultado.gerada_em)
