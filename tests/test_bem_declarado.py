import unittest

import pytest

from extractors import BemDeclaradoExtractor


class BemDeclaradoExtractorTestCase(unittest.TestCase):
    def test_converte_valor_com_overflow_de_hashes_em_vazio(self):
        # Exemplo real extraído de `bem_candidato_2026_DF.csv`: quando o número não cabe no campo, o TSE exporta o
        # valor como "##################".
        fields = ["ano", "numero_sequencial", "sigla_unidade_federativa", "tipo", "valor"]
        row = ["2026", "70002551323", "DF", "Direito de autor, de inventor e patente", "##################"]
        result = BemDeclaradoExtractor().convert_row(fields, fields)(row)
        self.assertEqual(result["valor"], "")

    def test_converte_valor_normal_com_virgula_decimal(self):
        fields = ["ano", "numero_sequencial", "sigla_unidade_federativa", "tipo", "valor"]
        row = ["2026", "250002541095", "SP", "Ações (inclusive as provenientes de linha telefônica)", "37964,16"]
        result = BemDeclaradoExtractor().convert_row(fields, fields)(row)
        self.assertEqual(result["valor"], "37964.16")


class BemDeclaradoHeadersTestCase(unittest.TestCase):
    def test_bens_uses_2022_headers_for_2026(self):
        headers = BemDeclaradoExtractor().get_headers(2026, None, "bem_candidato_2026_AC.csv")

        self.assertEqual(headers["year_fields"][0].nome_tse, "DT_GERACAO")
        self.assertEqual(headers["year_fields"][-1].nome_tse, "HH_ULT_ATUAL_BEM_CANDIDATO")


def converte_bem_sentinelas(extractor, dados):
    campos = list(dados)
    return extractor.convert_row(campos, campos)(list(dados.values()))


@pytest.mark.parametrize("valor", ["-4", "0", "-1,25", "-113,14", "-36,92", "-38101,07"])
def test_bem_preserva_negativos_e_zero(valor):
    bem = {"ano": "2024", "numero_sequencial": "123", "sigla_unidade_federativa": "SP", "valor": valor}
    assert converte_bem_sentinelas(BemDeclaradoExtractor(), bem)["valor"] == valor.replace(",", ".")


@pytest.mark.parametrize("sentinela", ["-1", "-3", "-4", "#NULO#", "#NE#"])
@pytest.mark.parametrize("campo", ["codigo_tipo", "tipo", "descricao", "ordem", "sigla_unidade_federativa"])
def test_ausencia_nao_monetaria_em_bem(campo, sentinela):
    bem = {"ano": "2024", "numero_sequencial": "123", "sigla_unidade_federativa": "SP", "valor": "42,00"}
    bem[campo] = sentinela
    resultado = converte_bem_sentinelas(BemDeclaradoExtractor(), bem)
    assert resultado[campo] == ""
    assert resultado["valor"] == "42.00"


@pytest.mark.parametrize("valor", ["#NULO#", "#NE#", "##################", ""])
def test_bem_valor_sem_informacao_e_vazio(valor):
    bem = {"ano": "2024", "numero_sequencial": "123", "sigla_unidade_federativa": "SP", "valor": valor}
    assert converte_bem_sentinelas(BemDeclaradoExtractor(), bem)["valor"] == ""


@pytest.mark.parametrize("valor", ["-1", "-3", "-1,00", "-3,00", "-1.00", "-3.00"])
def test_valor_sentinela_em_bem_e_ausencia(valor):
    bem = {"ano": "2024", "numero_sequencial": "123", "sigla_unidade_federativa": "SP", "valor": valor}
    assert converte_bem_sentinelas(BemDeclaradoExtractor(), bem)["valor"] == ""
