import re
from datetime import datetime, timezone

from .modelo import Contexto

_UFS = (
    "ac",
    "al",
    "am",
    "ap",
    "ba",
    "ce",
    "df",
    "es",
    "go",
    "ma",
    "mg",
    "ms",
    "mt",
    "pa",
    "pb",
    "pe",
    "pi",
    "pr",
    "rj",
    "rn",
    "ro",
    "rr",
    "rs",
    "sc",
    "se",
    "sp",
    "to",
)
_UFS_2022_SEGUNDO_TURNO = ("al", "am", "ba", "es", "ms", "pb", "pe", "ro", "rs", "sc", "se", "sp")
_BASE = "https://resultados.tse.jus.br"


def _inteiro(valor, campo: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, (str, int)) or not re.fullmatch(r"[0-9]+", str(valor)):
        raise ValueError(f"{campo}: esperado inteiro não negativo")
    return int(valor)


def _campo(dados: dict, chave: str, campo: str):
    if not isinstance(dados, dict) or chave not in dados:
        raise ValueError(f"{campo}: campo obrigatório ausente")
    return dados[chave]


def _lista(dados: dict, chave: str, campo: str) -> list[dict]:
    valor = _campo(dados, chave, campo)
    if not isinstance(valor, list) or any(not isinstance(item, dict) for item in valor):
        raise ValueError(f"{campo}: esperada lista de objetos")
    return valor


def _oficial(dados: dict):
    if _campo(dados, "f", "f") != "o":
        raise ValueError("f: apenas configuração oficial é aceita")


def _uf(dados: dict, campo: str) -> str:
    valor = _campo(dados, "cd", campo)
    if not isinstance(valor, str):
        raise ValueError(f"{campo}: esperada sigla da abrangência")  # noqa: TRY004
    return valor.lower()


def contextos_eleicao(dados: dict, ano: int, turno: int, cargo: int, municipios: dict | None = None) -> list[Contexto]:
    if ano not in (2022, 2026) or turno not in (1, 2) or cargo not in (1, 3):
        raise ValueError("ano/turno/cargo: suportados 2022 e 2026, turnos 1 e 2, presidente e governador")
    if ano == 2022:
        eleicao = (544 if cargo == 1 else 546) + turno - 1
        abrangencias = ("br",) if cargo == 1 else (_UFS if turno == 1 else _UFS_2022_SEGUNDO_TURNO)
        return [Contexto(ano, turno, eleicao, cargo, abrangencia) for abrangencia in abrangencias]
    _oficial(dados)
    contextos = []
    for pleito in _lista(dados, "pl", "pl"):
        if _campo(pleito, "c", "pl.c") != "ele2026":
            continue
        try:
            data = datetime.strptime(_campo(pleito, "dt", "pl.dt"), "%d/%m/%Y").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError) as erro:
            raise ValueError("pl.dt: data inválida") from erro
        if data.year != ano:
            continue
        for eleicao in _lista(pleito, "e", "pl.e"):
            if _inteiro(_campo(eleicao, "tp", "e.tp"), "e.tp") != (8 if cargo == 1 else 1):
                continue
            if _inteiro(_campo(eleicao, "t", "e.t"), "e.t") != turno:
                continue
            codigo = _inteiro(_campo(eleicao, "cd", "e.cd"), "e.cd")
            for abrangencia in _lista(eleicao, "abr", f"e[{codigo}].abr"):
                cargos = _lista(abrangencia, "cp", f"e[{codigo}].abr.cp")
                if not any(_inteiro(_campo(item, "cd", "cp.cd"), "cp.cd") == cargo for item in cargos):
                    continue
                sigla = _uf(abrangencia, f"e[{codigo}].abr.cd")
                if cargo == 1:
                    if sigla != "br":
                        raise ValueError(f"e[{codigo}].abr.cd: presidente exige br, recebido {sigla}")
                    siglas = ["br"]
                elif sigla == "br":
                    if municipios is None:
                        raise ValueError(f"e[{codigo}].abr: governador em br exige municípios (EA12) para expandir UFs")
                    _oficial(municipios)
                    siglas = []
                    for item in _lista(municipios, "abr", "municipios.abr"):
                        unidade = _uf(item, "municipios.abr.cd")
                        if unidade == "zz":
                            continue
                        if unidade not in _UFS:
                            raise ValueError(
                                f"municipios.abr.cd: UF inválida {unidade} para governador, eleicao={codigo}"
                            )
                        siglas.append(unidade)
                    if not siglas:
                        raise ValueError(f"municipios.abr: nenhuma UF para governador, eleicao={codigo}")
                elif sigla in _UFS:
                    siglas = [sigla]
                else:
                    raise ValueError(f"e[{codigo}].abr.cd: UF inválida {sigla} para governador")
                for unidade in siglas:
                    contexto = Contexto(ano, turno, codigo, cargo, unidade)
                    if contexto not in contextos:
                        contextos.append(contexto)
    if not contextos:
        if turno == 2:
            raise ValueError(
                "e.t: segundo turno não publicado para o cargo; cdt2 não substitui uma eleição de turno 2 em e"
            )
        raise ValueError(f"pl.e.abr.cp: nenhuma eleição ordinária de {ano} para turno={turno}, cargo={cargo}")
    return contextos


