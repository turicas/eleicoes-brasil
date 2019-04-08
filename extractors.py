import csv
import datetime
import re
from functools import lru_cache
from io import StringIO, TextIOWrapper
from pathlib import Path
from shutil import move as move_file
from urllib.parse import urljoin
from zipfile import ZipFile

import rarfile
import rows
from rows.utils import download_file

import utils
import settings


REGEXP_NUMBERS = re.compile("([0-9]+)")
REGEXP_WRONGQUOTE = re.compile(r';"([^;\r\n]+"[^;\r\n]*)";')
MAP_CODIGO_CARGO = {
    "PRESIDENTE": "1",
    "VICE-PRESIDENTE": "2",
    "GOVERNADOR": "3",
    "VICE-GOVERNADOR": "4",
    "SENADOR": "5",
    "DEPUTADO FEDERAL": "6",
    "DEPUTADO ESTADUAL": "7",
    "DEPUTADO DISTRITAL": "8",
    "1o SUPLENTE SENADOR": "9",
    "2o SUPLENTE SENADOR": "10",
    "PREFEITO": "11",
    "VICE-PREFEITO": "12",
    "VEREADOR": "13",
}
MAP_DESCRICAO_CARGO = {
    # Must change
    "1o SUPLENTE": "1o SUPLENTE SENADOR",
    "1O SUPLENTE": "1o SUPLENTE SENADOR",
    "1º SUPLENTE SENADOR": "1o SUPLENTE SENADOR",
    "1º SUPLENTE": "1o SUPLENTE SENADOR",
    "2o SUPLENTE": "2o SUPLENTE SENADOR",
    "2O SUPLENTE": "2o SUPLENTE SENADOR",
    "2º SUPLENTE SENADOR": "2o SUPLENTE SENADOR",
    "2º SUPLENTE": "2o SUPLENTE SENADOR",
    "VICE PREFEITO": "VICE-PREFEITO",
    "1O SUPLENTE SENADOR": "1o SUPLENTE SENADOR",
    "2O SUPLENTE SENADOR": "2o SUPLENTE SENADOR",
    # Do not change
    "PRESIDENTE": "PRESIDENTE",
    "VICE-PRESIDENTE": "VICE-PRESIDENTE",
    "GOVERNADOR": "GOVERNADOR",
    "VICE-GOVERNADOR": "VICE-GOVERNADOR",
    "SENADOR": "SENADOR",
    "DEPUTADO FEDERAL": "DEPUTADO FEDERAL",
    "DEPUTADO ESTADUAL": "DEPUTADO ESTADUAL",
    "DEPUTADO DISTRITAL": "DEPUTADO DISTRITAL",
    "1o SUPLENTE SENADOR": "1o SUPLENTE SENADOR",
    "2o SUPLENTE SENADOR": "2o SUPLENTE SENADOR",
    "PREFEITO": "PREFEITO",
    "VICE-PREFEITO": "VICE-PREFEITO",
    "VEREADOR": "VEREADOR",
}
NOW = datetime.datetime.now()
if NOW >= datetime.datetime(NOW.year, 10, 8, 0, 0, 0):
    FINAL_VOTATION_YEAR = NOW.year + 1
else:
    FINAL_VOTATION_YEAR = NOW.year


@lru_cache()
def read_header(filename, encoding="utf-8"):
    filename = Path(filename)
    return rows.import_from_csv(filename, encoding=encoding)


def fix_cargo(codigo_cargo, descricao_cargo):
    if codigo_cargo == "91":
        # It's a question on a plebiscite
        descricao_cargo, pergunta = "OPCAO PLEBISCITO", descricao_cargo

    else:
        # Normalize descricao_cargo spelling and fix codigo_cargo accordingly
        descricao_cargo = MAP_DESCRICAO_CARGO[descricao_cargo]
        codigo_cargo = MAP_CODIGO_CARGO[descricao_cargo]
        pergunta = ""
    return codigo_cargo, descricao_cargo, pergunta


