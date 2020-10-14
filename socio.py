import csv
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import distance
import rows
from tqdm import tqdm


def parse_company_name(words):
    """
    >>> parse_company_name(['FULANO', 'DE', 'TAL', '12345678901'])
    ('12345678901', 'FULANO DE TAL')
    >>> parse_company_name(['FULANO', 'DE', 'TAL', 'CPF', '12345678901'])
    ('12345678901', 'FULANO DE TAL')
    >>> parse_company_name(['FULANO', 'DE', 'TAL', '-', 'CPF', '12345678901'])
    ('12345678901', 'FULANO DE TAL')
    >>> parse_company_name(['123456'])
    (None, '123456')
    """
    if len(words) == 1 and words[0].isdigit():  # Weird name, but doesn't have a CPF
        return (None, words[0])

    document = None
    last_word = words[-1]
    if last_word.isdigit() and len(last_word) == 11:  # Remove CPF (numbers)
        document = words.pop()

    if words[-1].upper() == "CPF":  # Remove CPF (word)
        words.pop()

    if words[-1] == "-":
        words.pop()

    return (document, " ".join(words).strip())


@dataclass
class Person:
    document: str
    name: str

    @property
    def key(self):
        if getattr(self, "_key", None) is None:
            document = self.document.strip()
            name = rows.utils.slug(self.name.strip(), separator="-").upper()
            if not document or len(document) != 11 or not name:
                self._key = None
            self._key = f"{document[3:9]}-{name}"
        return self._key

    @property
    def url(self):
        if getattr(self, "_url", None) is None:
            self._url = f"https://id.brasil.io/person/v1/{self.key}"
        return self._url

    @property
    def uuid(self):
        if getattr(self, "_uuid", None) is None:
            self._uuid = uuid.uuid5(uuid.NAMESPACE_URL, self.url)
        return self._uuid


class Entity:

    def __init__(self, input_filename, file_type="full"):
        self.input_filename = input_filename
        self.file_type = file_type

    def read(self):
        fobj = rows.utils.open_compressed(self.input_filename)
        reader = csv.DictReader(fobj)
        yield from reader

    def data(self):
        yield from self.read()

    def filtered_data(self):
        yield from self.data()

    def get_data(self):
        if self.file_type == "full":
            yield from self.filtered_data()
        else:
            yield from self.data()

    def convert_to(self, output_filename):
        writer = rows.utils.CsvLazyDictWriter(output_filename)
        for row in self.get_data():
            writer.writerow(row)
        writer.close()


class Partner(Entity):

    def data(self):
        for row in tqdm(self.read(), desc="Reading partner file"):
            if "partner_uuid" not in row:
                partner = Person(row["cnpj_cpf_do_socio"], row["nome_socio"])
                representative = Person(row["cpf_representante_legal"], row["nome_representante_legal"])
                row["partner_uuid"] = str(partner.uuid) if partner.key else None
                row["representative_uuid"] = str(representative.uuid) if representative.key else None
            yield row

    def filtered_data(self):
        for row in self.data():
            if not row["partner_uuid"] and not row["representative_uuid"]:
                continue
            yield row

    def keys(self):
        for row in self.get_data():
            if row["partner_uuid"]:
                yield (row["partner_uuid"], row)
            if row["representative_uuid"]:
                yield (row["representative_uuid"], row)


class Candidate(Entity):

    def data(self):
        for row in tqdm(self.read(), desc="Reading candidate file"):
            if "person_uuid" not in row:
                person = Person(row["cpf"], row["nome"])
                row["person_uuid"] = str(person.uuid) if person.key else None
            yield row

    def filtered_data(self):
        for row in self.data():
            if not row["person_uuid"]:
                continue
            yield row

    def keys(self):
        for row in self.get_data():
            yield (row["person_uuid"], row)


