import csv
import re
from functools import lru_cache
from io import StringIO, TextIOWrapper
from os import rename as rename_file
from pathlib import Path
from zipfile import ZipFile

import rows
from rows.utils import download_file

import utils
import settings

REGEXP_NUMBERS = re.compile('([0-9]+)')
REGEXP_WRONGQUOTE = re.compile(r';"([^;\r\n]+"[^;\r\n]*)";')
MAP_CODIGO_CARGO = {
    'PRESIDENTE': '1',
    'VICE-PRESIDENTE': '2',
    'GOVERNADOR': '3',
    'VICE-GOVERNADOR': '4',
    'SENADOR': '5',
    'DEPUTADO FEDERAL': '6',
    'DEPUTADO ESTADUAL': '7',
    'DEPUTADO DISTRITAL': '8',
    '1o SUPLENTE SENADOR': '9',
    '2o SUPLENTE SENADOR': '10',
    'PREFEITO': '11',
    'VICE-PREFEITO': '12',
    'VEREADOR': '13',
}
MAP_DESCRICAO_CARGO = {
    # Must change
    '1o SUPLENTE': '1o SUPLENTE SENADOR',
    '1O SUPLENTE': '1o SUPLENTE SENADOR',
    '1º SUPLENTE SENADOR': '1o SUPLENTE SENADOR',
    '1º SUPLENTE': '1o SUPLENTE SENADOR',
    '2o SUPLENTE': '2o SUPLENTE SENADOR',
    '2O SUPLENTE': '2o SUPLENTE SENADOR',
    '2º SUPLENTE SENADOR': '2o SUPLENTE SENADOR',
    '2º SUPLENTE': '2o SUPLENTE SENADOR',
    'VICE PREFEITO': 'VICE-PREFEITO',
    '1O SUPLENTE SENADOR': '1o SUPLENTE SENADOR',
    '2O SUPLENTE SENADOR': '2o SUPLENTE SENADOR',

    # Do not change
    'PRESIDENTE': 'PRESIDENTE',
    'VICE-PRESIDENTE': 'VICE-PRESIDENTE',
    'GOVERNADOR': 'GOVERNADOR',
    'VICE-GOVERNADOR': 'VICE-GOVERNADOR',
    'SENADOR': 'SENADOR',
    'DEPUTADO FEDERAL': 'DEPUTADO FEDERAL',
    'DEPUTADO ESTADUAL': 'DEPUTADO ESTADUAL',
    'DEPUTADO DISTRITAL': 'DEPUTADO DISTRITAL',
    '1o SUPLENTE SENADOR': '1o SUPLENTE SENADOR',
    '2o SUPLENTE SENADOR': '2o SUPLENTE SENADOR',
    'PREFEITO': 'PREFEITO',
    'VICE-PREFEITO': 'VICE-PREFEITO',
    'VEREADOR': 'VEREADOR',
}


@lru_cache()
def read_header(filename, encoding='utf-8'):
    filename = Path(filename)
    return rows.import_from_csv(filename, encoding=encoding)


def fix_cargo(codigo_cargo, descricao_cargo):
    if codigo_cargo == '91':
        # It's a question on a plebiscite
        descricao_cargo, pergunta = 'OPCAO PLEBISCITO', descricao_cargo

    else:
        # Normalize descricao_cargo spelling and fix codigo_cargo accordingly
        descricao_cargo = MAP_DESCRICAO_CARGO[descricao_cargo]
        codigo_cargo = MAP_CODIGO_CARGO[descricao_cargo]
        pergunta = ''
    return codigo_cargo, descricao_cargo, pergunta


def fix_nome(value):
    value = value.replace("`", "'").replace("' ", "'")
    if value[0] in "',.]":
        value = value[1:]
    return value


def fix_sigla_uf(value):
    return value.replace('BH', 'BA').replace('LB', 'ZZ')


def fix_valor(value):
    return value.replace(',', '.')


def fix_cpf(value):
    value = ''.join(REGEXP_NUMBERS.findall(value))
    if len(value) < 11:
        value = '0' * (11 - len(value)) + value
    return value


