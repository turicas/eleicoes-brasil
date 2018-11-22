import io

from csv import Dialect
from unicodedata import normalize

from rows.fields import DateField


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
