import argparse
import csv
import os
import re
import stat
import sys
from collections import OrderedDict
from glob import glob

import rows
from rows.utils import open_compressed
from tqdm import tqdm

import settings
from extractors import (
    read_header,
    CandidaturaExtractor,
    BemDeclaradoExtractor,
    VotacaoZonaExtractor,
    PrestacaoContasReceitasExtractor,
    PrestacaoContasDespesasExtractor,
)

REGEXP_HEADER_YEAR = re.compile("([0-9]{4}.*)\.csv")


def extract_data(ExtractorClass, year_range, output_filename, base_url,
        force_redownload=False, download_only=False, censor=False):
    extractor_name = ExtractorClass.__name__.replace("Extractor", "")
    extractor = ExtractorClass(base_url, censor=censor)
    output_fobj = open_compressed(output_filename, mode="w", encoding="utf-8")
    writer = csv.DictWriter(
        output_fobj,
        fieldnames=list(extractor.schema.keys()),
    )
    writer.writeheader()
    for year in year_range:
        print(f"{extractor_name} {year}")

        print("  Downloading...", end="")
        result = extractor.download(year, force=force_redownload)
        if not result["downloaded"]:
            print(f" file has already been downloaded.")

        if not download_only:
            data = extractor.extract(year)
            for row in tqdm(data, desc="  Extracting..."):
                writer.writerow(row)

        print()
    output_fobj.close()


def create_final_headers(header_type, order_columns, final_filename):
    final_headers = {}
    filenames = sorted(
        [
            (REGEXP_HEADER_YEAR.findall(filename)[0], filename)
            for filename in glob(str(settings.HEADERS_PATH / f"{header_type}_*.csv"))
            if REGEXP_HEADER_YEAR.findall(filename)
        ]
    )
    # TODO: check if schema is according to final header. if there are diffs,
    # warn user.
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
        row_data = {"descricao": row["descricao"] or "", "nome_final": row["nome_final"]}
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
    extractors = {
        "candidatura": {
            "extractor_class": CandidaturaExtractor,
            "output_filename": settings.OUTPUT_PATH / "candidatura.csv.gz",
        },
        "bem_declarado": {
            "extractor_class": BemDeclaradoExtractor,
            "output_filename": settings.OUTPUT_PATH / "bem_declarado.csv.gz",
        },
        "votacao_zona": {
            "extractor_class": VotacaoZonaExtractor,
            "output_filename": settings.OUTPUT_PATH / "votacao_zona.csv.gz",
        },
        "receita": {
             "extractor_class": PrestacaoContasReceitasExtractor,
             "output_filename": settings.OUTPUT_PATH / "receita.csv.gz"
        },
        "despesa": {
             "extractor_class": PrestacaoContasDespesasExtractor,
             "output_filename": settings.OUTPUT_PATH / "despesa.csv.gz"
        },
    }
    # TODO: clear '##VERIFICAR BASE 1994##' so we can add 1994 too

    parser = argparse.ArgumentParser()
    parser.add_argument("type", choices=list(extractors.keys()) + ["headers", "mirror"])
    parser.add_argument("--force-redownload", action="store_true", default=False)
    parser.add_argument("--download-only", action="store_true", default=False)
    parser.add_argument("--output")
    parser.add_argument("--years", default="all")
    parser.add_argument("--use-mirror", action="store_true")
    parser.add_argument("--mirror-url", default="https://data.brasil.io/mirror/eleicoes-brasil/", help="Use the default data repository from TSE or a mirror")
    parser.add_argument("--no-censorship", action="store_true")
    args = parser.parse_args()

    if args.type == "headers":
        for header_type in extractors.keys():
            extractor = extractors[header_type]["extractor_class"]()
            final_filename = settings.HEADERS_PATH / f"{header_type}_final.csv"
            print(f"Creating {final_filename}")
            create_final_headers(header_type, extractor.order_columns, final_filename)

    elif args.type == "mirror":
        added_urls, created_paths = [], []
        base_path = settings.MIRROR_FILENAME.parent
        sha512sums_filename = (settings.DOWNLOAD_PATH / "SHA512SUMS").relative_to(base_path)
        with open(settings.MIRROR_FILENAME, mode="w") as fobj:
            fobj.write("#!/bin/bash\n")
            fobj.write("\n")
            fobj.write("set -e\n")
            fobj.write("mkdir -p data/download\n")
            fobj.write("rm -rf data/download/SHA512SUMS\n")
            fobj.write("\n")
            for header_type in sorted(extractors.keys()):
                extractor = extractors[header_type]["extractor_class"]()
                for year in extractor.year_range:
                    url = extractor.url(year)
                    if url in added_urls:
                        continue
                    else:
                        added_urls.append(url)
                    filename = extractor.filename(year)
                    download_filename = extractor.download_filename(year).relative_to(base_path)
                    save_path = str(download_filename.parent)
                    if save_path not in created_paths:
                        fobj.write(f"mkdir -p {save_path}\n")
                        created_paths.append(save_path)
                    fobj.write(f"time aria2c -s 8 -x 8 -k 1M -o '{download_filename}' '{url}'\n")
                    fobj.write(f"time s3cmd put '{download_filename}' s3://mirror/tse/{filename}\n")
                    fobj.write(f"time echo \"$(sha512sum '{download_filename}' | cut -d' ' -f 1) {filename}\" >> {sha512sums_filename}\n")
                fobj.write("\n")
        # chmod 750 {settings.MIRROR_FILENAME}
        os.chmod(settings.MIRROR_FILENAME, stat.S_IRUSR + stat.S_IWUSR + stat.S_IXUSR + stat.S_IRGRP + stat.S_IXGRP)

    else:
        for path in (settings.DATA_PATH, settings.DOWNLOAD_PATH, settings.OUTPUT_PATH):
            if not path.exists():
                path.mkdir(parents=True)

        extractor = extractors[args.type]
        if args.years == "all":
            years = extractor["extractor_class"].year_range
        else:
            years = []
            for value in args.years.split(","):
                try:
                    value = int(value)
                except ValueError:
                    pass
                if value not in extractor["extractor_class"].year_range:
                    sys.stderr.write(f"ERROR: invalid year '{value}' for {args.type}\n")
                    exit(1)
                years.append(value)

        extract_data(
            ExtractorClass=extractor["extractor_class"],
            year_range=years,
            output_filename=args.output or extractor["output_filename"],
            base_url=args.mirror_url if args.use_mirror else None,
            force_redownload=args.force_redownload,
            download_only=args.download_only,
            censor=not args.no_censorship,
        )