def fix_titulo_eleitoral(value):
    return ''.join(REGEXP_NUMBERS.findall(value))


def fix_pergunta(value, new_descricao_cargo):
    if value == '91':  # TODO: check
        return new_descricao_cargo
    else:
        return ''


class Extractor:

    encoding = 'latin-1'

    def download(self, year, force=False):
        filename = self.filename(year)
        if not force and filename.exists():  # File has already been downloaded
            return {'downloaded': False, 'filename': filename}

        url = self.url(year)
        file_data = download_file(url, progress=True)
        rename_file(file_data.uri, filename)
        return {'downloaded': True, 'filename': filename}

    def extract_state_from_filename(self, filename):
        """ 'bem_candidato_2006_AC.csv' -> 'AC' """
        return filename.split('.')[0].split('_')[-1]

    def fix_fobj(self, fobj):
        'Fix file-like object, if needed'
        return fobj

    def extract(self, year):
        filename = self.filename(year)
        zfile = ZipFile(filename)
        for file_info in zfile.filelist:
            internal_filename = file_info.filename
            if self.valid_filename(internal_filename):
                fobj = TextIOWrapper(
                    zfile.open(internal_filename),
                    encoding=self.encoding,
                )
                fobj = self.fix_fobj(fobj)
                reader = csv.reader(fobj, dialect=utils.TSEDialect)
                header_meta = self.get_headers(year, filename, internal_filename)
                year_fields = [field.nome_final or field.nome_tse
                               for field in header_meta['year_fields']]
                final_fields = [field.nome_final
                                for field in header_meta['final_fields']
                                if field.nome_final]
                convert_function = self.convert_row(year_fields, final_fields)
                for index, row in enumerate(reader):
                    if index == 0 and 'ANO_ELEICAO' in row:
                        # It's a header, we should skip it as a data row but
                        # use the information to get field ordering (better
                        # trust it then our headers files, TSE may change the
                        # order)
                        field_map = {field.nome_tse: field.nome_final or field.nome_tse
                                     for field in header_meta['year_fields']}
                        year_fields = [field_map[field_name] for field_name in row]
                        convert_function = self.convert_row(year_fields, final_fields)
                        continue

                    yield convert_function(row)


class CandidaturaExtractor(Extractor):

    def url(self, year):
        return f'http://agencia.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{year}.zip'

    def filename(self, year):
        return settings.DOWNLOAD_PATH / f'candidatura-{year}.zip'

    def valid_filename(self, filename):
        return filename.startswith('consulta_cand_')

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
            if uf != 'PI':
                uf = 'BR'
            header_year = f'1994-{uf}'
        elif 1996 <= year <= 2010:
            header_year = '1996'
        elif year == 2012:
            header_year = '2012'
        elif 2014 <= year <= 2016:
            header_year = '2014'
        elif year == 2018:
            header_year = '2018'
        else:
            raise ValueError(f'Unrecognized year ({year}, {uf})')
        return {
            'year_fields': read_header(settings.HEADERS_PATH / f'candidatura-{header_year}.csv'),
            'final_fields': read_header(settings.HEADERS_PATH / 'candidatura-final.csv'),
        }

    def convert_row(self, row_field_names, final_field_names):
        # TODO: may add validators for these converter methods

        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, '').strip()
                if value in ('#NULO', '#NULO#', '#NE#'):
                    value = ''
                new[key] = value = utils.unaccent(value).upper()

            # TODO: fix data_nascimento (dd/mm/yyyy, dd/mm/yy, yyyymmdd, xx/xx/)
            # TODO: fix situacao
            # TODO: fix totalizacao
            new['cpf'] = fix_cpf(new['cpf'])
            new['nome'] = fix_nome(new['nome'])
            new['sigla_uf'] = fix_sigla_uf(new['sigla_uf'])
            new['sigla_uf_nascimento'] = fix_sigla_uf(new['sigla_uf_nascimento'])
            new['titulo_eleitoral'] = fix_titulo_eleitoral(new['titulo_eleitoral'])
            new['codigo_cargo'], new['descricao_cargo'], new['pergunta'] = \
                fix_cargo(new['codigo_cargo'], new['descricao_cargo'])

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

        if 'eleicao' in name and ('idade' not in name and 'reeleicao' not in name):
            value = 0
        elif 'turno' in name:
            value = 1
        elif name.endswith('_ue') or name == 'sigla_uf':
            value = 2
        elif 'titulo' in name:
            value = 3
        elif ('coligacao' in name or 'legenda' in name or 'partido' in name or
              'agremiacao' in name):
            value = 4
        elif ('candidat' in name or 'cargo' in name or 'reeleicao' in name or
              'despesa' in name or 'declara' in name or 'urna' in name or
              'posse' in name or name == 'idade_data_eleicao' or
              name == 'numero_sequencial'):
            value = 5
        else:
            value = 3
        return value, name


