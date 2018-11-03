from pathlib import Path


BASE_PATH = Path(__file__).parent.absolute()
DATA_PATH = BASE_PATH / "data"
DOWNLOAD_PATH = DATA_PATH / "download"
OUTPUT_PATH = DATA_PATH / "output"
HEADERS_PATH = BASE_PATH / "headers"

for path in (DATA_PATH, DOWNLOAD_PATH, OUTPUT_PATH):
    if not path.exists():
        path.mkdir()