class Company(Entity):

    def __init__(self, input_filename, company_type_filename, file_type="full"):
        super().__init__(input_filename=input_filename, file_type=file_type)
        self.company_type_filename = company_type_filename

    def data(self):
        for row in tqdm(self.read(), desc="Reading company file"):
            if "owner_uuid" not in row:
                row["owner_uuid"] = None
                for field_name in ("razao_social", "nome_fantasia"):
                    words = row[field_name].split()
                    if words and words[-1].isdigit():
                        document, name = parse_company_name(words)
                        if document is None:
                            continue
                        person = Person(document, name)
                        if person.key is None:
                            continue
                        row["owner_uuid"] = str(person.uuid)
                        break
            yield row

    def filtered_data(self):
        individual_company_codes = tuple(
            str(row.codigo)
            for row in rows.import_from_csv(self.company_type_filename)
            if "individual" in row.natureza_juridica.lower()
        )
        for row in self.data():
            if row["codigo_natureza_juridica"] not in individual_company_codes or not row["owner_uuid"]:
                continue
            yield row

    def keys(self):
        for row in self.get_data():
            yield (row["owner_uuid"], row)


if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.absolute()
    ELECTIONS_PATH = BASE_PATH / "data" / "output"
    COMPANIES_PATH = BASE_PATH.parent / "socios-brasil" / "data"
    partner_filename = COMPANIES_PATH / "output" / "socio.csv.gz"
    filtered_partner_filename = COMPANIES_PATH / "output" / "socio-filtrado.csv.gz"
    company_filename = COMPANIES_PATH / "output" / "empresa.csv.gz"
    filtered_company_filename = COMPANIES_PATH / "output" / "empresa-filtrado.csv.gz"
    company_type_filename = COMPANIES_PATH / "natureza-juridica.csv"
    candidate_filename = ELECTIONS_PATH / "candidatura.csv.gz"
    filtered_candidate_filename = ELECTIONS_PATH / "candidatura-filtrado.csv.gz"
    output_filename = ELECTIONS_PATH / "politico_socio.csv.gz"

    if not filtered_candidate_filename.exists():
        print("Converting candidates")
        Candidate(candidate_filename, file_type="full").convert_to(filtered_candidate_filename)
    if not filtered_partner_filename.exists():
        print("Converting partners")
        Partner(partner_filename, file_type="full").convert_to(filtered_partner_filename)
    if not filtered_company_filename.exists():
        print("Converting companies")
        Company(company_filename, company_type_filename, file_type="full").convert_to(filtered_company_filename)

    candidate_uuids = set(
        person_uuid
        for person_uuid, _ in Candidate(filtered_candidate_filename, file_type="filtered").keys()
    )
    print(f"Total de candidatos com CPF: {len(candidate_uuids)}")

    business_and_politician = defaultdict(set)
    for partner_uuid, row in Partner(filtered_partner_filename, file_type="filtered").keys():
        if partner_uuid in candidate_uuids:
            business_and_politician[partner_uuid].add(row["cnpj"])
    total_1 = len(business_and_politician)
    print(f"Total de candidatos sócios de empresas não-individuais: {total_1}")

    for partner_uuid, row in Company(filtered_company_filename, company_type_filename, file_type="filtered").keys():
        if partner_uuid in candidate_uuids:
            business_and_politician[partner_uuid].add(row["cnpj"])
    total_2 = len(business_and_politician)
    print(f"Total de candidatos sócios de empresas individuais: {total_2 - total_1}")
    print(f"Total de candidatos sócios de empresas: {total_2}")

    cpfs_per_uuid = defaultdict(set)
    for person_uuid, row in Candidate(filtered_candidate_filename, file_type="filtered").keys():
        if person_uuid not in business_and_politician:
            continue
        cpfs_per_uuid[person_uuid].add(row["cpf"][:9])
    conflicting_cpfs = set()
    for person_uuid, values in cpfs_per_uuid.items():
        if len(values) == 1:
            continue
        values = list(values)
        for v1, v2 in zip(values, values[1:]):
            if set(v1[:3]) == set(v2[:3]):
                continue
            elif distance.levenshtein(v1, v2) >= 2:
                conflicting_cpfs.add(person_uuid)
    print(f"Encontrados {len(conflicting_cpfs)} CPFs conflitantes")

    cnpjs = set()
    writer = rows.utils.CsvLazyDictWriter(output_filename)
    for person_uuid, row in Candidate(filtered_candidate_filename, file_type="filtered").keys():
        candidate_companies = business_and_politician.get(person_uuid, None)
        if candidate_companies is None or row["cpf"] in conflicting_cpfs:
            continue
        for company_document in candidate_companies:
            new = row.copy()
            new["cnpj"] = company_document
            cnpjs.add(company_document)
            writer.writerow(new)
    print(f"Total de CNPJs encontrados: {len(cnpjs)}")