def fix_nome(value):
    value = value.replace("`", "'").replace("' ", "'")
    if value[0] in "',.]":
        value = value[1:]
    return value


def fix_sigla_uf(value):
    return value.replace("BH", "BA").replace("LB", "ZZ")


def fix_valor(value):
    return value.replace(",", ".")


def fix_cpf(value):
    value = "".join(REGEXP_NUMBERS.findall(value))
    if len(value) < 11:
        value = "0" * (11 - len(value)) + value
    return value


def fix_titulo_eleitoral(value):
    return "".join(REGEXP_NUMBERS.findall(value))


def get_organization(internal_filename, year):
    if year == 2010:
        if 'Receitas' in internal_filename:
            return internal_filename.split('Receitas')[1].replace('.txt', '').lower()
        else:
            return internal_filename.split('Despesas')[1].replace('.txt', '').lower()
    elif year in (2008, 2014, 2016):
        return internal_filename.split('_')[1]
    elif year == 2006 or year == 2004 or year == 2002:
        return 'comites' if 'Comit' in internal_filename else 'candidatos'
    elif year == 2012:
        return internal_filename.split('_')[1]


class Extractor:

    base_url = "http://agencia.tse.jus.br/estatistica/sead/odsele/"
    encoding = "latin-1"

    def __init__(self, base_url=None):
        if base_url is not None:
            self.base_url = base_url

    def download(self, year, force=False):
        filename = self.filename(year)
        if not force and filename.exists():  # File has already been downloaded
            return {"downloaded": False, "filename": filename}

        url = self.url(year)
        file_data = download_file(url, progress=True)
        move_file(file_data.uri, filename)
        return {"downloaded": True, "filename": filename}

    def extract_state_from_filename(self, filename):
        """ 'bem_candidato_2006_AC.csv' -> 'AC' """
        return filename.split(".")[0].split("_")[-1]

    def fix_fobj(self, fobj):
        "Fix file-like object, if needed"
        return fobj

    def extract(self, year):
        filename = self.filename(year)
        zfile = ZipFile(filename)
        for file_info in zfile.filelist:
            internal_filename = file_info.filename
            if not self.valid_filename(internal_filename):
                continue
            fobj = TextIOWrapper(
                zfile.open(internal_filename),
                encoding=self.encoding
            )
            fobj = self.fix_fobj(fobj)
            reader = csv.reader(fobj, dialect=utils.TSEDialect)
            header_meta = self.get_headers(year, filename, internal_filename)
            year_fields = [
                field.nome_final or field.nome_tse
                for field in header_meta["year_fields"]
            ]
            final_fields = [
                field.nome_final
                for field in header_meta["final_fields"]
                if field.nome_final
            ]
            convert_function = self.convert_row(year_fields, final_fields)
            for index, row in enumerate(reader):
                if index == 0 and "ANO_ELEICAO" in row:
                    # It's a header, we should skip it as a data row but
                    # use the information to get field ordering (better
                    # trust it then our headers files, TSE may change the
                    # order)
                    field_map = {
                        field.nome_tse: field.nome_final or field.nome_tse
                        for field in header_meta["year_fields"]
                    }
                    year_fields = [field_map[field_name] for field_name in row]
                    convert_function = self.convert_row(year_fields, final_fields)
                    continue

                data = convert_function(row)
                if data is not None:
                    yield data


