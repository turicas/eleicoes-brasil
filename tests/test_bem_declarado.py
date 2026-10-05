import unittest

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
