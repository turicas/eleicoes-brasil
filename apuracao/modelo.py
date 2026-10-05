from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Contexto:
    ano: int
    turno: int
    eleicao: int
    cargo: int
    abrangencia: str


@dataclass(frozen=True)
class Candidato:
    numero: str
    nome: str
    nome_urna: str
    vice: str | None
    votos: int
    percentual: Decimal | None
    sequencial: str | None = None
    partido: str | None = None
    destinacao: str | None = None
    situacao: str | None = None


@dataclass(frozen=True)
class Secoes:
    total: int
    apuradas: int
    totalizadas: int | None = None
    percentual_totalizadas: Decimal | None = None
    percentual_apuradas: Decimal | None = None


@dataclass(frozen=True)
class Eleitorado:
    total: int
    apurado: int
    nao_totalizado: int | None = None


@dataclass(frozen=True)
class Votos:
    total: int
    validos: int
    nulos: int
    brancos: int
    concorrentes: int | None = None
    anulados: int | None = None
    anulados_sub_judice: int | None = None


@dataclass(frozen=True)
class Resultado:
    contexto: Contexto
    gerada_em: datetime
    secoes: Secoes
    eleitorado: Eleitorado
    votos: Votos
    candidatos: tuple[Candidato, ...]
    geracao: str | None = None
    totalizada_em: datetime | None = None
    divulgacao_liberada: bool = True
    andamento: str | None = None
    finalizada: bool | None = None
    matematicamente_definida: str | None = None
    origem: str = "tse"
    fontes_desde: datetime | None = None
    fontes_ate: datetime | None = None
    capturada_em: datetime | None = None
