from dataclasses import replace
from decimal import Decimal

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_historico
from apuracao.modelo import Contexto


def test_lula_flavio_antes_demais_com_valores_corretos(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    lula = resultado.candidatos[0]
    flavio = replace(resultado.candidatos[1], nome_urna="FLAVIO BOLSONARO")
    outro = replace(lula, numero="14", nome_urna="Pessoa C", percentual=Decimal("0.01"))
    resultado = replace(resultado, candidatos=(outro, flavio, lula))
    tabela = tabela_historico([resultado])
    assert tabela.linhas[0] == [
        "Data/Hora",
        "% Seções apuradas",
        "% LULA (13)",
        "% FLAVIO BOLSONARO (22)",
        "% Pessoa C (14)",
    ]
    assert tabela.linhas[1][2:] == [0.6, 0.4, 0.01]