class CandidaturaExtractor(Extractor):

    year_range = tuple(range(1996, NOW.year + 1, 2))

    def url(self, year):
        return urljoin(self.base_url, f"consulta_cand/consulta_cand_{year}.zip")

    def filename(self, year):
        return settings.DOWNLOAD_PATH / f"candidatura-{year}.zip"

    def valid_filename(self, filename):
        name = filename.lower()
        return name.startswith("consulta_cand_") and "_brasil.csv" not in name

    def fix_fobj(self, fobj):
        """Fix wrong-escaped lines from the TSE's CSVs

        Files with error:
        - consulta_cand_2000_RS.txt
        - consulta_cand_2008_PR.txt
        - consulta_cand_2008_SP.txt
        """

        text = fobj.read()
        for fix in REGEXP_WRONGQUOTE.findall(text):
            if any('"' in part for part in fix.split('""')):
                text = text.replace(fix, fix.replace('"', '""'))

        return StringIO(text)

    def get_headers(self, year, filename, internal_filename):
        uf = self.extract_state_from_filename(internal_filename)
        if year == 1994:
            if uf != "PI":
                uf = "BR"
            header_year = f"1994-{uf}"
        elif 1996 <= year <= 2010:
            header_year = "1996"
        elif year == 2012:
            header_year = "2012"
        elif 2014 <= year <= 2018:
            header_year = "2018"
        else:
            raise ValueError(f"Unrecognized year ({year}, {uf})")
        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"candidatura-{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / "candidatura-final.csv"
            ),
        }

    def convert_row(self, row_field_names, final_field_names):
        # TODO: may add validators for these converter methods

        def convert(row_data):
            if len(row_data) == 1 and "elapsed" in row_data[0].lower():
                return None

            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, "").strip()
                if value in ("#NULO", "#NULO#", "#NE#"):
                    value = ""
                new[key] = value = utils.unaccent(value).upper()

            # TODO: fix data_nascimento (dd/mm/yyyy, dd/mm/yy, yyyymmdd, xx/xx/)
            # TODO: fix situacao
            # TODO: fix totalizacao
            new["cpf"] = fix_cpf(new["cpf"])
            new["nome"] = fix_nome(new["nome"])
            new["sigla_uf"] = fix_sigla_uf(new["sigla_uf"])
            new["sigla_uf_nascimento"] = fix_sigla_uf(new["sigla_uf_nascimento"])
            new["titulo_eleitoral"] = fix_titulo_eleitoral(new["titulo_eleitoral"])
            new["codigo_cargo"], new["descricao_cargo"], new["pergunta"] = fix_cargo(
                new["codigo_cargo"], new["descricao_cargo"]
            )

            return new

        return convert

    def order_columns(self, name):
        """Order columns according to a (possible) normalization

        The order is:
        - Election
        - Election round
        - Geographic Area
        - Person
        - Party
        - Application
        """

        if "eleicao" in name and ("idade" not in name and "reeleicao" not in name):
            value = 0
        elif "turno" in name:
            value = 1
        elif name.endswith("_ue") or name == "sigla_uf":
            value = 2
        elif "titulo" in name:
            value = 3
        elif (
            "coligacao" in name
            or "legenda" in name
            or "partido" in name
            or "agremiacao" in name
        ):
            value = 4
        elif (
            "candidat" in name
            or "cargo" in name
            or "reeleicao" in name
            or "despesa" in name
            or "declara" in name
            or "urna" in name
            or "posse" in name
            or name == "idade_data_eleicao"
            or name == "numero_sequencial"
        ):
            value = 5
        else:
            value = 3
        return value, name


class BemDeclaradoExtractor(Extractor):

    year_range = tuple(range(2006, NOW.year + 1, 2))

    def url(self, year):
        return urljoin(self.base_url, f"bem_candidato/bem_candidato_{year}.zip")

    def filename(self, year):
        return settings.DOWNLOAD_PATH / f"bem-declarado-{year}.zip"

    def valid_filename(self, filename):
        name = filename.lower()
        return name.startswith("bem_candidato") and "_brasil.csv" not in name

    def get_headers(self, year, filename, internal_filename):
        uf = self.extract_state_from_filename(internal_filename)
        if 2006 <= year <= 2012:
            header_year = "2006"
        elif 2014 <= year <= 2018:
            header_year = "2014"
        else:
            raise ValueError("Unrecognized year")

        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"bem-declarado-{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / "bem-declarado-final.csv"
            ),
        }

    def convert_row(self, row_field_names, final_field_names):

        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, "").strip()
                if value in ("#NULO", "#NULO#", "#NE#"):
                    value = ""
                new[key] = value = utils.unaccent(value).upper()

            new["sigla_uf"] = fix_sigla_uf(new["sigla_uf"])
            new["valor"] = fix_valor(new["valor"])

            return new

        return convert

    def order_columns(self, name):
        """Order columns according to a (possible) normalization

        The order is:
        - Election
        - Geographic Area
        - Application
        - Declared Item
        """

        if name.endswith("_eleicao"):
            value = 0
        elif name.endswith("_ue") or name == "sigla_uf":
            value = 1
        elif name == "numero_sequencial":
            value = 2
        else:
            value = 3
        return value, name


