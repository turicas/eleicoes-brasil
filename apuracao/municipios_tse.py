import csv
import io
import zipfile
from pathlib import Path

from rows.utils.download import Downloader, Download
from rows.utils import CsvLazyDictWriter
from tqdm import tqdm


url = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2022_BR.zip"
path = Path("data")
filename = path / "votacao_secao_2022_br.zip"
if not filename.exists():
    downloader = Downloader.subclasses()["aria2c"](path=path, user_agent="Mozilla")
    downloader.add(Download(url=url, filename=filename.name))
    downloader.run()

zf = zipfile.ZipFile(filename)
file_info = [file_info for file_info in zf.filelist if file_info.filename.lower().endswith(".csv")][0]
fobj = io.TextIOWrapper(zf.open(file_info.filename), encoding="iso-8859-1")
reader = csv.DictReader(fobj, delimiter=";")
municipios = set()
for row in tqdm(reader):
    municipios.add((row["SG_UF"], row["NM_MUNICIPIO"], row["CD_MUNICIPIO"]))
writer = CsvLazyDictWriter(Path(__file__).parent.parent / "data" / "municipios-tse.csv")
for uf, municipio, codigo in sorted(municipios):
    writer.writerow({"uf": uf, "municipio": municipio, "codigo": codigo})
writer.close()
