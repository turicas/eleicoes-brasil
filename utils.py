import io
import zipfile

from csv import Dialect
from unicodedata import normalize

from rows.fields import DateField
from tqdm import tqdm


class TSEDialect(Dialect):
    "CSV dialect to read files from Tribunal Superior Eleitoral"

    delimiter = ";"
    doublequote = True
    escapechar = None
    lineterminator = "\n"
    quotechar = '"'
    quoting = 0
    skipinitialspace = False


class PtBrDateField(DateField):
    INPUT_FORMAT = "%d/%m/%Y"


def unaccent(text):
    return normalize("NFKD", text).encode("ascii", errors="ignore").decode("ascii")


def merge_zipfiles(filename1, filename2):
    with zipfile.ZipFile(filename1, 'a') as zip1:
        zip2 = zipfile.ZipFile(filename2, 'r')
        for filename in tqdm(zip2.namelist(), desc=" Merging zip files..."):
            zip1.writestr(filename, zip2.open(filename).read())



class FixQuotes(io.TextIOWrapper):
    def readline(self, *args, **kwargs):
        data = super().readline(*args, **kwargs)
        if data.endswith('\r\n'):
            newline = '\r\n'
        elif data.endswith('\n'):
            newline = '\n'
        if '";"' in data and not data.startswith('"') and not data.endswith('"'):
            data = '"' + data[:- len(newline)] + '"' + newline
        return data
