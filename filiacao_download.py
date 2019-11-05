import io
from collections import OrderedDict

import rows
import scrapy

import settings

PARTIES = [
    "avante",
    "cidadania",
    "dc",
    "dem",
    "mdb",
    "novo",
    "patriota",
    "pcb",
    "pcdob",
    "pco",
    "pdt",
    "phs",
    "pl",
    "pmb",
    "pmn",
    "pode",
    "pp",
    "ppl",
    "pros",
    "prp",
    "prtb",
    "psb",
    "psc",
    "psd",
    "psdb",
    "psl",
    "psol",
    "pstu",
    "pt",
    "ptb",
    "ptc",
    "pv",
    "rede",
    "republicanos",
    "solidariedade",
]
STATES = [
    "ac",
    "al",
    "am",
    "ap",
    "ba",
    "ce",
    "df",
    "es",
    "go",
    "ma",
    "mg",
    "ms",
    "mt",
    "pa",
    "pb",
    "pe",
    "pi",
    "pr",
    "rj",
    "rn",
    "ro",
    "rr",
    "rs",
    "sc",
    "se",
    "sp",
    "to",
    "zz",
]

def make_filepath(party, state):
    return settings.DOWNLOAD_PATH / f"filiacao-{state}-{party}.zip"


class FiliadosFileListSpider(scrapy.Spider):
    name = "filiados-file-list"

    def start_requests(self):
        for party in PARTIES:
            if party == "solidariedade":
                party = "sd"
            for state in STATES:
                download_filename = make_filepath(party, state)
                yield scrapy.Request(
                    url=f"http://agencia.tse.jus.br/estatistica/sead/eleitorado/filiados/uf/filiados_{party}_{state}.zip",
                    meta={
                        "filename": download_filename,
                        "party": party,
                        "state": state,
                    },
                    callback=self.save_zip,
                )

    def save_zip(self, response):
        meta = response.request.meta
        with open(meta["filename"], mode="wb") as fobj:
            fobj.write(response.body)
        yield {
            "filename": meta["filename"],
            "party": meta["party"],
            "state": meta["state"],
            "url": response.url,
        }
