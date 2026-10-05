import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

import settings
from extractors import CandidaturaExtractor


class CandidaturaExtractorTestCase(unittest.TestCase):
    def assert_fix_fobj(self, input_str, expected_str):
        extractor = CandidaturaExtractor()
        result = extractor.fix_fobj(StringIO(input_str))
        self.assertEqual(result.read(), expected_str)

    def test_fix_line_correct_escape(self):
        input_data = '''"83494650853";"SONIA ""MEREU""";"2";"DEFERIDO"'''
        expected_data = '''"83494650853";"SONIA ""MEREU""";"2";"DEFERIDO"'''
        self.assert_fix_fobj(input_data, expected_data)

    def test_fix_line_incorrect_escape(self):
        input_data = '''"83494650853";"SONIA "MEREU"";"2";"DEFERIDO"'''
        expected_data = '''"83494650853";"SONIA ""MEREU""";"2";"DEFERIDO"'''
        self.assert_fix_fobj(input_data, expected_data)

    def test_fix_line_incorrect_escape_2(self):
        input_data = '''"83494650853";"SONIA MEREU"";"2";"DEFERIDO"'''
        expected_data = '''"83494650853";"SONIA MEREU""";"2";"DEFERIDO"'''
        self.assert_fix_fobj(input_data, expected_data)

    def test_fix_line_incorrect_escape_3(self):
        input_data = '''"61937410978";"DAVID ''XIXICO"";"2";"DEFERIDO"'''
        expected_data = '''"61937410978";"DAVID ''XIXICO""";"2";"DEFERIDO"'''
        self.assert_fix_fobj(input_data, expected_data)

    def test_fix_line_incorrect_escape_4(self):
        input_data = '''"61937410978";""DAVID XIXICO"";"2";"DEFERIDO"'''
        expected_data = '''"61937410978";"""DAVID XIXICO""";"2";"DEFERIDO"'''
        self.assert_fix_fobj(input_data, expected_data)

    def test_converte_dados_nao_divulgaveis_em_campos_vazios(self):
        fields = [
            "ano",
            "numero_sequencial",
            "codigo_cargo",
            "cargo",
            "cpf",
            "nome",
            "data_eleicao",
            "data_aceite",
            "data_nascimento",
            "sigla_unidade_federativa",
            "sigla_unidade_federativa_nascimento",
            "titulo_eleitoral",
            "candidatura_inserida_urna",
            "email",
            "nome_social",
            "codigo_genero",
            "etnia",
            "estado_civil",
            "genero",
            "grau_instrucao",
            "unidade_eleitoral",
            "tipo_abrangencia_eleicao",
            "tipo_eleicao",
            "tipo_agremiacao",
            "ocupacao",
        ]
        row = [
            "2024",
            "123",
            "1",
            "PRESIDENTE",
            "-4",
            "CANDIDATO NAO DIVULGAVEL",
            "",
            "",
            "",
            "BR",
            "Não divulgável",
            "-4",
            "SIM",
            "NÃO DIVULGÁVEL",
            "Não divulgável",
            "-4",
            "PARDA",
            "CASADO(A)",
            "FEMININO",
            "ENSINO MÉDIO COMPLETO",
            "ABADIA DE GOIÁS",
            "MUNICIPAL",
            "ELEIÇÃO SUPLEMENTAR",
            "PARTIDO ISOLADO",
            "ADVOGADO",
        ]

        result = CandidaturaExtractor().convert_row(fields, fields)(row)

        self.assertEqual(result["cpf"], "")
        self.assertIsNone(result["pessoa_uuid"])
        self.assertEqual(result["titulo_eleitoral"], "")
        self.assertEqual(result["email"], "")
        self.assertEqual(result["nome_social"], "")
        self.assertEqual(result["codigo_genero"], "")
        self.assertEqual(result["sigla_unidade_federativa_nascimento"], "")

    def test_conversao_preserva_nome_original_e_nome_urna_e_calcula_nome_exibicao(self):
        fields = [
            "ano",
            "numero_sequencial",
            "codigo_cargo",
            "cargo",
            "cpf",
            "nome",
            "nome_urna",
            "data_eleicao",
            "data_aceite",
            "data_nascimento",
            "sigla_unidade_federativa",
            "sigla_unidade_federativa_nascimento",
            "titulo_eleitoral",
            "candidatura_inserida_urna",
            "etnia",
            "estado_civil",
            "genero",
            "grau_instrucao",
            "unidade_eleitoral",
            "tipo_abrangencia_eleicao",
            "tipo_eleicao",
            "tipo_agremiacao",
            "ocupacao",
        ]
        row = [
            "2024",
            "123456789",
            "6",
            "DEPUTADO FEDERAL",
            "12345678901",
            "LUIZ INACIO LULA DA SILVA",
            "CB PM LULA",
            "06/10/2024",
            "15/08/2024",
            "27/10/1945",
            "SP",
            "PE",
            "123456789012",
            "SIM",
            "PRETA",
            "SOLTEIRO(A)",
            "MASCULINO",
            "SUPERIOR INCOMPLETO",
            "AFONSO CLÁUDIO",
            "FEDERAL",
            "ELEIÇÃO SUPLEMENTAR",
            "COLIGAÇÃO",
            "PROFESSOR DE ENSINO MÉDIO",
        ]

        result = CandidaturaExtractor().convert_row(fields, fields)(row)

        self.assertEqual(result["nome"], "LUIZ INACIO LULA DA SILVA")
        self.assertEqual(result["nome_exibicao"], "Luiz Inacio Lula da Silva")
        self.assertEqual(result["nome_urna"], "CB PM LULA")  # Preserva nome_urna como publicado

    def test_download_adiciona_cache_busting_em_urls_do_tse(self):
        extractor = CandidaturaExtractor()
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_path = settings.DOWNLOAD_PATH
            try:
                settings.DOWNLOAD_PATH = Path(tmpdir)
                chamadas = []

                def fake_download_file(url, **kwargs):
                    chamadas.append(url)
                    temp_fobj = tempfile.NamedTemporaryFile(delete=False)
                    temp_fobj.write(b"conteudo")
                    temp_fobj.close()
                    return temp_fobj.name

                with patch("extractors.download_file", side_effect=fake_download_file):
                    extractor.download(2026, force=True)

                self.assertEqual(len(chamadas), 1)
                self.assertIn("cdn.tse.jus.br", chamadas[0])
                self.assertIn("_=", chamadas[0])
            finally:
                settings.DOWNLOAD_PATH = orig_path

    def test_uses_2024_headers_for_2026(self):
        headers = CandidaturaExtractor().get_headers(2026, None, "consulta_cand_2026_AC.csv")

        self.assertEqual(headers["year_fields"][0].nome_tse, "DT_GERACAO")
        self.assertEqual(headers["year_fields"][-1].nome_tse, "DS_SIT_TOT_TURNO")


