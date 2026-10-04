from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import linhas_resultado
from apuracao.modelo import Contexto


def test_tabela_tipificada_preserva_2022(dados_2022):
    from apuracao.apuracao import first_sheet_rows, read_data

    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    assert linhas_resultado(resultado) == first_sheet_rows(read_data(dados_2022))
