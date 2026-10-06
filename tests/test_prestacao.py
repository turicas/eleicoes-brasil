import pytest

from extractors import PrestacaoContasDespesasExtractor, PrestacaoContasReceitasExtractor


@pytest.fixture(params=[PrestacaoContasReceitasExtractor, PrestacaoContasDespesasExtractor])
def prestacao(request):
    return request.param()


def converter(prestacao, **valores):
    dados = {
        "numero_sequencial": "123",
        "data": "",
        "data_prestacao_contas": "",
        "data_eleicao": "",
        "valor": "42,00",
        "cnpj": "",
        "cpf_cnpj_doador": "",
        "cpf_cnpj_doador_originario": "",
        "cpf_cnpj_fornecedor": "",
    }
    dados.update(valores)
    return prestacao.convert_row(list(dados), list(dados), 2024)(list(dados.values()))


@pytest.mark.parametrize("campo", ["cargo", "cargo_doador", "cargo_fornecedor"])
def test_cargo_e_formatado_sem_recalcular_codigo(prestacao, campo):
    codigo = campo.replace("cargo", "codigo_cargo", 1)
    resultado = converter(prestacao, **{campo: "VICE PREFEITO", codigo: "987"})
    assert resultado[campo] == "Vice-Prefeito"
    assert resultado[codigo] == "987"


@pytest.mark.parametrize("campo", ["cargo", "cargo_doador", "cargo_fornecedor"])
@pytest.mark.parametrize("sentinela", ["-1", "-3", "-4", "#NE", "#NULO"])
def test_cargo_ausente_nao_ganha_codigo(prestacao, campo, sentinela):
    codigo = campo.replace("cargo", "codigo_cargo", 1)
    resultado = converter(prestacao, **{campo: sentinela, codigo: sentinela})
    assert resultado[campo] == resultado[codigo] == ""


@pytest.mark.parametrize("campo", ["cargo", "cargo_doador", "cargo_fornecedor"])
def test_cargo_desconhecido_interrompe_prestacao(prestacao, campo):
    with pytest.raises(KeyError):
        converter(prestacao, **{campo: "Cargo desconhecido"})


def test_descricao_do_cargo_nao_inventa_coluna_codigo(prestacao):
    resultado = converter(prestacao, cargo="Vereador")
    assert resultado["cargo"] == "Vereador"
    assert "codigo_cargo" not in resultado