@pytest.fixture
def candidatura_identidade():
    return {
        "ano": "2024",
        "numero_sequencial": "123",
        "codigo_cargo": "6",
        "cargo": "DEPUTADO FEDERAL",
        "cpf": "12345678901",
        "nome": "JOÃO D´ÁVILA",
        "nome_urna": "JOÃO",
        "data_eleicao": "06/10/2024",
        "data_aceite": "",
        "data_nascimento": "",
        "sigla_unidade_federativa": "SP",
        "sigla_unidade_federativa_nascimento": "SP",
        "titulo_eleitoral": "",
        "candidatura_inserida_urna": "SIM",
        "etnia": "",
        "estado_civil": "",
        "genero": "",
        "grau_instrucao": "",
        "unidade_eleitoral": "SÃO PAULO",
        "tipo_abrangencia_eleicao": "FEDERAL",
        "tipo_eleicao": "ELEIÇÃO ORDINÁRIA",
        "tipo_agremiacao": "PARTIDO ISOLADO",
        "ocupacao": "",
    }


def converte_candidatura_identidade(candidatura_identidade):
    campos = list(candidatura_identidade)
    return CandidaturaExtractor().convert_row(campos, campos)(list(candidatura_identidade.values()))


@pytest.mark.parametrize(
    "nome,esperado",
    [
        ("JOÃO D´ÁVILA", "6bf49b6a-7d3f-5b93-85ad-485a15e69d14"),
        ("` D' ÁVILA", "3a1f337d-ddea-5390-9d1b-1c5e652ff3cd"),
        (" ANA  MARIA ", "66010900-8181-5149-9aad-932ef9cbe79c"),
        ("MARIA DE SOUZA", "8c262b4d-fb51-5b0a-9184-033e3aeb9118"),
        ("JOÃO-MARIA III", "f2973e32-a8f4-5e93-8ce7-4cd981959577"),
        ("MCDONALD D’ÁVILA", "84617c8c-ff82-5035-9e23-4f1739ea5fe6"),
    ],
)
def test_uuid_compativel_com_identidade_publicada(candidatura_identidade, nome, esperado):
    candidatura_identidade["nome"] = nome
    assert str(converte_candidatura_identidade(candidatura_identidade)["pessoa_uuid"]) == esperado


