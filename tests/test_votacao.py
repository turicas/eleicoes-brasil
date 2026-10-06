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
def test_fix_cargo_aceita_grafias_e_preserva_codigo(original, codigo, esperado, forma):
    assert fix_cargo("0", forma(original)) == ("0", esperado, "")


def test_codigo_nao_transforma_pergunta_em_descricao_conhecida():
    with pytest.raises(KeyError):
        fix_cargo("91", "Você é a favor da criação de São João?")


def test_fix_cargo_desconhecido_nao_e_silenciado():
    with pytest.raises(KeyError, match="CARGO DESCONHECIDO"):
        fix_cargo("0", "Cargo desconhecido")


@pytest.mark.parametrize("codigo", ["2", "17", "91", "DEFERIDO", "999", ""])
def test_cargo_nao_deduz_codigo_pela_descricao(codigo):
    assert fix_cargo(codigo, "Vereador") == (codigo, "Vereador", "")


@pytest.mark.parametrize("ausencia", ["-1", "-3", "-4", "#NE", "#NULO", ""])
def test_cargo_limpa_sentinelas_sem_criar_codigo(ausencia):
    assert fix_cargo(ausencia, ausencia) == ("", "", "")
