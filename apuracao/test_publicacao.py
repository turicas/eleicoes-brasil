from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_historico, tabela_resultado
from apuracao.modelo import Contexto, Secoes, Votos


def resultado_2022(dados):
    return Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados)


def test_tabela_resultado_ordena_sem_mudar_objeto(dados_2022):
    resultado = resultado_2022(dados_2022)
    invertido = replace(resultado, candidatos=tuple(reversed(resultado.candidatos)))
    tabela = tabela_resultado(invertido, "Presidente")
    assert tabela.nome == "Presidente"
    assert tabela.linhas[1] == ["LULA", "VICE A", "13", 54, 0.6, 18]
    assert tabela.linhas[2][-1] is None
    assert invertido.candidatos[0].numero == "22"
    assert tabela.colunas_percentuais == (4,)


def test_historico_dinamico_identidade_ordem_percentual(dados_2022):
    primeiro = resultado_2022(dados_2022)
    candidato = replace(primeiro.candidatos[0], sequencial="100", percentual=Decimal("0.415"))
    primeiro = replace(primeiro, candidatos=(candidato, primeiro.candidatos[1]), geracao="10")
    segundo = replace(
        primeiro,
        candidatos=tuple(reversed(primeiro.candidatos)),
        gerada_em=primeiro.gerada_em + timedelta(days=1),
        geracao="11",
    )
    tabela = tabela_historico([segundo, primeiro, primeiro])
    assert len(tabela.linhas) == 3
    assert tabela.linhas[0] == ["Data/Hora", "% Seções apuradas", "% LULA (13)", "% JAIR BOLSONARO (22)"]
    assert tabela.linhas[1][0] == 44836 + 18.5 / 24
    assert tabela.linhas[2][0] == 44837 + 18.5 / 24
    assert tabela.linhas[1][2:] == [0.415, 0.4]
    assert tabela.linhas[1][1] == 0.5
    assert tabela.colunas_percentuais == (1, 2, 3)


def test_historico_candidato_ausente_nao_vira_zero(dados_2022):
    primeiro = resultado_2022(dados_2022)
    segundo = replace(primeiro, candidatos=primeiro.candidatos[:1], gerada_em=primeiro.gerada_em + timedelta(seconds=1))
    assert tabela_historico([primeiro, segundo]).linhas[-1][-1] is None


def test_dados_nao_liberados_nao_exibem_zero(dados_2022):
    resultado = replace(resultado_2022(dados_2022), divulgacao_liberada=False)
    tabela = tabela_resultado(resultado, "Presidente")
    assert tabela.linhas[1][3:] == [None, None, None]
    assert ["Divulgação", "Aguardando liberação pelo TSE"] in tabela.linhas
    assert tabela_historico([resultado]).linhas[1][2:] == [None, None]


def test_resumo_distingue_totalizadas_apuradas_e_anulados(dados_2022):
    resultado = replace(
        resultado_2022(dados_2022),
        secoes=Secoes(100, 80, 90, Decimal("0.9"), Decimal(1)),
        votos=Votos(100, 70, 5, 5, 90, 10, 10),
        finalizada=False,
        andamento="p",
    )
    linhas = tabela_resultado(resultado, "Presidente").linhas
    assert ["Seções totalizadas", 90, "Seções totais", 100, "% Seções totalizadas", 0.9] in linhas
    assert ["Seções apuradas", 80, None, None, "% Seções apuradas / total", 0.8] in linhas
    assert ["Votos anulados", 10] in linhas
    assert ["Votos anulados sub judice", 10] in linhas


def test_historico_vazio_tem_cabecalho():
    assert tabela_historico([]).linhas == [["Data/Hora", "% Seções totalizadas"]]


def test_historico_omite_snapshots_sem_votos_validos(dados_2022):
    apurado = replace(resultado_2022(dados_2022), geracao="com-votos")
    inicial = replace(
        apurado,
        geracao="sem-votos",
        gerada_em=apurado.gerada_em - timedelta(minutes=1),
        secoes=Secoes(100, 0, 0, Decimal(0)),
        votos=Votos(0, 0, 0, 0),
        candidatos=tuple(replace(candidato, votos=0, percentual=Decimal(0)) for candidato in apurado.candidatos),
    )
    tabela = tabela_historico([inicial, apurado], incluir_origem=True)
    assert tabela.linhas == tabela_historico([apurado], incluir_origem=True).linhas
    assert len(tabela_historico([inicial]).linhas) == 1


def test_historico_preserva_zero_legitimo_de_candidato(dados_2022):
    resultado = resultado_2022(dados_2022)
    resultado = replace(
        resultado,
        candidatos=(
            replace(resultado.candidatos[0], votos=0, percentual=Decimal(0)),
            replace(resultado.candidatos[1], votos=resultado.votos.validos, percentual=Decimal(1)),
        ),
    )
    assert tabela_historico([resultado]).linhas[1][2:] == [0.0, 1.0]