def test_nome_original_e_apresentacao_separados(candidatura_identidade):
    resultado = converte_candidatura_identidade(candidatura_identidade)
    assert resultado["nome"] == "JOÃO D´ÁVILA"
    assert resultado["nome_exibicao"] == "João D'Ávila"
    assert resultado["nome_urna"] == "JOÃO"


def test_identidade_independe_da_apresentacao(candidatura_identidade, monkeypatch):
    import extractors

    esperado = converte_candidatura_identidade(candidatura_identidade)["pessoa_uuid"]
    monkeypatch.setattr(extractors, "nome_bonito", lambda nome: "Apresentação diferente")
    resultado = converte_candidatura_identidade(candidatura_identidade)
    assert resultado["pessoa_uuid"] == esperado
    assert resultado["nome_exibicao"] == "Apresentação diferente"


@pytest.mark.parametrize("cpf", ["", "#NULO#", "-4"])
def test_pessoa_sem_cpf_nao_ganha_uuid(candidatura_identidade, cpf):
    candidatura_identidade["cpf"] = cpf
    assert converte_candidatura_identidade(candidatura_identidade)["pessoa_uuid"] is None


def test_nome_ausente_nao_quebra_conversao(candidatura_identidade):
    candidatura_identidade["nome"] = "#NULO#"
    resultado = converte_candidatura_identidade(candidatura_identidade)
    assert resultado["nome"] == resultado["nome_exibicao"] == ""


def test_nome_exibicao_no_schema_dicionario_e_exportacao(candidatura_identidade, tmp_path):
    import csv
    from io import StringIO

    import rows

    import settings
    from tse import create_final_headers

    extractor = CandidaturaExtractor()
    assert extractor.schema["nome_exibicao"] is rows.fields.TextField
    destino = tmp_path / "candidatura_final.csv"
    create_final_headers("candidatura", extractor.order_columns, destino, extractor.calculated_fields)
    with destino.open() as arquivo:
        gerado = list(csv.DictReader(arquivo))
    with (settings.HEADERS_PATH / "candidatura_final.csv").open() as arquivo:
        assert gerado == list(csv.DictReader(arquivo))
    descricao = next(campo["descricao"] for campo in gerado if campo["nome_final"] == "nome_exibicao")
    assert "calculada" in descricao and "Aparece no TSE" not in descricao
    metadados = extractor.get_headers(2024, None, "consulta_cand_2024_SP.csv")
    assert "nome_exibicao" not in [campo.nome_final for campo in metadados["year_fields"]]
    campos_finais = [campo.nome_final for campo in metadados["final_fields"] if campo.nome_final]
    resultado = extractor.convert_row(list(candidatura_identidade), campos_finais)(
        list(candidatura_identidade.values())
    )
    saida = StringIO()
    escritor = csv.DictWriter(saida, fieldnames=list(extractor.schema))
    escritor.writeheader()
    escritor.writerow(resultado)
    publicado = next(csv.DictReader(StringIO(saida.getvalue())))
    assert publicado["nome"] == candidatura_identidade["nome"]
    assert publicado["nome_exibicao"] == "João D'Ávila"


