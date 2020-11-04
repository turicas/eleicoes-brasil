import csv
import datetime
import re
from functools import lru_cache
from io import StringIO, TextIOWrapper
from pathlib import Path
from shutil import move as rename_file
from urllib.parse import urljoin
from zipfile import ZipFile

import rarfile
import rows
from cached_property import cached_property
from rows.utils import download_file, load_schema

import utils
import settings


# TODO: may add validators to convert_row methods

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


@lru_cache
def last_elections_year(reference=None):
    """
    >>> import datetime
    >>> last_elections_year(datetime.date(2021, 1, 1))
    2020
    >>> last_elections_year(datetime.date(2021, 12, 1))
    2020
    >>> last_elections_year(datetime.date(2022, 1, 1))
    2020
    >>> last_elections_year(datetime.date(2022, 12, 1))
    2022
    """

    reference = reference or datetime.datetime.now().date()
    if reference.year % 2 == 1:  # Não é ano de eleição retorna o anterior
        return reference.year - 1

    if reference >= datetime.date(reference.year, 8, 15):  # Passou a divulgação das candidaturas desse ano
        return reference.year

    return reference.year - 2


def obfuscate_cpf(cpf):
    """
    >>> obfuscate_cpf("12345678901")
    '***456789**'
    >>> obfuscate_cpf("123")
    '123'
    """
    if len(cpf) == 11:
        cpf = f"***{cpf[3:9]}**"
    return cpf


class SimNaoBooleanField(rows.fields.BoolField):
    TRUE_VALUES = ("sim",)
    FALSE_VALUES = ("não", "nao")


@lru_cache()
def read_header(filename, encoding="utf-8"):
    filename = Path(filename)
    return rows.import_from_csv(filename, encoding=encoding)


def fix_cargo(codigo_cargo, cargo):
    if codigo_cargo == "91":
        # It's a question on a plebiscite
        cargo, pergunta = "OPCAO PLEBISCITO", cargo

    else:
        # Normalize cargo spelling and fix codigo_cargo accordingly
        cargo = MAP_DESCRICAO_CARGO[cargo]
        codigo_cargo = MAP_CODIGO_CARGO[cargo]
        pergunta = ""
    return codigo_cargo, cargo, pergunta


def fix_nome(value):
    value = value.replace("`", "'").replace("' ", "'")
    if value[0] in "',.]":
        value = value[1:]
    return value


def fix_sigla_unidade_federativa(value):
    return value.replace("BH", "BA").replace("LB", "ZZ")


def fix_valor(value):
    return value.replace(",", ".")


def fix_cpf(value):
    """
    >>> fix_cpf("123.456.789-01")
    '12345678901'
    >>> fix_cpf("123456789")
    '00123456789'
    >>> fix_cpf("000.000.000-00")
    ''
    """

    value = "".join(REGEXP_NUMBERS.findall(value))
    if len(value) < 11:
        value = "0" * (11 - len(value)) + value
    if set(value) == {"0"}:
        value = ""
    return value


def fix_cnpj_cpf(value):
    value = re.sub(r"\s+", "", value)
    if set(value) == {"0"}:
        value = ""
    return value


def fix_titulo_eleitoral(value):
    return "".join(REGEXP_NUMBERS.findall(value))


def fix_data(value):
    original_value = value
    new_dt = ""
    value = value.replace("00:00:00", "").replace("0002", "2002").strip()
    if not value:
        return None

    possible_date_formats = ("%d/%m/%Y", "%d/%m/%y", "%d-%b-%y")
    dt = None
    for date_format in possible_date_formats:
        try:
            dt = datetime.datetime.strptime(value, date_format)
        except ValueError:
            continue
    if dt is None:
        # TODO: talvez gerar uma exceção com o erro, salvar o erro em algum log
        # ou gravar valor em outra coluna
        return None

    result = dt.strftime("%Y-%m-%d")
    if len(result) == 9 and re.match("^9[0-9]{2}-", result):
        # Corrige valores como: '941-09-03', '942-08-23', '955-12-13',
        # '964-12-10', '983-09-17', '989-01-15', '992-01-20'
        result = "1" + result

    if len(result) != 10:
        return None

    return result