class VotacaoZonaExtractor(Extractor):

    year_range = tuple(range(1996, FINAL_VOTATION_YEAR, 2))

    def url(self, year):
        return urljoin(self.base_url, f"votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip")

    def filename(self, year):
        return settings.DOWNLOAD_PATH / f"votacao-zona-{year}.zip"

    def valid_filename(self, filename):
        return filename.startswith("votacao_candidato_munzona_")

    def get_headers(self, year, filename, internal_filename):
        uf = self.extract_state_from_filename(internal_filename)
        if year < 2014:
            header_year = "1994"
        elif 2014 <= year <= 2016:
            header_year = "2014"
        elif year == 2018:
            header_year = "2018"
        else:
            raise ValueError("Unrecognized year")
        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"votacao-zona-{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / "votacao-zona-final.csv"
            ),
        }

    def convert_row(self, row_field_names, final_field_names):

        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, "").strip()
                if value in ("#NULO", "#NULO#", "#NE#"):
                    value = ""
                new[key] = value = utils.unaccent(value).upper()

            new["sigla_uf"] = fix_sigla_uf(new["sigla_uf"])
            new["nome"] = fix_nome(new["nome"])
            new["codigo_cargo"], new["descricao_cargo"], _ = fix_cargo(
                new["codigo_cargo"], new["descricao_cargo"]
            )

            return new

        return convert

    def order_columns(self, name):
        """Order columns according to a (possible) normalization

        The order is:
        - Election
        - Election Round
        - Geographic Area
        - Party
        - Application
        - Votes
        """

        if name.endswith("_eleicao"):
            value = 0
        elif name.endswith("_turno"):
            value = 1
        elif (
            name.endswith("_ue") or name.endswith("_uf") or name.endswith("_municipio")
        ):
            value = 2
        elif (
            name.endswith("_legenda")
            or name.endswith("_coligacao")
            or name.endswith("_partido")
        ):
            value = 3
        elif "zona" in name or "voto" in name:
            value = 5
        else:
            value = 4
        return value, name


