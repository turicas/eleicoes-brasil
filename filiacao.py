import datetime
import json
from dataclasses import dataclass
from pathlib import Path

import scrapy
from scrapy.exporters import CsvItemExporter


def parse_date(value):
    value = str(value or "").strip()
    if not value:
        return None
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


def parse_date_list(value):
    """
    >>> print(parse_date_list(None))
    None
    >>> print(parse_date_list([]))
    None
    >>> parse_date_list([2012, 3, 13])
    datetime.date(2012, 3, 13)
    """
    if not value:
        return None
    return datetime.date(int(value[0]), int(value[1]), int(value[2]))


@dataclass
class UF:
    id: int
    nome: str
    sigla: str
    id_municipio_capital: int = None
    codigo: int = None

    @classmethod
    def from_dict(cls, obj):
        return cls(
            id=obj["codObjeto"],
            id_municipio_capital=int(obj["codObjetoMunicCapital"]) if obj["codObjetoMunicCapital"] else None,
            codigo=int(obj["codUf"]) if obj["codUf"] else None,
            nome=obj["nomUf"],
            sigla=obj["sglUf"],
        )


@dataclass
class Municipio:
    id_tse: int
    id: str
    nome: str
    uf_id: int
    uf_nome: str
    uf_sigla: str
    uf_obj: UF
    uf_codigo: int = None
    uf_id_municipio_capital: int = None
    id_localidade_superior: str = None

    @classmethod
    def from_dict(cls, obj, uf_obj):
        uf = obj["uf"]
        return cls(
            id=obj["codObjeto"],
            id_tse=int(obj["codLocalidadeTse"]),
            id_localidade_superior=obj["codObjetoLocSuperior"] if obj["codObjetoLocSuperior"] else None,
            nome=obj["nomLocalidade"],
            uf_id=int(uf["codObjeto"]),
            uf_id_municipio_capital=int(uf["codObjetoMunicCapital"]) if uf["codObjetoMunicCapital"] else None,
            uf_codigo=int(uf["codUf"]) if uf["codUf"] else None,
            uf_nome=uf["nomUf"],
            uf_sigla=uf["sglUf"],
            uf_obj=uf_obj,
        )


@dataclass
class Partido:
    id: int
    sigla: str
    nome: str
    legenda: int
    data_fundacao: datetime.date
    situacao: int
    data_inativacao: datetime.date = None
    descricao: str = None

    @classmethod
    def from_dict(cls, obj):
        return cls(
            id=int(obj["id"]),
            sigla=obj["sgPartido"],
            nome=obj["nmPartido"],
            legenda=int(obj["nrLegenda"]),
            data_fundacao=parse_date(obj["dtFundacao"]),
            situacao=int(obj["situacaoPartido"]),
            data_inativacao=parse_date(obj["dtInativacao"]),
            descricao=obj["descricao"],
        )


@dataclass
class Zona:
    id: str
    id_localidade: str
    codigo_uf: str
    numero: int
    municipio_obj: Municipio

    @classmethod
    def from_dict(cls, obj, municipio_obj):
        return cls(
            id=obj["codObjeto"],
            id_localidade=obj["codObjetoLocalidade"],
            codigo_uf=obj["codObjetoUf"],
            numero=int(obj["numZona"]),
            municipio_obj=municipio_obj,
        )


@dataclass
class Filiacao:
    codigo_municipio: str
    codigo_localidade_tse: str
    codigo_objeto_zona: str
    codigo_situacao_eleitor: int
    situacao_eleitor: str
    data_filiacao: datetime.date
    origem: int
    pendencia: int
    nome: str
    partido: str
    localidade: str
    numero_legenda: int
    titulo_eleitor: str
    cpf: str
    numero_secao: int
    numero_zona: int
    sigla_partido: str
    sigla_ue: str
    sequencial_partido: int
    sequencial_registro_filiacao: int
    status_registro_filiacao: int
    sexo: int
    zona_obj: Zona
    codigo_motivo_cancelamento: int = None
    codigo_motivo_desfiliacao: int = None
    data_cancelamento: datetime.date = None
    data_desfiliacao: datetime.date = None
    data_exclusao: datetime.date = None
    nome_social: datetime.date = None
    cadastro_desfiliacao: str = None

    @classmethod
    def from_dict(cls, obj, zona_obj):
        codigo_situacao_eleitor = int(obj["codSitEleitor"])
        origem = int(obj["indOrigem"])
        pendencia = int(obj["indPendencia"])
        numero_legenda = int(obj["nrLegenda"])
        numero_secao = int(obj["numSecao"])
        numero_zona = int(obj["numZona"])
        sequencial_partido = int(obj["sqPartido"])
        sequencial_registro_filiacao = int(obj["sqRegistroFiliacao"])
        status_registro_filiacao = int(obj["stRegistroFiliacao"])
        sexo = int(obj["tpSexo"])
        codigo_motivo_cancelamento = int(obj["cdMotivoCancelamento"]) if obj["cdMotivoCancelamento"] else None
        codigo_motivo_desfiliacao = int(obj["cdMotivoDesfiliacao"]) if obj["cdMotivoDesfiliacao"] else None
        data_cancelamento = parse_date_list(obj["dtCancelamento"])
        data_desfiliacao = parse_date_list(obj["dtDesfiliacao"])
        data_exclusao = parse_date_list(obj["dtExclusao"])
        data_filiacao = parse_date_list(obj["dtFiliacao"])
        return cls(
            codigo_motivo_cancelamento=codigo_motivo_cancelamento,
            codigo_motivo_desfiliacao=codigo_motivo_desfiliacao,
            codigo_municipio=obj["cdMunicipio"],
            codigo_localidade_tse=obj["codLocalidadeTse"],
            codigo_objeto_zona=obj["codObjetoZona"],
            codigo_situacao_eleitor=codigo_situacao_eleitor,
            situacao_eleitor=obj["desSituacaoEleitor"],
            data_cancelamento=data_cancelamento,
            data_desfiliacao=data_desfiliacao,
            data_exclusao=data_exclusao,
            data_filiacao=data_filiacao,
            origem=origem,
            pendencia=pendencia,
            nome=obj["nmEleitor"],
            partido=obj["nmPartido"],
            nome_social=obj["nmSocialEleitor"],
            localidade=obj["nomLocalidade"],
            numero_legenda=numero_legenda,
            titulo_eleitor=obj["nrTituloEleitor"],
            cpf=obj["numCpf"],
            numero_secao=numero_secao,
            numero_zona=numero_zona,
            sigla_partido=obj["sgPartido"],
            sigla_ue=obj["sgUe"],
            sequencial_partido=sequencial_partido,
            sequencial_registro_filiacao=sequencial_registro_filiacao,
            status_registro_filiacao=status_registro_filiacao,
            sexo=sexo,
            cadastro_desfiliacao=obj["tsCadastroDesfiliacao"],
            zona_obj=zona_obj,
        )


