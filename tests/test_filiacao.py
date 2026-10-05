import asyncio
import unittest

from filiacao import FiliacaoSpider, retry_delay


class FiliacaoTestCase(unittest.TestCase):
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
