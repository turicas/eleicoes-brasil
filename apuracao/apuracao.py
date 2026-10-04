# pip install gspread==5.5.0 oauth2client==4.1.3 requests==2.27.1
import argparse
import datetime
import decimal
import json
import sys
import time
from pathlib import Path

import requests


def perc(value, total):
    return f"{100 * (value / total):02.02f}%" if total else ""


def read_data(data):
    from apuracao.adaptador2022 import Apuracao2022
    from apuracao.apresentacao import dados_legados
    from apuracao.modelo import Contexto

    return dados_legados(Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(data))


def first_sheet_rows(data):
    from apuracao.apresentacao import linhas_resultado
    from apuracao.modelo import (
        Candidato,
        Contexto,
        Eleitorado,
        Resultado,
        Secoes,
        Votos,
    )

    resultado = Resultado(
        Contexto(2022, 1, 544, 1, "br"),
        datetime.datetime.fromisoformat(data["updated_at"]),
        Secoes(data["secoes"], data["secoes_apuradas"]),
        Eleitorado(data["eleitorado"], data["eleitorado_apurado"]),
        Votos(data["total_votos"], data["total_validos"], data["total_nulos"], data["total_brancos"]),
        tuple(
            Candidato(
                row["numero"],
                row["candidato"],
                row["candidato"],
                row["vice"],
                row["votos_apurados"],
                decimal.Decimal(row["perc"].rstrip("%")) / 100,
            )
            for row in data["apuracao"]
        ),
    )
    return linhas_resultado(resultado)


def second_sheet_rows(filenames):
    lines = [
        ["Data/Hora", "% Seções apuradas", "% Bolsonaro", "% Lula"],
    ]
    for filename in sorted(filenames):
        with filename.open() as fobj:
            try:
                json_data = json.load(fobj)
            except json.decoder.JSONDecodeError as erro:
                raise ValueError(f"JSON inválido: {filename}") from erro
            old_data = read_data(json_data)
        dt = datetime.datetime.fromisoformat(filename.name.split("-r-")[1].replace(".json", ""))
        bolsonaro = [item for item in old_data["apuracao"] if item["candidato"] == "JAIR BOLSONARO"][0]
        lula = [item for item in old_data["apuracao"] if item["candidato"] == "LULA"][0]
        lines.append(
            [
                f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}",
                old_data["secoes_apuradas"] / old_data["secoes"],
                bolsonaro["votos_apurados"] / old_data["total_validos"],
                lula["votos_apurados"] / old_data["total_validos"],
            ]
        )
    return lines


def download_and_save(urls, data_path):
    session = requests.session()
    all_data = []
    for url in urls:
        response = session.get(url)
        try:
            response_data = response.json()
        except json.decoder.JSONDecodeError:
            raise
        data = read_data(response_data)

        json_filename = data_path / Path(url).name.replace(".json", f"-{data['updated_at']}.json")
        if not json_filename.exists():
            with json_filename.open(mode="w") as fobj:
                json.dump(response_data, fobj)
        all_data.append(data)
    return all_data


def make_url(codigo_eleicao, unidade_eleitoral, codigo_cargo):
    unidade_eleitoral = unidade_eleitoral.lower()
    return f"https://resultados.tse.jus.br/oficial/ele2022/{codigo_eleicao}/dados-simplificados/{unidade_eleitoral}/{unidade_eleitoral}-c{codigo_cargo:04d}-e{codigo_eleicao:06d}-r.json"


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-only", action="store_true", help="Do not update spreadsheets")
    parser.add_argument("turno", type=int, choices=[1, 2])
    parser.add_argument("tipo", choices=["presidente", "governador"])
    args = parser.parse_args()

    data_path = Path(__file__).parent / "data"
    if not data_path.exists():
        data_path.mkdir(parents=True)

    if args.turno == 1:
        sheet_id = "1Oy1mHo78313Ls1jSKayyVWW4KeqFyS94eg3LIIe1UXU"
        codigo_eleicao_main = 544
        codigo_eleicao_uf = 546
        states = (
            "AC",
            "AL",
            "AM",
            "AP",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MG",
            "MS",
            "MT",
            "PA",
            "PB",
            "PE",
            "PI",
            "PR",
            "RJ",
            "RN",
            "RO",
            "RR",
            "RS",
            "SC",
            "SE",
            "SP",
            "TO",
        )
    elif args.turno == 2:
        sheet_id = "1r9UmthUo9IPSLqNN89r_fhrsXo-igSjzCMv2sViwNZo"
        credentials_filename = "credentials/eleicoes-2022-brasil-io-sheets.json"
        codigo_eleicao_main = 545
        codigo_eleicao_uf = 547
        states = ("AL", "AM", "BA", "ES", "MS", "PB", "PE", "RO", "RS", "SC", "SE", "SP")

    if not args.print_only:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        with open(credentials_filename) as fobj:
            credentials = json.load(fobj)
            account = ServiceAccountCredentials.from_json_keyfile_dict(credentials)
        client = gspread.authorize(account)
        workbook = client.open_by_key(sheet_id)
        sheet = workbook.worksheet("Presidente")
        timeline = workbook.worksheet("LinhaDoTempo")

    if args.tipo == "presidente":
        main_url = make_url(codigo_eleicao_main, "br", 1)
        data = download_and_save([main_url], data_path)[0]
        first_rows = first_sheet_rows(data)
        if args.print_only:
            print("Won't update spreadsheet")
            for row in first_rows:
                print(row)
        else:
            sheet.clear()
            sheet.append_rows(first_rows)

        second_rows = second_sheet_rows(data_path.glob(Path(main_url).name.replace(".json", "*.json")))
        if args.print_only:
            print(f"Won't update spreadsheet: {data['title']}")
            for row in second_rows:
                print(row)
        else:
            timeline.clear()
            timeline.append_rows(second_rows)
            workbook.update_title(data["title"])

    elif args.tipo == "governador":
        import gspread

        urls = [make_url(codigo_eleicao_uf, state, 3) for state in states]
        all_data = download_and_save(urls, data_path)
        for state, data in zip(states, all_data):
            first_rows = first_sheet_rows(data)
            if args.print_only:
                print(f"Won't update spreadsheet [{state}]")
                for row in first_rows:
                    print(row)
            else:
                try:
                    state_sheet = workbook.worksheet(state.upper())
                except gspread.exceptions.WorksheetNotFound:
                    state_sheet = workbook.add_worksheet(state.upper(), 999, 10)
                state_sheet.clear()
                state_sheet.append_rows(first_rows)
            time.sleep(3)
