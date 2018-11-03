import argparse
import datetime
import re
from collections import OrderedDict
from glob import glob

import rows
from rows.utils import CsvLazyDictWriter
from tqdm import tqdm

import settings
from extractors import (
    read_header,
    CandidaturaExtractor,
    BemDeclaradoExtractor,
    VotacaoZonaExtractor,
)

REGEXP_HEADER_YEAR = re.compile("([0-9]{4}.*)\.csv")


def extract_data(ExtractorClass, year_range, output_filename, force_redownload=False):
    extractor_name = ExtractorClass.__name__.replace("Extractor", "")
    extractor = ExtractorClass()
    writer = CsvLazyDictWriter(output_filename)
    for year in year_range:
        print(f"{extractor_name} {year}")

        print("  Downloading...", end="")
        result = extractor.download(year, force=force_redownload)
        if not result["downloaded"]:
            print(f" file has already been downloaded.")

        data = extractor.extract(year)
        for row in tqdm(data, desc="  Extracting..."):
            writer.writerow(row)


def create_final_headers(header_type, order_columns, final_filename):
    final_headers = {}
    filenames = sorted(
        [
            (REGEXP_HEADER_YEAR.findall(filename)[0], filename)
            for filename in glob(str(settings.HEADERS_PATH / f"{header_type}-*.csv"))
            if REGEXP_HEADER_YEAR.findall(filename)
        ]
    )
    for index, (header_year, filename) in enumerate(filenames):
        header = read_header(filename)
        for row in header:
            if not row.nome_final:
                continue
            if row.nome_final not in final_headers:
                row_data = row._asdict()
                if index > 0:
                    row_data["introduced_on"] = header_year
                row_data["original_names"] = [(header_year, row_data.pop("nome_tse"))]
                final_headers[row.nome_final] = row_data
            else:
                original_name = (header_year, row.nome_tse)
                original_names = final_headers[row.nome_final]["original_names"]
                should_add = True
                for original in original_names:
                    if original[1] == original_name[1]:
                        should_add = False
                        break
                if should_add:
                    original_names.append(original_name)

    table = rows.Table(
        fields=OrderedDict(
            [
                ("nome_final", rows.fields.TextField),
                ("descricao", rows.fields.TextField),
            ]
        )
    )

    header_list = sorted(
        final_headers.values(), key=lambda row: order_columns(row["nome_final"])
    )
    for row in header_list:
        row_data = {"descricao": row["descricao"], "nome_final": row["nome_final"]}
        introduced_on = row.get("introduced_on", None)
        original_names = ", ".join(
            f"{item[1]} ({item[0]})" for item in row.get("original_names")
        )
        row_data["descricao"] += f". Aparece no TSE como: {original_names}"
        if introduced_on:
            row_data["descricao"] += f". Coluna adicionada em {introduced_on}"
        if row_data["descricao"][-1] != ".":
            row_data["descricao"] += "."
        table.append(row_data)
    rows.export_to_csv(table, final_filename)


if __name__ == "__main__":
    now = datetime.datetime.now()
    if now >= datetime.datetime(now.year, 10, 8, 0, 0, 0):
        final_votation_year = now.year + 1
    else:
        final_votation_year = now.year
    extractors = {
        "candidatura": {
            "years": range(1996, now.year + 1, 2),
            "extractor_class": CandidaturaExtractor,
            "output_filename": settings.OUTPUT_PATH / "candidatos.csv.xz",
        },
        "bemdeclarado": {
            "years": range(2006, now.year + 1, 2),
            "extractor_class": BemDeclaradoExtractor,
            "output_filename": settings.OUTPUT_PATH / "bemdeclarado.csv.xz",
        },
        "votacao-zona": {
            "years": range(1996, final_votation_year, 2),
            "extractor_class": VotacaoZonaExtractor,
            "output_filename": settings.OUTPUT_PATH / "votacao-zona.csv.xz",
        },
    }
    # TODO: clear '##VERIFICAR BASE 1994##' so we can add 1994 too

    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=list(extractors.keys()) + ["headers"])
    parser.add_argument("--force-redownload", action="store_true", default=False)
    parser.add_argument("--output")
    parser.add_argument("--years", default="all")
    args = parser.parse_args()

    if args.type == "headers":
        for header_type in extractors.keys():
            extractor = extractors[header_type]["extractor_class"]()
            final_filename = settings.HEADERS_PATH / f"{header_type}-final.csv"
            print(f"Creating {final_filename}")
            create_final_headers(header_type, extractor.order_columns, final_filename)

    else:
        extractor = extractors[args.type]
        if args.years == "all":
            years = extractor["years"]
        else:
            years = [int(value) for value in args.years.split(",")]
        force_redownload = args.force_redownload
        for path in (settings.DATA_PATH, settings.DOWNLOAD_PATH, settings.OUTPUT_PATH):
            if not path.exists():
                path.mkdir()

        extract_data(
            extractor["extractor_class"],
            years,
            args.output or extractor["output_filename"],
            force_redownload=force_redownload,
        )