def clean_header(header):
    return re.sub('"', "", header.strip())


def get_organization(internal_filename, year):
    if year == 2010:
        if "Receitas" in internal_filename:
            return internal_filename.split("Receitas")[1].replace(".txt", "").lower()
        else:
            return internal_filename.split("Despesas")[1].replace(".txt", "").lower()
    elif year in (2014, 2016):
        return internal_filename.split("_")[1]
    elif year in (2002, 2004, 2006, 2008):
        return "comites" if "comit" in internal_filename.lower() else "candidatos"
    elif year == 2012:
        return internal_filename.split("_")[1]
    elif "2018" in year or "2020" in year:
        cand_or_party = (
            "candidatos" if "candidatos" in internal_filename else "partidos"
        )
        if "pagas" in internal_filename:
            cand_or_party = "pagas-" + cand_or_party
        elif "contratadas" in internal_filename:
            cand_or_party = "contratadas-" + cand_or_party
        origin = "originarios-" if "originario" in internal_filename else ""
        return origin + cand_or_party


class Extractor:

    base_url = "http://cdn.tse.jus.br/estatistica/sead/odsele/"
    encoding = "latin-1"
    schema_filename = ""

    def __init__(self, base_url=None, censor=False):
        if base_url is not None:
            self.base_url = base_url
        self.censor = censor

    def filename(self, year):
        """Caminho para arquivo de um ano, que será juntado com self.base_url"""
        raise NotImplementedError()

    def url(self, year):
        return urljoin(self.base_url, self.filename(year))

    def download_filename(self, year):
        return settings.DOWNLOAD_PATH / self.filename(year)

    @property
    def schema(self):
        return load_schema(str(self.schema_filename))

    def download(self, year, force=False):
        filename = self.download_filename(year)
        if not filename.parent.exists():
            filename.parent.mkdir(parents=True)
        if not force and filename.exists():  # File has already been downloaded
            return {"downloaded": False, "filename": filename}

        url = self.url(year)
        file_data = download_file(url, progress=True, chunk_size=256 * 1024, user_agent="Mozilla/4")
        rename_file(file_data.uri, filename)
        return {"downloaded": True, "filename": filename}

    def extract_state_from_filename(self, filename):
        """ 'bem_candidato_2006_AC.csv' -> 'AC' """
        return filename.split(".")[0].split("_")[-1]

    def fix_fobj(self, fobj):
        "Fix file-like object, if needed"
        return fobj

    def extract(self, year):
        filename = self.download_filename(year)
        zfile = ZipFile(filename)
        for file_info in zfile.filelist:
            internal_filename = file_info.filename
            if not self.valid_filename(internal_filename):
                continue
            fobj = TextIOWrapper(zfile.open(internal_filename), encoding=self.encoding)
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

    year_range = tuple(range(1996, last_elections_year() + 1, 2))
    schema_filename = settings.SCHEMA_PATH / "candidatura.csv"

    def filename(self, year):
        return f"consulta_cand/consulta_cand_{year}.zip"

    def valid_filename(self, filename):
        name = filename.lower()
        return (
            name.startswith("consulta_cand_")
            and "_brasil.csv" not in name
            and not name.endswith("todos.csv")
        )

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
            header_year = f"1994_{uf}"
        elif 1996 <= year <= 2010:
            header_year = "1996"
        elif year == 2012:
            header_year = "2012"
        elif year == 2014:
            header_year = "2014"
        elif 2016 <= year <= 2020:
            header_year = "2020"
        elif year == 2022:
            header_year = "2022"
        else:
            raise ValueError(f"Unrecognized year ({year}, {uf})")
        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"candidatura_{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / "candidatura_final.csv"
            ),
        }

    def convert_row(self, row_field_names, final_field_names):
        censor = self.censor
        def convert(row_data):
            if len(row_data) == 1 and "elapsed" in row_data[0].lower():
                return None

            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, "").strip()
                if value in ("#NULO", "#NULO#", "#NE#", "#NE"):
                    value = ""
                new[key] = value = utils.unaccent(value).upper()

            # TODO: fix data_nascimento (dd/mm/yyyy, dd/mm/yy, yyyymmdd, xx/xx/)
            # TODO: fix situacao
            # TODO: fix totalizacao
            new["cpf"] = fix_cpf(new["cpf"])
            new["nome"] = fix_nome(new["nome"])
            new["sigla_unidade_federativa"] = fix_sigla_unidade_federativa(new["sigla_unidade_federativa"])
            new["sigla_unidade_federativa_nascimento"] = fix_sigla_unidade_federativa(new["sigla_unidade_federativa_nascimento"])
            new["titulo_eleitoral"] = fix_titulo_eleitoral(new["titulo_eleitoral"])
            new["codigo_cargo"], new["cargo"], new["pergunta"] = fix_cargo(
                new["codigo_cargo"], new["cargo"]
            )
            new["candidatura_inserida_urna"] = SimNaoBooleanField.deserialize(
                new["candidatura_inserida_urna"]
            )
            new["data_eleicao"] = fix_data(new["data_eleicao"])
            new["data_nascimento"] = fix_data(new["data_nascimento"])
            # TODO: seria interessante confirmar a idade na data da posse com
            # os valores corrigidos, para verificar se a correção é compatível
            # TODO: existem casos em que row['idade_data_eleicao'] é '' e
            # row['idade_data_posse'] é '999' - esses provavelmente devem ser
            # corrigidos (e a data de nascimento provavelmente deve ficar em
            # branco).
            # TODO: idade_data_eleicao está em branco em muitos casos, porém
            # conseguimos preenchê-lo caso a data de nascimento esteja correta
            if censor:
                row["cpf"] = obfuscate_cpf(row["cpf"])
                row["email"] = ""

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
        elif name.endswith("_unidade_eleitoral") or name == "sigla_unidade_federativa":
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

    year_range = tuple(range(2006, last_elections_year() + 1, 2))
    schema_filename = settings.SCHEMA_PATH / "bem_declarado.csv"

    def filename(self, year):
        return f"bem_candidato/bem_candidato_{year}.zip"

    def valid_filename(self, filename):
        name = filename.lower()
        return (
            name.startswith("bem_candidato")
            and "_brasil.csv" not in name
            and not name.endswith("todos.csv")
        )

    def get_headers(self, year, filename, internal_filename):
        uf = self.extract_state_from_filename(internal_filename)
        if 2006 <= year <= 2012:
            header_year = "2006"
        elif 2014 <= year <= 2022:
            header_year = "2014"
        else:
            raise ValueError("Unrecognized year")

        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"bem_declarado_{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / "bem_declarado_final.csv"
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

            new["sigla_unidade_federativa"] = fix_sigla_unidade_federativa(new["sigla_unidade_federativa"])
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
        elif name.endswith("_unidade_eleitoral") or name == "sigla_unidade_federativa":
            value = 1
        elif name == "numero_sequencial":
            value = 2
        else:
            value = 3
        return value, name