class PrestacaoContasExtractor(Extractor):

    year_range = (2002, 2004, 2006, 2008, 2010, 2012, 2014, '2014-suplementar', 2016, "2016-suplementar", 2018)

    def url(self, year):
        urls = {
            2002: f"contas_2002",
            2004: f"contas_2004",
            2006: f"contas_2006",
            2008: f"contas_2008",
            2010: f"contas_2010",
            2012: f"final_2012",
            2014: f"final_2014",
            "2014-suplementar": "contas_final_sup_2014",
            2016: f"contas_final_2016",
            "2016-suplementar": "contas_final_sup_2016",
            2018: "de_contas_eleitorais_candidatos_2018",
        }
        return urljoin(self.base_url, f"prestacao_contas/prestacao_{urls[year]}.zip")

    def _get_compressed_fobjs(self, filename, year):
        with open(filename, mode="rb") as fobj:
            first_bytes = fobj.read(10)
        if first_bytes.startswith(b"PK\x03\x04"):  # Zip archive
            zfile = ZipFile(str(filename))
            filelist = [fn.filename for fn in zfile.filelist]
            opener = zfile
        elif first_bytes.startswith(b"Rar!"):
            rarobj = rarfile.RarFile(str(filename))
            filelist = rarobj.namelist()
            opener = rarobj
        else:
            raise RuntimeError(f"Could not extract archive '{filename}'")

        valid_names = []
        fobjs = []
        for internal_filename in filelist:
            if not self.valid_filename(internal_filename, year=year):
                continue
            fobjs.append(opener.open(internal_filename))
            valid_names.append(internal_filename)

        return fobjs, valid_names

    def fix_fobj(self, fobj, year):
        if year == 2004 or year == 2008:
            fobj = utils.FixQuotes(fobj, encoding=self.encoding)
        else:
            fobj = TextIOWrapper(fobj, encoding=self.encoding)

        return fobj

    def filename(self, year):
        return settings.DOWNLOAD_PATH / f"prestacao-contas-{year}.zip"

    def get_headers(self, year, filename, internal_filename):
        if str(year).endswith("suplementar"):
            # TODO: check if 2016-suplementar should use the same headers as
            # 2014
            header_year = year
            year = 2014
        else:
            header_year = str(year)

        org = get_organization(internal_filename, year)

        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"{self.type_mov}-{org}-{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / f"{self.type_mov}-final.csv"
            ),
        }

    def convert_row(self, row_field_names, final_field_names, year):

        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, "").strip()
                if value in ("#NULO", "#NULO#", "#NE#"):
                    value = ""
                new[key] = value = utils.unaccent(value).upper()

            # TODO: may fix situacao_cadastral
            new['ano_eleicao'] = year
            return new

        return convert

    def valid_filename(self, filename, year):
        filename = filename.lower()
        year = str(year)

        is_type_mov = self.type_mov in filename
        extension = filename.endswith('.csv') or filename.endswith('.txt')
        not_brasil = 'br' not in filename
        is_2008 = year == '2008'
        is_suplementar = 'sup' not in filename
        is_year_suplementar = year.endswith('suplementar')

        return (is_type_mov and extension and (((not_brasil or is_2008) and
                is_suplementar) or is_year_suplementar))

    def order_columns(self, name):
        """Order columns according to a (possible) normalization

        The order is:
        - Geographic Area
        - Person
        - Party
        - Donator
        - Revenue
        """

        if "uf" in name or "ue" in name or name == 'municipio':
            value = 0
        elif "sequencial" in name or 'candidato' in name:
            value = 1
        elif 'partido' in name or 'comite' in name:
            value = 2
        elif 'doador' in name or 'fornecedor' in name:
            value = 3
        elif 'receita' in name or 'despesa' in name or 'recurso' in name:
            value = 4
        else:
            value = 5

        return value, name

    def extract(self, year):
        filename = self.filename(year)
        fobjs, internal_filenames = self._get_compressed_fobjs(
                filename,
                year,
        )
        for fobj, internal_filename in zip(fobjs, internal_filenames):
            fobj = self.fix_fobj(fobj, year)
            dialect = csv.Sniffer().sniff(fobj.read(1024))
            fobj.seek(0)
            reader = csv.reader(fobj, dialect=dialect)
            header_meta = self.get_headers(
                year,
                filename,
                internal_filename,
            )
            year_fields = [
                field.nome_final or field.nome_tse
                for field in header_meta["year_fields"]
            ]
            final_fields = [
                field.nome_final
                for field in header_meta["final_fields"]
                if field.nome_final
            ]

            # Add year to final csv
            final_fields = ['ano_eleicao'] + final_fields
            convert_function = self.convert_row(year_fields, final_fields, year)
            for index, row in enumerate(reader):
                if index == 0 and ("UF" in row or
                                   "SG_UE_SUP" in row or
                                   "SITUACAOCADASTRAL" in row):
                    # It's a header, we should skip it as a data row but
                    # use the information to get field ordering (better
                    # trust it then our headers files, TSE may change the
                    # order)
                    field_map = {
                        field.nome_tse: field.nome_final or field.nome_tse
                        for field in header_meta["year_fields"]
                    }
                    year_fields = [field_map[field_name.strip()] for field_name in row]
                    convert_function = self.convert_row(year_fields, final_fields, year)
                    continue

                yield convert_function(row)


class PrestacaoContasReceitasExtractor(PrestacaoContasExtractor):

    type_mov = "receita"


class PrestacaoContasDespesasExtractor(PrestacaoContasExtractor):

    type_mov = "despesa"
