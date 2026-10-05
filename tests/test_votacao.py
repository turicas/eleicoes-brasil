import pytest

from extractors import fix_cargo

CARGOS = [
    ("PRESIDENTE", "1", "Presidente"),
    ("VICE-PRESIDENTE", "2", "Vice-Presidente"),
    ("GOVERNADOR", "3", "Governador"),
    ("VICE-GOVERNADOR", "4", "Vice-Governador"),
    ("SENADOR", "5", "Senador"),
    ("DEPUTADO FEDERAL", "6", "Deputado Federal"),
    ("DEPUTADO ESTADUAL", "7", "Deputado Estadual"),
    ("DEPUTADO DISTRITAL", "8", "Deputado Distrital"),
    ("1o SUPLENTE", "9", "1º Suplente Senador"),
    ("1O SUPLENTE", "9", "1º Suplente Senador"),
    ("1º SUPLENTE SENADOR", "9", "1º Suplente Senador"),
    ("1º SUPLENTE", "9", "1º Suplente Senador"),
    ("1O SUPLENTE SENADOR", "9", "1º Suplente Senador"),
    ("1o SUPLENTE SENADOR", "9", "1º Suplente Senador"),
    ("2o SUPLENTE", "10", "2º Suplente Senador"),
    ("2O SUPLENTE", "10", "2º Suplente Senador"),
    ("2º SUPLENTE SENADOR", "10", "2º Suplente Senador"),
    ("2º SUPLENTE", "10", "2º Suplente Senador"),
    ("2O SUPLENTE SENADOR", "10", "2º Suplente Senador"),
    ("2o SUPLENTE SENADOR", "10", "2º Suplente Senador"),
    ("PREFEITO", "11", "Prefeito"),
    ("VICE PREFEITO", "12", "Vice-Prefeito"),
    ("VICE-PREFEITO", "12", "Vice-Prefeito"),
    ("VEREADOR", "13", "Vereador"),
]


@pytest.mark.parametrize("forma", [str.upper, str.title, str.lower], ids=["uppercase", "mixed", "lowercase"])
@pytest.mark.parametrize("original,codigo,esperado", CARGOS)
def test_fix_cargo_aceita_grafias_e_corrige_codigo(original, codigo, esperado, forma):
    assert fix_cargo("0", forma(original)) == (codigo, esperado, "")


def test_fix_cargo_preserva_pergunta_original_plebiscito():
    pergunta = "Você é a favor da criação de São João?"
    assert fix_cargo("91", pergunta) == ("91", "Opção Plebiscito", pergunta)


def test_fix_cargo_desconhecido_nao_e_silenciado():
    with pytest.raises(KeyError, match="CARGO DESCONHECIDO"):
        fix_cargo("0", "Cargo desconhecido")