def test_extracao_publica_preserva_header_tse_e_calcula_apresentacao(candidatura_identidade, tmp_path, monkeypatch):
    import csv
    from io import StringIO
    from zipfile import ZipFile

    import settings
    from utils import TSEDialect

    extractor = CandidaturaExtractor()
    monkeypatch.setattr(settings, "DOWNLOAD_PATH", tmp_path)
    metadados = extractor.get_headers(2024, None, "consulta_cand_2024_SP.csv")
    colunas = list(metadados["year_fields"])
    conteudo = StringIO()
    escritor = csv.writer(conteudo, dialect=TSEDialect)
    escritor.writerow([campo.nome_tse for campo in colunas])
    escritor.writerow([candidatura_identidade.get(campo.nome_final, "") for campo in colunas])
    destino = extractor.download_filename(2024)
    destino.parent.mkdir(parents=True)
    with ZipFile(destino, "w") as arquivo:
        arquivo.writestr("consulta_cand_2024_SP.csv", conteudo.getvalue().encode("latin-1"))
    resultados = list(extractor.extract(2024))
    assert len(resultados) == 1
    assert resultados[0]["nome"] == candidatura_identidade["nome"]
    assert resultados[0]["nome_exibicao"] == "João D'Ávila"
    assert str(resultados[0]["pessoa_uuid"]) == "6bf49b6a-7d3f-5b93-85ad-485a15e69d14"


@pytest.fixture
def candidatura_categorias():
    return {
        "ano": "2024",
        "numero_sequencial": "123",
        "codigo_cargo": "6",
        "cargo": "DEPUTADO FEDERAL",
        "cpf": "12345678901",
        "nome": "JOÃO D´ÁVILA",
        "nome_urna": "JOÃO",
        "data_eleicao": "06/10/2024",
        "data_aceite": "",
        "data_nascimento": "",
        "sigla_unidade_federativa": "SP",
        "sigla_unidade_federativa_nascimento": "SP",
        "titulo_eleitoral": "",
        "candidatura_inserida_urna": "SIM",
        "etnia": "",
        "estado_civil": "",
        "genero": "",
        "grau_instrucao": "",
        "unidade_eleitoral": "SÃO PAULO",
        "tipo_abrangencia_eleicao": "FEDERAL",
        "tipo_eleicao": "ELEIÇÃO ORDINÁRIA",
        "tipo_agremiacao": "PARTIDO ISOLADO",
        "ocupacao": "",
    }


def converte_candidatura_categorias(candidatura_categorias):
    campos = list(candidatura_categorias)
    return CandidaturaExtractor().convert_row(campos, campos)(list(candidatura_categorias.values()))


CATEGORIAS_HISTORICAS = [
    ("estado_civil", "NÃO INFORMADO", "Não informado"),
    ("genero", "NÃO INFORMADO", "Não informado"),
    ("grau_instrucao", "1º GRAU COMPLETO", "1º grau completo"),
    ("grau_instrucao", "1º GRAU INCOMPLETO", "1º grau incompleto"),
    ("grau_instrucao", "2º GRAU COMPLETO", "2º grau completo"),
    ("grau_instrucao", "2º GRAU INCOMPLETO", "2º grau incompleto"),
    ("grau_instrucao", "FUNDAMENTAL COMPLETO", "Ensino fundamental completo"),
    ("grau_instrucao", "FUNDAMENTAL INCOMPLETO", "Ensino fundamental incompleto"),
    ("grau_instrucao", "MÉDIO COMPLETO", "Ensino médio completo"),
    ("grau_instrucao", "MÉDIO INCOMPLETO", "Ensino médio incompleto"),
    ("grau_instrucao", "NÃO INFORMADO", "Não informado"),
    ("tipo_agremiacao", "", ""),
    ("tipo_eleicao", "ORDINÁRIA", "Eleição ordinária"),
]


@pytest.mark.parametrize("campo,original,esperado", CATEGORIAS_HISTORICAS)
def test_categorias_historicas(candidatura_categorias, campo, original, esperado):
    candidatura_categorias[campo] = original
    assert converte_candidatura_categorias(candidatura_categorias)[campo] == esperado


@pytest.mark.parametrize("campo", ["estado_civil", "genero", "grau_instrucao", "tipo_agremiacao", "tipo_eleicao"])
def test_categoria_desconhecida_nao_e_silenciada(candidatura_categorias, campo):
    candidatura_categorias[campo] = "CATEGORIA SEM SIGNIFICADO CONFIRMADO"
    with pytest.raises(KeyError):
        converte_candidatura_categorias(candidatura_categorias)


