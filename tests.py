import asyncio
import unittest
from io import StringIO

from extractors import CandidaturaExtractor
from filiacao import FiliacaoSpider


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

    def test_inicia_spider_com_a_api_atual_do_scrapy(self):
        async def collect_start_requests():
            return [item async for item in FiliacaoSpider().start()]

        requests = asyncio.run(collect_start_requests())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url, "https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/partidos")
