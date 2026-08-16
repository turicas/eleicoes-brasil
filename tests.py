import asyncio
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import settings
from divulgacandcontas import url_candidatura
from extractors import CandidaturaExtractor
from filiacao import FiliacaoSpider, retry_delay


class DivulgaCandContasTestCase(unittest.TestCase):
    def test_gera_url_de_candidatura_municipal(self):
        candidatura = {
            "ano": "2024",
            "codigo_eleicao": "619",
            "numero_sequencial": "160001990123",
            "sigla_unidade_federativa": "PR",
            "sigla_unidade_eleitoral": "75353",
        }

        self.assertEqual(
            url_candidatura(candidatura),
            "https://divulgacandcontas.tse.jus.br/divulga/#/candidato/SUL/PR/2045202024/160001990123/2024/75353",
        )

    def test_gera_url_de_candidatura_estadual_e_federal(self):
        estadual = {
            "ano": "2022",
            "codigo_eleicao": "546",
            "numero_sequencial": "260001693738",
            "sigla_unidade_federativa": "SE",
            "sigla_unidade_eleitoral": "SE",
        }
        federal = {
            "ano": "2022",
            "codigo_eleicao": "545",
            "numero_sequencial": "280001618036",
            "sigla_unidade_federativa": "BR",
            "sigla_unidade_eleitoral": "BR",
        }

        self.assertEqual(url_candidatura(estadual).split("/")[6], "NORDESTE")
        self.assertIn("/2040602022/", url_candidatura(estadual))
        self.assertEqual(url_candidatura(federal).split("/")[6], "BRASIL")
        self.assertIn("/2040602022/", url_candidatura(federal))

    def test_exige_id_do_divulgacand_em_eleicao_suplementar(self):
        candidatura = {
            "ano": "2014",
            "tipo_eleicao": "ELEICAO SUPLEMENTAR",
            "numero_sequencial": "270000010435",
            "sigla_unidade_federativa": "TO",
            "sigla_unidade_eleitoral": "TO",
        }

        with self.assertRaisesRegex(ValueError, "codigo_eleicao_divulgacand"):
            url_candidatura(candidatura)
        self.assertIn("/91575/", url_candidatura(candidatura, codigo_eleicao_divulgacand="91575"))

    def test_rejeita_campos_ausentes_e_unidade_federativa_desconhecida(self):
        with self.assertRaisesRegex(ValueError, "numero_sequencial"):
            url_candidatura(
                {
                    "ano": "2024",
                    "codigo_eleicao": "1",
                    "sigla_unidade_federativa": "PR",
                    "sigla_unidade_eleitoral": "3",
                }
            )
        with self.assertRaisesRegex(ValueError, "unidade federativa"):
            url_candidatura(
                {
                    "ano": "2024",
                    "codigo_eleicao": "1",
                    "numero_sequencial": "2",
                    "sigla_unidade_federativa": "XX",
                    "sigla_unidade_eleitoral": "3",
                }
            )


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
                    return SimpleNamespace(uri=temp_fobj.name)

                with patch("extractors.download_file", side_effect=fake_download_file):
                    extractor.download(2026, force=True)

                self.assertEqual(len(chamadas), 1)
                self.assertIn("cdn.tse.jus.br", chamadas[0])
                self.assertIn("_=", chamadas[0])
            finally:
                settings.DOWNLOAD_PATH = orig_path

    def test_calcula_espera_exponencial_para_retries(self):
        self.assertEqual(retry_delay(1, base=2, maximum=30), 2)
        self.assertEqual(retry_delay(2, base=2, maximum=30), 4)
        self.assertEqual(retry_delay(5, base=2, maximum=30), 30)

    def test_inicia_spider_com_a_api_atual_do_scrapy(self):
        async def collect_start_requests():
            return [item async for item in FiliacaoSpider().start()]

        requests = asyncio.run(collect_start_requests())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url, "https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/partidos")
