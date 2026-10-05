import unittest

from extractors import BemDeclaradoExtractor


class BemDeclaradoHeadersTestCase(unittest.TestCase):
    def test_bens_uses_2022_headers_for_2026(self):
        headers = BemDeclaradoExtractor().get_headers(2026, None, "bem_candidato_2026_AC.csv")

        self.assertEqual(headers["year_fields"][0].nome_tse, "DT_GERACAO")
        self.assertEqual(headers["year_fields"][-1].nome_tse, "HH_ULT_ATUAL_BEM_CANDIDATO")
