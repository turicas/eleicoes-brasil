import io
import os
import random
import string
import tempfile
from collections import OrderedDict
from urllib.parse import urljoin
from pathlib import Path

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
    "up",
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


def random_string(length):
    return "".join(random.choice(string.ascii_letters) for _ in range(length))

def random_file():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix="txt")
    with open(tmp.name, mode="w") as fobj:
        fobj.write("test\n")
    return Path(tmp.name)


class FiliadosFileListSpider(scrapy.Spider):
    name = "filiados-file-list"
    base_url = "http://agencia.tse.jus.br/estatistica/sead/"

    def filename(self, party, state):
        return f"eleitorado/filiados/uf/filiados_{party}_{state}.zip"

    def download_filename(self, party, state):
        return settings.DOWNLOAD_PATH / self.filename(party, state)

    def url(self, party, state):
        return urljoin(self.base_url, self.filename(party, state))

    def start_requests(self):
        for party in PARTIES:
            for state in STATES:
                download_filename = self.download_filename(party, state)
                url = self.url(party, state)
                if not download_filename.exists():
                    yield scrapy.Request(
                        url=url,
                        meta={
                            "filename": download_filename,
                            "party": party,
                            "state": state,
                        },
                        callback=self.save_zip,
                    )
                else:
                    # Hack to yield an already downloaded file from here
                    temp_filename = random_file()
                    yield scrapy.Request(
                       "file://" + str(temp_filename),
                        meta={
                            "row": {
                                "filename": download_filename,
                                "party": party,
                                "state": state,
                                "url": url,
                            },
                            "dont_cache": True,
                            "temp_filename": temp_filename,
                        },
                        callback=self.yield_row,
                    )

    def yield_row(self, response):
        meta = response.meta
        yield meta["row"]
        os.unlink(meta["temp_filename"])

    def save_zip(self, response):
        meta = response.request.meta
        filename = meta["filename"]
        if not filename.parent.exists():
            filename.parent.mkdir(parents=True)
        with open(filename, mode="wb") as fobj:
            fobj.write(response.body)
        yield {
            "filename": meta["filename"],
            "party": meta["party"],
            "state": meta["state"],
            "url": response.url,
        }