class VotacaoZonaExtractor(Extractor):

    year_range = tuple(range(1996, last_elections_year(), 2))
    schema_filename = settings.SCHEMA_PATH / "votacao_zona.csv"

    @cached_property
    def codigo_situacao_candidatura(self):
        return {
            (
                row.codigo_situacao_candidatura,
                row.situacao_candidatura,
            ): row.novo_codigo_situacao_candidatura
            for row in rows.import_from_csv(
                settings.HEADERS_PATH / f"situacao_candidatura.csv",
            )
        }

    @cached_property
    def situacao_candidatura(self):
        return {
            (
                row.codigo_situacao_candidatura,
                row.situacao_candidatura,
            ): row.nova_situacao_candidatura
            for row in rows.import_from_csv(
                settings.HEADERS_PATH / f"situacao_candidatura.csv",
            )
        }

    def filename(self, year):
        return f"votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip"

    def valid_filename(self, filename):
        return filename.startswith("votacao_candidato_munzona_")

    def get_headers(self, year, filename, internal_filename):
        uf = self.extract_state_from_filename(internal_filename)
        if year < 2014:
            header_year = "1994"
        elif 2014 <= year <= 2018:
            header_year = "2014"
        else:
            raise ValueError("Unrecognized year")
        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"votacao_zona_{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / "votacao_zona_final.csv"
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

            new["sigla_unidade_federativa"] = fix_sigla_unidade_federativa(new["sigla_unidade_federativa"])
            new["nome"] = fix_nome(new["nome"])
            new["codigo_cargo"], new["cargo"], _ = fix_cargo(
                new["codigo_cargo"], new["cargo"]
            )

            key = (new["codigo_situacao_candidatura"],
                    new["situacao_candidatura"])
            new["codigo_situacao_candidatura"] = self.codigo_situacao_candidatura[key]
            new["situacao_candidatura"] = self.situacao_candidatura[key]

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
            name.endswith("_unidade_eleitoral") or name.endswith("_uf") or name.endswith("_municipio")
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

    year_range = (
        2002,
        2004,
        2006,
        2008,
        2010,
        2012,
        2014,
        "2014_suplementar",
        2016,
        "2018_orgaos",
        "2018_candidatos",
        "2020_orgaos",
        "2020_candidatos",
    )

    def filename(self, year):
        urls = {
            2002: "contas_2002",
            2004: "contas_2004",
            2006: "contas_2006",
            2008: "contas_2008",
            2010: "contas_2010",
            2012: "final_2012",
            2014: "final_2014",
            "2014_suplementar": "contas_final_sup_2014",
            2016: "contas_final_2016",
            "2016_suplementar": "contas_final_sup_2016",
            "2018_orgaos": "de_contas_eleitorais_orgaos_partidarios_2018",
            "2018_candidatos": "de_contas_eleitorais_candidatos_2018",
            "2020_orgaos": "de_contas_eleitorais_orgaos_partidarios_2020",
            "2020_candidatos": "de_contas_eleitorais_candidatos_2020",
        }
        return f"prestacao_contas/prestacao_{urls[year]}.zip"

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
        if year == 2002 or year == 2004 or year == 2006 or year == 2008:
            fobj = utils.FixQuotes(fobj, encoding=self.encoding)
        else:
            fobj = TextIOWrapper(fobj, encoding=self.encoding)

        return fobj

    def get_headers(self, year, filename, internal_filename):
        if str(year).endswith("suplementar"):
            # TODO: check if 2016-suplementar should use the same headers as
            # 2014
            header_year = year
            year = 2014
        elif isinstance(year, str) and ("2018" in year or "2020" in year):
            header_year = "2018"
        else:
            header_year = str(year)

        org = get_organization(internal_filename, year)

        return {
            "year_fields": read_header(
                settings.HEADERS_PATH / f"{self.type_mov}_{org}_{header_year}.csv"
            ),
            "final_fields": read_header(
                settings.HEADERS_PATH / f"{self.type_mov}_final.csv"
            ),
        }

    def valid_filename(self, filename, year):
        filename = filename.lower()
        year = str(year)

        is_type_mov = self.type_mov in filename
        extension = filename.endswith(".csv") or filename.endswith(".txt")
        not_brasil = "_brasil" not in filename
        is_2008 = year == "2008"
        is_suplementar = "sup" not in filename
        is_year_suplementar = year.endswith("suplementar")

        return (
            is_type_mov
            and extension
            and (((not_brasil or is_2008) and is_suplementar) or is_year_suplementar)
        )

    def order_columns(self, name):
        """Order columns according to a (possible) normalization

        The order is:
        - Geographic Area
        - Person
        - Party
        - Donator
        - Revenue
        """

        if "unidade_federativa" in name or "unidade_eleitoral" in name or name == "municipio":
            value = 0
        elif "sequencial" in name or "candidato" in name:
            value = 1
        elif "partido" in name or "comite" in name:
            value = 2
        elif "doador" in name or "fornecedor" in name:
            value = 3
        elif "receita" in name or "despesa" in name or "recurso" in name:
            value = 4
        else:
            value = 5

        return value, name

    def extract(self, year):
        filename = self.download_filename(year)
        fobjs, internal_filenames = self._get_compressed_fobjs(filename, year)
        for fobj, internal_filename in zip(fobjs, internal_filenames):
            fobj = self.fix_fobj(fobj, year)
            dialect = csv.Sniffer().sniff(fobj.read(1024))
            fobj.seek(0)
            reader = csv.reader(fobj, dialect=dialect)
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

            # Add year to final csv
            final_fields = ["ano"] + final_fields
            convert_function = self.convert_row(year_fields, final_fields, year)
            for index, row in enumerate(reader):
                if index == 0 and (
                    "UF" in row
                    or "SG_UF" in row
                    or "SG_UE_SUP" in row
                    or "SITUACAOCADASTRAL" in row
                    or "DS_ORGAO" in row
                    or "RV_MEANING" in row
                    or "SEQUENCIAL_CANDIDATO" in row
                ):
                    # It's a header, we should skip it as a data row but
                    # use the information to get field ordering (better
                    # trust it then our headers files, TSE may change the
                    # order)
                    field_map = {
                        field.nome_tse: field.nome_final or field.nome_tse
                        for field in header_meta["year_fields"]
                    }
                    year_fields = [
                        field_map[clean_header(field_name)] for field_name in row
                    ]
                    convert_function = self.convert_row(year_fields, final_fields, year)
                    continue

                yield convert_function(row)