def _diretorio(ano: int, eleicao: int, tipo: str, uf: str, diretorios: list[dict] | None) -> str:
    if ano not in (2022, 2026):
        raise ValueError("ano: suportados 2022 e 2026")
    _inteiro(eleicao, "eleicao")
    if diretorios is None:
        caminho = "config" if tipo == "cm" else ("dados-simplificados/<uf>" if ano == 2022 else "dados/<uf>")
        template = f"<base>/<ambiente>/<ciclo>/<cd_eleicao>/{caminho}"
    else:
        if not isinstance(diretorios, list) or any(not isinstance(item, dict) for item in diretorios):
            raise ValueError("arq: esperada lista de diretórios")
        encontrados = [item for item in diretorios if item.get("tp") == tipo]
        if len(encontrados) != 1:
            raise ValueError(f"arq.tp: esperado exatamente um diretório {tipo}")
        template = _campo(encontrados[0], "dir", f"arq[{tipo}].dir")
    if not isinstance(template, str):
        raise ValueError(f"arq[{tipo}].dir: esperado texto")  # noqa: TRY004
    tokens = {"base": _BASE, "ambiente": "oficial", "ciclo": f"ele{ano}", "cd_eleicao": str(eleicao), "uf": uf}
    for token in re.findall(r"<([^<>]+)>", template):
        if token not in tokens:
            motivo = "código do pleito indisponível no contexto" if token == "cd_pleito" else "token desconhecido"
            raise ValueError(f"arq[{tipo}].dir: {motivo} <{token}>")
        template = template.replace(f"<{token}>", tokens[token])
    if "<" in template or ">" in template:
        raise ValueError(f"arq[{tipo}].dir: token malformado")
    if not template.startswith(f"{_BASE}/oficial/"):
        raise ValueError(f"arq[{tipo}].dir: esperado servidor de resultados oficiais do TSE")
    return template.rstrip("/")


def url_resultado(contexto: Contexto, diretorios: list[dict] | None = None) -> str:
    uf = contexto.abrangencia
    if (
        contexto.cargo not in (1, 3)
        or (contexto.cargo == 3 and uf not in _UFS)
        or (contexto.cargo == 1 and uf not in (*_UFS, "br", "zz"))
    ):
        raise ValueError(f"cargo/abrangencia: contexto inválido, eleicao={contexto.eleicao}, abrangencia={uf}")
    diretorio = _diretorio(contexto.ano, contexto.eleicao, "u", uf, diretorios)
    sufixo = "r" if contexto.ano == 2022 else "u"
    return f"{diretorio}/{uf}-c{contexto.cargo:04d}-e{contexto.eleicao:06d}-{sufixo}.json"


def url_municipios(ano: int, eleicao: int, diretorios: list[dict] | None = None) -> str:
    diretorio = _diretorio(ano, eleicao, "cm", "br", diretorios)
    return f"{diretorio}/mun-e{eleicao:06d}-cm.json"


def codigo_eleicao(dados: dict, ano: int, turno: int, cargo: int) -> int:
    """Descobre o código antes de baixar EA12, sem inferir a existência do segundo turno."""
    municipios = {"f": "o", "abr": [{"cd": sigla} for sigla in _UFS]}
    codigos = {contexto.eleicao for contexto in contextos_eleicao(dados, ano, turno, cargo, municipios)}
    if len(codigos) != 1:
        raise ValueError(f"Configuração ambígua para ano={ano}, turno={turno}, cargo={cargo}")
    return codigos.pop()