class MultiCSVItemPipeline:
    def __init__(self):
        self.files = {}
        self.exporters = {}

    def open_spider(self, spider):
        output_path = Path("data")
        output_path.mkdir(parents=True, exist_ok=True)
        for klass in [UF, Municipio, Partido, Zona, Filiacao]:
            file = open(output_path / f"{klass.__name__}.csv", "w+b")
            self.files[klass] = file
            exporter = CsvItemExporter(file)
            exporter.start_exporting()
            self.exporters[klass] = exporter

    def close_spider(self, spider):
        for exporter in self.exporters.values():
            exporter.finish_exporting()
        for file in self.files.values():
            file.close()

    def process_item(self, item, spider):
        item_type = type(item)
        if item_type in self.exporters:
            self.exporters[item_type].export_item(item)
        return item


class FiliacaoSpider(scrapy.Spider):
    name = "filiado"

    def start_requests(self):
        self.partidos = []
        yield scrapy.Request(
            "https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/partidos",
            meta={"tipo": "partido"},
        )

    async def start(self):
        """Compatibiliza o ponto de entrada assíncrono do Scrapy >= 2.13."""
        for request in self.start_requests():
            yield request

    def parse(self, response):
        tipo = response.request.meta["tipo"]

        if tipo == "partido":
            data = json.loads(response.text)
            for item in data:
                obj = Partido.from_dict(item)
                self.partidos.append(obj)
                yield obj
            yield scrapy.Request(
                "https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/uf/todas",
                meta={"tipo": "uf"},
            )

        elif tipo == "uf":
            data = json.loads(response.text)
            for item in data:
                obj = UF.from_dict(item)
                yield obj
                yield scrapy.Request(
                    f"https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/localidade/{obj.id}/municipios",
                    meta={"tipo": "municipio", "uf": obj},
                )

        elif tipo == "municipio":
            uf = response.request.meta["uf"]
            data = json.loads(response.text)
            for item in data:
                obj = Municipio.from_dict(item, uf_obj=uf)
                yield obj
                yield scrapy.Request(
                    f"https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/zona/municipio/{obj.id}/zonasEleitorais",
                    meta={"tipo": "zona", "municipio": obj},
                )

        elif tipo == "zona":
            municipio = response.request.meta["municipio"]
            data = json.loads(response.text)
            for item in data:
                obj = Zona.from_dict(item, municipio_obj=municipio)
                yield obj
                for partido in self.partidos:
                    sigla_ue = municipio.uf_obj.sigla
                    codigo_municipio = municipio.id
                    codigo_zona = obj.id
                    codigo_partido = partido.id
                    yield scrapy.Request(
                        f"https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/relacao-filiados?sgUe={sigla_ue}&cdMunicipio={codigo_municipio}&cdZona={codigo_zona}&sqPartido={codigo_partido}&currentPage=0&pageSize=999999",
                        meta={"tipo": "filiacao", "zona": obj},
                    )

        elif tipo == "filiacao":
            zona = response.request.meta["zona"]
            data = json.loads(response.text)
            assert (
                len(data["entitys"]) == data["totalElements"]
            ), f"Quantidade de elementos difere: {data['totalElements']}"
            for item in data["entitys"]:
                obj = Filiacao.from_dict(item, zona_obj=zona)
                yield obj


# Links:
# - lista de UFs: https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/uf/todas
# - lista de partidos: https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/partidos
# - lista de municípios: https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/localidade/3/municipios ("3" ali é o codObjeto da UF)
# - lista de zonas eleitorais: https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/zona/municipio/7043/zonasEleitorais (7043 ali é o codObjeto do município)
# - dados de filiações: https://filia2-consulta.tse.jus.br/filia-consulta/rest/v1/relacao-filiados?sgUe=RJ&cdMunicipio=7043&cdZona=1935&sqPartido=42&currentPage=0&pageSize=10 (tem que tomar cuidado com a paginação)


if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess

    settings = {
        "ITEM_PIPELINES": {
            MultiCSVItemPipeline: 300,
        },
        "LOG_LEVEL": "INFO",
        "USER_AGENT": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    }
    process = CrawlerProcess(settings)
    process.crawl(FiliacaoSpider)
    process.start()
