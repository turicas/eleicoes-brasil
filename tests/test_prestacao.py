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


@pytest.fixture
def arquivo_prestacao(prestacao, monkeypatch, tmp_path):
    import csv
    from io import BytesIO, StringIO
    from types import SimpleNamespace

    dados = {
        "UF": ("sigla_unidade_federativa", "AC"),
        "SEQ": ("numero_sequencial", "123"),
        "DATA": ("data", ""),
        "PRESTACAO": ("data_prestacao_contas", ""),
        "ELEICAO": ("data_eleicao", ""),
        "VALOR": ("valor", "42,00"),
        "CNPJ": ("cnpj", ""),
        "DOADOR": ("cpf_cnpj_doador", ""),
        "ORIGINARIO": ("cpf_cnpj_doador_originario", ""),
        "FORNECEDOR": ("cpf_cnpj_fornecedor", ""),
    }
    campos = [SimpleNamespace(nome_tse=nome, nome_final=campo) for nome, (campo, _) in dados.items()]
    monkeypatch.setattr(prestacao, "download_filename", lambda ano: tmp_path / "prestacao.zip")
    monkeypatch.setattr(prestacao, "get_headers", lambda *args: {"year_fields": campos, "final_fields": campos})

    def preparar(*, extra=False, ausente=False, aspas=False):
        nomes = list(reversed(dados))
        if ausente:
            nomes.remove("VALOR")
        valores = [dados[nome][1] for nome in nomes]
        if extra:
            nomes.append("DESCONHECIDO")
            valores.append("valor novo")
        if aspas:
            for campo in campos:
                campo.nome_tse = f'"{campo.nome_tse}"'
        stream = StringIO(newline="")
        escritor = csv.writer(stream, delimiter=";")
        escritor.writerow(nomes)
        escritor.writerow(valores)
        bruto = stream.getvalue().encode("latin-1")
        monkeypatch.setattr(
            prestacao,
            "_get_compressed_fobjs",
            lambda *args: ([BytesIO(bruto)], ["prestacao_AC.csv"]),
        )

    return preparar


def test_extracao_respeita_ordem_do_cabecalho(prestacao, arquivo_prestacao):
    arquivo_prestacao()
    (resultado,) = prestacao.extract(2022)
    assert resultado["valor"] == "42.00"
    assert resultado["ano"] == 2022
    assert resultado["sigla_unidade_federativa"] == "AC"


@pytest.mark.parametrize("alteracao,coluna", [("extra", "DESCONHECIDO"), ("ausente", "VALOR")])
def test_extracao_rejeita_cabecalho_divergente(prestacao, arquivo_prestacao, alteracao, coluna):
    arquivo_prestacao(**{alteracao: True})
    with pytest.raises(ValueError, match=rf"prestacao.zip#prestacao_AC.csv:.*{coluna}"):
        list(prestacao.extract(2022))


def test_extracao_normaliza_aspas_no_dicionario(prestacao, arquivo_prestacao):
    arquivo_prestacao(aspas=True)
    (resultado,) = prestacao.extract(2022)
    assert resultado["valor"] == "42.00"
