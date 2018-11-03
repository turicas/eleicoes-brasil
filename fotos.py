from urllib.parse import urljoin
from pathlib import Path
from zipfile import ZipFile

from rows.utils import download_file, import_from_uri
from tqdm import tqdm


data_path = Path("fotos")
download_path = data_path / "download"
output_path = data_path / "output"
for path in (data_path, download_path, output_path):
    if not path.exists():
        path.mkdir()


def download_photos(year):
    year = str(year)
    url = f"http://agencia.tse.jus.br/estatistica/sead/eleicoes/eleicoes{year}/fotos/"
    table = import_from_uri(url)
    for row in table:
        if row.name == "Parent Directory":
            continue

        filename = download_path / year / row.name
        print(f"Downloading {filename.name}", end="")
        if filename.exists():
            print(" - downloaded already, skipping.")
        else:
            if not filename.parent.exists():
                filename.parent.mkdir()
            print()
            download_file(urljoin(url, row.name), progress=True, filename=filename)
            print(f"  saved: {filename}")

        photo_path = output_path / year
        if not photo_path.exists():
            photo_path.mkdir()
        print(f"  Exporting to: {photo_path}")
        zf = ZipFile(filename)
        for file_info in tqdm(zf.filelist, desc="Exporting pictures"):
            internal_name = file_info.filename
            internal_path = Path(internal_name)
            extension = internal_path.name.split(".")[-1].lower()
            info = internal_path.name.split(".")[0].split("_")[0]
            state, sequence_number = info[1:3], info[3:]
            new_filename = photo_path / state / f"{sequence_number}.{extension}"

            if not new_filename.parent.exists():
                new_filename.parent.mkdir()
            zfobj = zf.open(internal_name)
            with open(new_filename, mode="wb") as fobj:
                fobj.write(zfobj.read())


if __name__ == "__main__":
    for year in range(2012, 2018 + 1, 2):
        download_photos(year)
