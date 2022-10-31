# Necessita do aria2 instalado no sistema
import csv
import json
from collections import defaultdict
from pathlib import Path

import rows
from rows.utils.download import Downloader, Download


municipios_codigos_por_uf = defaultdict(list)
municipio_por_codigo = {}
with open(Path(__file__).parent.parent / "data" / "municipios-tse.csv") as fobj:
    for row in csv.DictReader(fobj):
        municipios_codigos_por_uf[row["uf"]].append(int(row["codigo"]))
        municipio_por_codigo[int(row["codigo"])] = row["municipio"]

path = Path("data/eleicoes-2022")
if not path.exists():
    path.mkdir(parents=True)


downloader = Downloader.subclasses()["aria2c"](path=path)
for eleicao in (544, 545):
    for uf, municipios in municipios_codigos_por_uf.items():
        for cod_mun in municipios:
            url = f"https://resultados.tse.jus.br/oficial/ele2022/{eleicao}/dados/{uf.lower()}/{uf.lower()}{cod_mun:05d}-c0001-e{eleicao:06d}-v.json"
            filename = path / Path(url).name
            if not filename.exists():
                downloader.add(Download(url=url, filename=filename.name))
downloader.run()

writer = rows.utils.CsvLazyDictWriter("data/votacao-presidencial-por-municipio.csv")
for uf, municipios in municipios_codigos_por_uf.items():
    for cod_mun in municipios:
        filename_1 = path / f"{uf.lower()}{cod_mun:05d}-c0001-e{544:06d}-v.json"
        filename_2 = path / f"{uf.lower()}{cod_mun:05d}-c0001-e{545:06d}-v.json"
        with filename_1.open() as fobj:
            data_1 = json.load(fobj)
            apuracao_municipal_1 = [item for item in data_1["abr"] if item["tpabr"] == "MU"][0]
            cand_1 = apuracao_municipal_1["cand"]
            lula_1 = [item for item in cand_1 if item["n"] == "13"][0]
            bolso_1 = [item for item in cand_1 if item["n"] == "22"][0]
        with filename_2.open() as fobj:
            data_2 = json.load(fobj)
            apuracao_municipal_2 = [item for item in data_2["abr"] if item["tpabr"] == "MU"][0]
            cand_2 = apuracao_municipal_2["cand"]
            lula_2 = [item for item in cand_2 if item["n"] == "13"][0]
            bolso_2 = [item for item in cand_2 if item["n"] == "22"][0]

        writer.writerow(
            {
                "uf": uf,
                "codigo_municipio": cod_mun,
                "municipio": municipio_por_codigo[cod_mun],
                "eleitorado_total_1T": apuracao_municipal_1["e"],
                "eleitorado_total_2T": apuracao_municipal_2["e"],
                "total_votos_1T": apuracao_municipal_1["tv"],
                "total_votos_2T": apuracao_municipal_2["tv"],
                "votos_nulos_1T": apuracao_municipal_1["tvn"],
                "votos_nulos_2T": apuracao_municipal_2["tvn"],
                "votos_brancos_1T": apuracao_municipal_1["vb"],
                "votos_brancos_2T": apuracao_municipal_2["vb"],
                "votos_validos_1T": apuracao_municipal_1["vv"],
                "votos_validos_2T": apuracao_municipal_2["vv"],
                "abstencao_1T": apuracao_municipal_1["a"],
                "abstencao_2T": apuracao_municipal_2["a"],
                "perc_abstencao_1T": apuracao_municipal_1["pa"].replace(",", "."),
                "perc_abstencao_2T": apuracao_municipal_2["pa"].replace(",", "."),
                "votos_lula_1T": lula_1["vap"],
                "votos_bolso_1T": bolso_1["vap"],
                "votos_lula_2T": lula_2["vap"],
                "votos_bolso_2T": bolso_2["vap"],
                "perc_lula_1T": lula_1["pvap"].replace(",", "."),
                "perc_lula_2T": lula_2["pvap"].replace(",", "."),
                "perc_bolso_1T": bolso_1["pvap"].replace(",", "."),
                "perc_bolso_2T": bolso_2["pvap"].replace(",", "."),
            }
        )
writer.close()