@pytest.mark.parametrize("campo", ["estado_civil", "genero", "grau_instrucao", "tipo_agremiacao"])
@pytest.mark.parametrize("ausencia", ["", "#NULO#", "#NE#"])
def test_ausencia_de_categoria(candidatura_categorias, campo, ausencia):
    candidatura_categorias[campo] = ausencia
    assert converte_candidatura_categorias(candidatura_categorias)[campo] == ""


@pytest.fixture
def candidatura_sentinelas():
    return {
        "ano": "2024",
        "numero_sequencial": "123",
        "codigo_cargo": "6",
        "cargo": "DEPUTADO FEDERAL",
        "cpf": "12345678901",
        "nome": "JOÃO D´ÁVILA",
        "nome_urna": "JOÃO",
        "data_eleicao": "06/10/2024",
        "data_aceite": "",
        "data_nascimento": "",
        "sigla_unidade_federativa": "SP",
        "sigla_unidade_federativa_nascimento": "SP",
        "titulo_eleitoral": "",
        "candidatura_inserida_urna": "SIM",
        "etnia": "",
        "estado_civil": "",
        "genero": "",
        "grau_instrucao": "",
        "unidade_eleitoral": "SÃO PAULO",
        "tipo_abrangencia_eleicao": "FEDERAL",
        "tipo_eleicao": "ELEIÇÃO ORDINÁRIA",
        "tipo_agremiacao": "PARTIDO ISOLADO",
        "ocupacao": "",
        "idade_data_posse": "42",
        "codigo_etnia": "1",
        "numero_partido": "10",
        "despesa_maxima_campanha": "0",
    }


def converte_candidatura_sentinelas(extractor, dados):
    campos = list(dados)
    return extractor.convert_row(campos, campos)(list(dados.values()))


@pytest.mark.parametrize("sentinela", ["-1", "-3", "-4", "#NULO", "#NULO#", "#NE", "#NE#", "NÃO DIVULGÁVEL"])
@pytest.mark.parametrize(
    "campo",
    [
        "cpf",
        "titulo_eleitoral",
        "codigo_etnia",
        "idade_data_posse",
        "numero_partido",
        "nome",
        "nome_urna",
        "data_eleicao",
        "data_nascimento",
        "tipo_eleicao",
        "tipo_abrangencia_eleicao",
        "estado_civil",
        "genero",
        "grau_instrucao",
        "etnia",
        "tipo_agremiacao",
        "ocupacao",
        "candidatura_inserida_urna",
    ],
)
def test_ausencia_nao_monetaria_em_candidatura(candidatura_sentinelas, campo, sentinela):
    candidatura_sentinelas[campo] = sentinela
    resultado = converte_candidatura_sentinelas(CandidaturaExtractor(), candidatura_sentinelas)
    assert resultado[campo] in ("", None)
    if campo == "cpf":
        assert resultado["pessoa_uuid"] is None
    if campo == "nome":
        assert resultado["nome_exibicao"] == ""


@pytest.mark.parametrize("valor", ["-4", "0", "-1,25", "-113,14"])
def test_candidatura_preserva_valor_monetario(candidatura_sentinelas, valor):
    candidatura_sentinelas["despesa_maxima_campanha"] = valor
    assert (
        converte_candidatura_sentinelas(CandidaturaExtractor(), candidatura_sentinelas)["despesa_maxima_campanha"]
        == valor
    )


def test_cpf_real_mantem_uuid_publicado(candidatura_sentinelas):
    assert (
        str(converte_candidatura_sentinelas(CandidaturaExtractor(), candidatura_sentinelas)["pessoa_uuid"])
        == "6bf49b6a-7d3f-5b93-85ad-485a15e69d14"
    )


@pytest.mark.parametrize("valor", ["-1", "-3", "-1,00", "-3,00", "-1.00", "-3.00"])
def test_limite_de_despesa_sentinela_e_ausencia(candidatura_sentinelas, valor):
    candidatura_sentinelas["despesa_maxima_campanha"] = valor
    resultado = converte_candidatura_sentinelas(CandidaturaExtractor(), candidatura_sentinelas)
    assert resultado["despesa_maxima_campanha"] == ""
