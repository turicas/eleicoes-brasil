import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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
        ]

        result = CandidaturaExtractor().convert_row(fields, fields)(row)

        self.assertEqual(result["cpf"], "")
        self.assertIsNone(result["pessoa_uuid"])
        self.assertEqual(result["titulo_eleitoral"], "")
        self.assertEqual(result["email"], "")
        self.assertEqual(result["nome_social"], "")
        self.assertEqual(result["codigo_genero"], "")
        self.assertEqual(result["sigla_unidade_federativa_nascimento"], "")

    def test_conversao_nome_aplica_nome_bonito_e_preserva_nome_urna(self):
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
        ]

        result = CandidaturaExtractor().convert_row(fields, fields)(row)

        self.assertEqual(result["nome"], "Luiz Inacio Lula da Silva")
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