class BemDeclaradoExtractor(Extractor):

    def url(self, year):
        return f'http://agencia.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_{year}.zip'

    def filename(self, year):
        return settings.DOWNLOAD_PATH / f'bemdeclarado-{year}.zip'

    def valid_filename(self, filename):
        return filename.startswith('bem_candidato')

    def get_headers(self, year, filename, internal_filename):
        uf = self.extract_state_from_filename(internal_filename)
        if 2006 <= year <= 2016:
            header_year = '2006'
        elif year == 2018:
            header_year = '2018'
        else:
            raise ValueError('Unrecognized year')

        return {
            'year_fields': read_header(settings.HEADERS_PATH / f'bemdeclarado-{header_year}.csv'),
            'final_fields': read_header(settings.HEADERS_PATH / 'bemdeclarado-final.csv'),
        }

    def convert_row(self, row_field_names, final_field_names):
        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, '').strip()
                if value in ('#NULO', '#NULO#', '#NE#'):
                    value = ''
                new[key] = value = utils.unaccent(value).upper()

            new['sigla_uf'] = fix_sigla_uf(new['sigla_uf'])
            new['valor'] = fix_valor(new['valor'])

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

        if name.endswith('_eleicao'):
            value = 0
        elif name.endswith('_ue') or name == 'sigla_uf':
            value = 1
        elif name == 'numero_sequencial':
            value = 2
        else:
            value = 3
        return value, name


class VotacaoZonaExtractor(Extractor):

    def url(self, year):
        return f'http://agencia.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip'

    def filename(self, year):
        return settings.DOWNLOAD_PATH / f'votacao-zona-{year}.zip'

    def valid_filename(self, filename):
        return filename.startswith('votacao_candidato_munzona_')

    def get_headers(self, year, filename, internal_filename):
        uf = self.extract_state_from_filename(internal_filename)
        if year < 2014:
            header_year = '1994'
        elif 2014 <= year <= 2018:
            header_year = '2014'
        else:
            raise ValueError('Unrecognized year')
        return {
            'year_fields': read_header(settings.HEADERS_PATH / f'votacao-zona-{header_year}.csv'),
            'final_fields': read_header(settings.HEADERS_PATH / 'votacao-zona-final.csv'),
        }

    def convert_row(self, row_field_names, final_field_names):
        def convert(row_data):
            row = dict(zip(row_field_names, row_data))
            new = {}
            for key in final_field_names:
                value = row.get(key, '').strip()
                if value in ('#NULO', '#NULO#', '#NE#'):
                    value = ''
                new[key] = value = utils.unaccent(value).upper()

            new['sigla_uf'] = fix_sigla_uf(new['sigla_uf'])
            new['nome'] = fix_nome(new['nome'])
            new['codigo_cargo'], new['descricao_cargo'], _ = \
                fix_cargo(new['codigo_cargo'], new['descricao_cargo'])

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

        if name.endswith('_eleicao'):
            value = 0
        elif name.endswith('_turno'):
            value = 1
        elif (name.endswith('_ue') or name.endswith('_uf') or
              name.endswith('_municipio')):
            value = 2
        elif (name.endswith('_legenda') or name.endswith('_coligacao') or
              name.endswith('_partido')):
            value = 3
        elif 'zona' in name or 'voto' in name:
            value = 5
        else:
            value = 4
        return value, name
