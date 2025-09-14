"""Simplifica arquivo `Filiacao.csv` gerado pelo scraper para facilitar/agilizar cruzamento com candidaturas"""

import argparse
import csv

from rows.utils import open_compressed
from tqdm import tqdm

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv_filename", help="Like data/Filiacao.csv.gz")
    parser.add_argument("output_csv_filename", help="Like data/output/filiacao_partidaria.csv.gz")
    args = parser.parse_args()
    input_csv_filename = args.input_csv_filename
    output_csv_filename = args.output_csv_filename

    output_field_names = "situacao_eleitor data_filiacao nome titulo_eleitor cpf".split()
    with (
        open_compressed(input_csv_filename, encoding="utf-8") as in_fobj,
        open_compressed(output_csv_filename, encoding="utf-8", mode="w") as out_fobj,
    ):
        reader = csv.DictReader(in_fobj)
        writer = csv.DictWriter(out_fobj, fieldnames=output_field_names)
        writer.writeheader()
        for row in tqdm(reader):
            writer.writerow({field: row[field] for field in output_field_names})