class PrestacaoContasReceitasExtractor(PrestacaoContasExtractor):

    type_mov = "receita"
    schema_filename = settings.SCHEMA_PATH / "receita.csv"

    def convert_row(self, row_field_names, final_field_names, year):
        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, "").strip()
                if value in ("#NULO", "#NULO#", "#NE#", "#NE"):
                    value = ""
                new[key] = value = utils.unaccent(value).upper()

            cleaned_year, *_unused_suffix = str(year).split('_')
            new["ano"] = int(cleaned_year)
            new["valor"] = fix_valor(new["valor"])
            new["data"] = fix_data(new["data"])
            new["data_prestacao_contas"] = fix_data(new["data_prestacao_contas"])
            new["data_eleicao"] = fix_data(new["data_eleicao"])
            new["cnpj"] = fix_cnpj_cpf(new["cnpj"])
            new["cpf_cnpj_doador"] = fix_cnpj_cpf(new["cpf_cnpj_doador"])
            new["cpf_cnpj_doador_originario"] = fix_cnpj_cpf(
                new["cpf_cnpj_doador_originario"]
            )
            return new

        return convert


class PrestacaoContasDespesasExtractor(PrestacaoContasExtractor):

    type_mov = "despesa"
    schema_filename = settings.SCHEMA_PATH / "despesa.csv"

    def convert_row(self, row_field_names, final_field_names, year):
        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, "").strip()
                if value in ("#NULO", "#NULO#", "#NE#", "#NE"):
                    value = ""
                new[key] = value = utils.unaccent(value).upper()

            cleaned_year, *_unused_suffix = str(year).split('_')
            new["ano"] = int(cleaned_year)
            new["valor"] = fix_valor(new["valor"])
            new["data"] = fix_data(new["data"])
            new["data_prestacao_contas"] = fix_data(new["data_prestacao_contas"])
            new["data_eleicao"] = fix_data(new["data_eleicao"])
            new["cnpj"] = fix_cnpj_cpf(new["cnpj"])
            new["cpf_cnpj_fornecedor"] = fix_cnpj_cpf(new["cpf_cnpj_fornecedor"])
            return new

        return convert
