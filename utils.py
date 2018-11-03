from csv import Dialect
from unicodedata import normalize

from rows.fields import DateField


class TSEDialect(Dialect):
    "CSV dialect to read files from Tribunal Superior Eleitoral"

    delimiter = ";"
    doublequote = True
    escapechar = None
    lineterminator = "\r\n"
    quotechar = '"'
    quoting = 0
    skipinitialspace = False


class PtBrDateField(DateField):
    INPUT_FORMAT = "%d/%m/%Y"


def unaccent(text):
    return normalize("NFKD", text).encode("ascii", errors="ignore").decode("ascii")
