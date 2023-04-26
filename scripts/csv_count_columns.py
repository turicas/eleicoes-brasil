import argparse
import csv
import io


parser = argparse.ArgumentParser()
parser.add_argument("--encoding", default="iso-8859-1")
parser.add_argument("--delimiter", default=";")
parser.add_argument("csv_filename")
args = parser.parse_args()

with open(args.csv_filename, encoding=args.encoding) as fobj:
    row_length, errors = None, 0
    for row_index, line in enumerate(fobj):
        reader = csv.reader(io.StringIO(line), delimiter=args.delimiter)
        row = next(reader)
        if row_length is None:
            row_length = len(row)
            print(f"Detectado número de colunas pelo cabeçalho: {row_length}")
            continue
        elif row_length != len(row):
            errors += 1
            print(f"[{errors:06d}] Erro no registro {row_index}: {len(row)} colunas (esperado: {row_length})")
            print(f"    Linha original: {repr(line)}")
            print(f"    Registro lido: {row}")
if errors > 0:
    print(f"\nTotal de erros encontrados: {errors}.")
else:
    print("Nenhum erro com relação ao número de colunas foi encontrado.")
