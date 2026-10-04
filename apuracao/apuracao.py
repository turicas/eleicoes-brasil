import sys

if __name__ == "__main__":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from apuracao.cli import main

    raise SystemExit(main())

import datetime
import decimal
import json
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
    from apuracao.apresentacao import linhas_resultado  # noqa: I001 - preserva formato do isort local
    from apuracao.modelo import Candidato, Contexto, Eleitorado, Resultado, Secoes, Votos

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
        bolsonaro = next(item for item in old_data["apuracao"] if item["candidato"] == "JAIR BOLSONARO")
        lula = next(item for item in old_data["apuracao"] if item["candidato"] == "LULA")
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
        response = session.get(url, timeout=30)
        response.raise_for_status()
        response_data = response.json()
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
