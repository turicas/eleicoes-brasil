import io
import re
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
    with zipfile.ZipFile(filename1, "a") as zip1:
        zip2 = zipfile.ZipFile(filename2, "r")
        for filename in tqdm(zip2.namelist(), desc=" Merging zip files..."):
            zip1.writestr(filename, zip2.open(filename).read())


class FixQuotes(io.TextIOWrapper):
    def readline(self, *args, **kwargs):
        data = super().readline(*args, **kwargs)
        if data.endswith("\r\n"):
            newline = "\r\n"
        elif data.endswith("\n"):
            newline = "\n"
        if '";"' in data and not data.startswith('"') and not data.endswith('"'):
            data = '"' + data[: -len(newline)] + '"' + newline
        return data


PREPOSICOES_NOMES: frozenset[str] = frozenset(
    {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "e",
        "di",
        "del",
        "della",
        "delle",
        "dello",
        "degli",
        "dei",
        "du",
        "des",
        "van",
        "von",
        "der",
        "den",
        "ten",
        "ter",
        "te",
    }
)
NUMERAIS_ROMANOS_NOMES: frozenset[str] = frozenset(
    {
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "IX",
        "X",
        "XI",
        "XII",
        "XIII",
        "XIV",
        "XV",
    }
)


def nome_bonito(nome: str) -> str:
    """Formata o nome em Title Case inteligente com regras de capitalização do Português e casos especiais."""
    if not nome:
        return ""

    nome_limpo = nome.strip().replace("`", "'").replace("´", "'").replace("’", "'")
    if not nome_limpo:
        return ""

    palavras = nome_limpo.split()
    resultado: list[str] = []

    for idx, palavra in enumerate(palavras):
        palavra_upper = palavra.upper().rstrip(".,")
        if palavra_upper in NUMERAIS_ROMANOS_NOMES and re.fullmatch(r"[IVXLCDMivxlcdm]+[.,]?", palavra):
            sufixo = palavra[len(palavra_upper) :]
            resultado.append(palavra_upper + sufixo)
            continue

        if "-" in palavra:
            sub_partes = palavra.split("-")
            sub_res = []
            for sub_idx, sub_p in enumerate(sub_partes):
                sub_lower = sub_p.lower()
                if sub_idx > 0 and sub_lower in PREPOSICOES_NOMES:
                    sub_res.append(sub_lower)
                else:
                    sub_res.append(sub_p.capitalize())
            resultado.append("-".join(sub_res))
            continue

        if "'" in palavra:
            sub_partes = palavra.split("'")
            sub_res = []
            for sub_idx, sub_p in enumerate(sub_partes):
                if sub_idx == 0 and sub_p.lower() in ("d", "sant", "dell", "dall", "o", "m", "c"):
                    sub_res.append(sub_p.capitalize())
                elif sub_p:
                    sub_res.append(sub_p.capitalize())
                else:
                    sub_res.append("")
            resultado.append("'".join(sub_res))
            continue

        if re.match(r"^MC[A-ZÁÉÍÓÚÂÊÔÃÕÇ]", palavra.upper()) and len(palavra) > 2:
            resultado.append("Mc" + palavra[2:].capitalize())
            continue

        palavra_lower = palavra.lower()
        if idx > 0 and palavra_lower in PREPOSICOES_NOMES:
            resultado.append(palavra_lower)
        else:
            resultado.append(palavra.capitalize())

    return " ".join(resultado)
