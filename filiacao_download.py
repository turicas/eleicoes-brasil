import io
from collections import OrderedDict

import rows
import scrapy

import settings


def make_filepath(party, state):
    return settings.DOWNLOAD_PATH / f"filiacao-{state}-{party}.zip"


class FiliadosFileListSpider(scrapy.Spider):
    name = 'filiados-file-list'

    start_urls = ['http://filiaweb.tse.jus.br/filiaweb/portal/relacoesFiliados.xhtml']

    def parse(self, response):
        html = response.body
        encoding = 'iso-8859-15'  # TODO: use encoding from header
        parties = rows.import_from_xpath(
            io.BytesIO(html),
            encoding='iso-8859-15',  # TODO: use encoding from header
            rows_xpath='//select[@id="partido"]/option',
            fields_xpath=OrderedDict([('code', './@value'), ('name', './text()')])
        )
        states = rows.import_from_xpath(
            io.BytesIO(html),
            encoding=encoding,
            rows_xpath='//select[@id="uf"]/option',
            fields_xpath=OrderedDict([('code', './@value'), ('name', './text()')])
        )
        link = 'http://agencia.tse.jus.br/estatistica/sead/eleitorado/filiados/uf/filiados_{party_code}_{state_code}.zip'
        for party in parties:
            for state in states:
                party_code = party.code
                if party_code == "SOLIDARIEDADE":  # Fix TSE link
                    party_code = "sd"
                url = link.format(party_code=party_code, state_code=state.code)
                download_filename = make_filepath(party_code, state.code)
                yield scrapy.Request(
                    url=url,
                    meta={
                        'filename': download_filename,
                        'party': party.name,
                        'state': state.name,
                        'url': url,
                    },
                    callback=self.save_zip,
                )

    def save_zip(self, response):
        meta = response.request.meta
        with open(meta['filename'], mode='wb') as fobj:
            fobj.write(response.body)
        yield {
            'filename': meta['filename'],
            'party': meta['party'],
            'state': meta['state'],
            'url': meta['url'],
        }
