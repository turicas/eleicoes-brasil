import csv
from io import BytesIO, TextIOWrapper
from pathlib import Path
from zipfile import ZipFile

import rows
import scrapy

import utils
import settings


field_map = {
    "codigo_municipio": "CODIGO DO MUNICIPIO",
    "data_cancelamento": "DATA DO CANCELAMENTO",
    "data_desfiliacao": "DATA DA DESFILIACAO",
    "data_filiacao": "DATA DA FILIACAO",
    "data_processamento": "DATA DO PROCESSAMENTO",
    "data_regularizacao": "DATA DA REGULARIZACAO",
    "motivo_cancelamento": "MOTIVO DO CANCELAMENTO",
    "nome": "NOME DO FILIADO",
    "nome_municipio": "NOME DO MUNICIPIO",
    "nome_partido": "NOME DO PARTIDO",
    "secao_eleitoral": "SECAO ELEITORAL",
    "sigla_partido": "SIGLA DO PARTIDO",
    "situacao_registro": "SITUACAO DO REGISTRO",
    "tipo_registro": "TIPO DO REGISTRO",
    "titulo_eleitoral": "NUMERO DA INSCRICAO",
    "uf": "UF",
    "zona_eleitoral": "ZONA ELEITORAL",
}


def convert_row(row):
    new = {}
    for new_name, old_name in field_map.items():
        value = utils.unaccent(row[old_name]).upper()
        if new_name.startswith("data_"):
            value = str(utils.PtBrDateField.deserialize(value) or "")
        new[new_name] = value
    return new


class FiliadosFileParserSpider(scrapy.Spider):
    name = "filiados-file-parse"

    def start_requests(self):
        links = rows.import_from_csv(settings.OUTPUT_PATH / "filiacao-links.csv")
        for row in links:
            yield scrapy.Request(
                url="file://" + str(Path(row.filename).absolute()), meta=row._asdict()
            )

    def parse(self, response):
        meta = response.request.meta
        zf = ZipFile(BytesIO(response.body))
        files = sorted(zf.filelist, key=lambda row: row.filename, reverse=True)
        csv_fobj = None
        for file_info in files:
            filename = Path(file_info.filename).name
            if filename.startswith("filiados_") and filename.endswith(".csv"):
                csv_fobj = zf.open(file_info.filename)
                break

        if csv_fobj is not None:
            reader = csv.DictReader(
                TextIOWrapper(csv_fobj, encoding="iso-8859-15"), dialect=utils.TSEDialect
            )
            for row in reader:
                yield convert_row(row)
