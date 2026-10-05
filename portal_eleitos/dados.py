"""Normalização pura de EA20 oficial e descoberta de fontes da edição via EA11."""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

BASE_TSE = "https://resultados.tse.jus.br"
FUSO_TSE = timezone(timedelta(hours=-3))
SITUACOES_ELEITAS = frozenset({"Eleito", "Eleito por QP", "Eleito por média"})
UFS_NOMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}
CARGOS = {1, 3, 5, 6, 7, 8}


def _inteiro(valor: object, campo: str, minimo: int = 0) -> int:
    if isinstance(valor, bool) or not isinstance(valor, (int, str)):
        raise ValueError(f"{campo}: inteiro esperado")  # noqa: TRY004 - contrato de dados inválidos
    if isinstance(valor, str) and (not valor or not valor.isascii() or not valor.isdecimal()):
        raise ValueError(f"{campo}: inteiro não negativo esperado")
    numero = int(valor)
    if numero < minimo:
        raise ValueError(f"{campo}: mínimo {minimo}")
    return numero


def _identificador(valor: object, campo: str) -> str:
    _inteiro(valor, campo)
    return str(valor)


def _texto(valor: object, campo: str) -> str:
    if not isinstance(valor, str) or not valor:
        raise ValueError(f"{campo}: texto não vazio esperado")
    return valor


def _lista(valor: object, campo: str) -> list:
    if not isinstance(valor, list):
        raise ValueError(f"{campo}: lista esperada")  # noqa: TRY004 - contrato de dados inválidos
    return valor


def _opcao(valor: object, campo: str, opcoes: set[str], opcional: bool = False) -> str | None:
    if opcional and valor is None:
        return None
    if not isinstance(valor, str) or valor not in opcoes:
        raise ValueError(f"{campo}: valor inválido {valor!r}")
    return valor


def _booleano(valor: object, campo: str, opcional: bool = False) -> bool | None:
    opcao = _opcao(valor, campo, {"s", "n"}, opcional)
    return None if opcao is None else opcao == "s"


def _uf(valor: str) -> str:
    codigo = _texto(valor, "UF").upper()
    if codigo != "BR" and codigo not in UFS_NOMES:
        raise ValueError(f"UF desconhecida: {codigo}")
    return codigo


def _url_oficial(url: str) -> str:
    partes = urlsplit(_texto(url, "URL"))
    if (
        partes.scheme != "https"
        or partes.netloc != "resultados.tse.jus.br"
        or partes.username
        or partes.password
        or partes.query
        or partes.fragment
        or "\\" in url
        or "%" in partes.path
        or "<" in url
        or ">" in url
        or any(parte in {".", ".."} for parte in partes.path.split("/"))
        or not partes.path.startswith("/oficial/")
    ):
        raise ValueError(f"URL oficial inválida: {url!r}")
    return url


def _data_hora(data: object, hora: object, campo: str, opcional: bool = False) -> str | None:
    if opcional and data in (None, "") and hora in (None, ""):
        return None
    data = _texto(data, campo)
    hora = _texto(hora, campo)
    valor = datetime.strptime(f"{data} {hora}-03:00", "%d/%m/%Y %H:%M:%S%z")
    if valor.strftime("%d/%m/%Y %H:%M:%S") != f"{data} {hora}":
        raise ValueError(f"{campo}: formato esperado dd/mm/aaaa hh:mm:ss")
    return valor.replace(tzinfo=FUSO_TSE).isoformat()


def _contexto(ano: int, eleicao: int, turno: int, cargo: int, uf: str) -> str:
    return f"ano={ano}, eleição={eleicao}, turno={turno}, cargo={cargo}, abrangência={uf}"


def url_foto(*, ano: int, eleicao: int, uf: str, sequencial_tse: str, config: dict | None = None) -> str:
    """Resolve ft do EA11; sem configuração usa o caminho oficial do ciclo informado."""
    ano = _inteiro(ano, "ano", 1)
    eleicao = _inteiro(eleicao, "eleicao", 1)
    uf = _uf(uf).lower()
    sequencial_tse = _identificador(sequencial_tse, "sqcand")
    if config is None:
        diretorio = f"{BASE_TSE}/oficial/ele{ano}/{eleicao}/fotos/{uf}"
    else:
        if config.get("f") != "o":
            raise ValueError("EA11: configuração não oficial")
        pleitos = [
            pleito
            for pleito in _lista(config["pl"], "pl")
            if any(_inteiro(evento["cd"], "cd", 1) == eleicao for evento in _lista(pleito["e"], "e"))
        ]
        if len(pleitos) != 1:
            raise ValueError(f"EA11: eleição {eleicao} ausente ou ambígua")
        diretorio = _diretorio(config, "ft", pleitos[0], eleicao, uf)
    return _url_oficial(f"{diretorio}/{sequencial_tse}.jpeg")


def normalizar_resultado(
    dados: dict,
    *,
    ano: int,
    eleicao: int,
    turno: int,
    cargo: int,
    uf: str,
    url: str,
    capturado_em: str,
    hash_bruto: str,
) -> dict:
    """Seleciona situações oficiais finais; inconsistências abortam, nunca inferem eleitos."""
    contexto = _contexto(ano, eleicao, turno, cargo, str(uf).upper())
    try:
        ano = _inteiro(ano, "ano", 1)
        eleicao = _inteiro(eleicao, "eleicao", 1)
        turno = _inteiro(turno, "turno", 1)
        cargo = _inteiro(cargo, "cargo", 1)
        uf = _uf(uf)
        if turno not in {1, 2} or cargo not in CARGOS:
            raise ValueError("turno ou cargo fora do escopo")
        if (cargo == 1) != (uf == "BR") or (cargo == 8 and uf != "DF") or (cargo == 7 and uf == "DF"):
            raise ValueError("cargo incompatível com a abrangência da disputa")
        if dados["f"] != "o":
            raise ValueError("f: resultado não oficial")
        if _inteiro(dados["ele"], "ele", 1) != eleicao or _inteiro(dados["t"], "t", 1) != turno:
            raise ValueError("ele/t: contexto divergente")
        tipo = "br" if uf == "BR" else "uf"
        if dados["tpabr"] != tipo or _uf(dados["cdabr"]) != uf:
            raise ValueError("tpabr/cdabr: abrangência divergente")
        cargos = [item for item in _lista(dados["carg"], "carg") if _inteiro(item["cd"], "carg.cd", 1) == cargo]
        if len(cargos) != 1:
            raise ValueError("carg: cargo ausente ou duplicado")
        cargo_tse = cargos[0]
        tf = _booleano(dados["tf"], "tf")
        md = _opcao(dados.get("md"), "md", {"e", "s", "n"}, True)
        andamento = _opcao(dados["and"], "and", {"n", "p", "f"})
        sem_eleitos = _booleano(dados.get("esae"), "esae", True)
        motivos = list(_lista(dados.get("mnae", []), "mnae"))
        if sem_eleitos and not tf:
            raise ValueError("esae=s exige tf=s")
        url = _url_oficial(url)
        captura = datetime.fromisoformat(_texto(capturado_em, "capturado_em"))
        if captura.utcoffset() is None:
            raise ValueError("capturado_em: fuso obrigatório")
        if (
            not isinstance(hash_bruto, str)
            or len(hash_bruto) != 64
            or any(caractere not in "0123456789abcdefABCDEF" for caractere in hash_bruto)
        ):
            raise ValueError("hash_bruto: SHA-256 hexadecimal esperado")
        eleitos = []
        segundo_turno = md == "s"
        sequenciais = set()
        for agregacao in _lista(cargo_tse.get("agr", []), "agr"):
            for partido in _lista(agregacao.get("par", []), "par"):
                for candidato in _lista(partido.get("cand", []), "cand"):
                    votos = _inteiro(candidato["vap"], "cand.vap")
                    situacao = candidato.get("st")
                    segundo_turno = segundo_turno or (tf and situacao == "2º turno")
                    if not isinstance(situacao, str) or situacao not in SITUACOES_ELEITAS:
                        continue
                    if not tf or sem_eleitos:
                        raise ValueError("st eleito incompatível com tf/esae")
                    sequencial = _identificador(candidato["sqcand"], "sqcand")
                    if sequencial in sequenciais:
                        raise ValueError(f"sqcand duplicado: {sequencial}")
                    sequenciais.add(sequencial)
                    eleitos.append(
                        {
                            "sequencial_tse": sequencial,
                            "numero": _identificador(candidato["n"], "cand.n"),
                            "nome": _texto(candidato["nm"], "cand.nm"),
                            "nome_urna": _texto(candidato["nmu"], "cand.nmu"),
                            "partido": {
                                "numero": (
                                    _identificador(partido["n"], "par.n") if partido.get("n") is not None else None
                                ),
                                "sigla": partido.get("sg"),
                                "nome": partido.get("nm"),
                            },
                            "votos": votos,
                            "situacao": situacao,
                            "destinacao_votos": candidato.get("dvt"),
                            "foto": {
                                "estado": "pendente",
                                "url": None,
                                "sha256": None,
                                "largura": None,
                                "altura": None,
                                "formato": "webp",
                                "fonte_tse": url_foto(ano=ano, eleicao=eleicao, uf=uf, sequencial_tse=sequencial),
                            },
                        }
                    )
        eleitos.sort(key=lambda candidato: (-candidato["votos"], candidato["nome_urna"], candidato["sequencial_tse"]))
        estado = (
            "sem-eleitos" if sem_eleitos else "segundo-turno" if segundo_turno else "finalizado" if tf else "pendente"
        )
        return {
            "cargo": {"codigo": cargo, "nome": _texto(cargo_tse["nmn"], "carg.nmn")},
            "abrangencia_disputa": {"tipo": tipo, "codigo": uf},
            "eleicao": eleicao,
            "turno": turno,
            "vagas": _inteiro(cargo_tse["nv"], "nv") if cargo_tse.get("nv") is not None else None,
            "tf": tf,
            "md": md,
            "andamento": andamento,
            "sem_atribuicao_eleitos": sem_eleitos,
            "motivos": motivos,
            "estado": estado,
            "fonte": {
                "url": url,
                "eleicao": eleicao,
                "turno": turno,
                "cargo": cargo,
                "abrangencia": uf,
                "gerado_em": _data_hora(dados["dg"], dados["hg"], "dg/hg"),
                "totalizado_em": _data_hora(dados.get("dt"), dados.get("ht"), "dt/ht", True),
                "idg": _identificador(dados["idg"], "idg"),
                "capturado_em": capturado_em,
                "sha256_bruto": hash_bruto,
                "estado_coleta": "sucesso",
            },
            "eleitos": eleitos,
        }
    except (KeyError, TypeError, ValueError, AttributeError) as erro:
        raise ValueError(f"EA20 ({contexto}): {erro}") from erro


def _diretorio(config: dict, tipo: str, pleito: dict, eleicao: int, uf: str) -> str:
    diretorios = [item["dir"] for item in _lista(config["arq"], "arq") if item["tp"] == tipo]
    if len(diretorios) != 1:
        raise ValueError(f"arq: diretório {tipo!r} ausente ou duplicado")
    diretorio = _texto(diretorios[0], "arq.dir")
    substituicoes = {
        "base": BASE_TSE,
        "ambiente": "oficial",
        "ciclo": _texto(pleito["c"], "pl.c"),
        "cd_eleicao": str(eleicao),
        "uf": uf.lower(),
        "cd_pleito": str(_inteiro(pleito["cd"], "pl.cd", 1)),
    }
    for token, valor in substituicoes.items():
        diretorio = diretorio.replace(f"<{token}>", valor)
    return _url_oficial(diretorio.rstrip("/"))


def descobrir_fontes(config: dict, ano: int, turno: int) -> list[dict]:
    """Seleciona eventos ordinários explícitos; BR estadual expande somente cargos presentes em cp."""
    contexto = f"ano={ano}, turno={turno}"
    try:
        ano = _inteiro(ano, "ano", 1)
        turno = _inteiro(turno, "turno", 1)
        if turno not in {1, 2}:
            raise ValueError("turno deve ser 1 ou 2")
        if config["f"] != "o":
            raise ValueError("configuração não oficial")
        fontes = {}
        for pleito in _lista(config["pl"], "pl"):
            data = datetime.strptime(_texto(pleito["dt"], "pl.dt"), "%d/%m/%Y").replace(tzinfo=timezone.utc)
            if data.year != ano:
                continue
            for evento in _lista(pleito["e"], "e"):
                if _inteiro(evento["tp"], "e.tp", 1) not in {1, 8} or _inteiro(evento["t"], "e.t", 1) != turno:
                    continue
                eleicao = _inteiro(evento["cd"], "e.cd", 1)
                for abrangencia in _lista(evento["abr"], "abr"):
                    uf_config = _uf(abrangencia["cd"])
                    for item_cargo in _lista(abrangencia["cp"], "cp"):
                        cargo = _inteiro(item_cargo["cd"], "cp.cd", 1)
                        if cargo not in CARGOS or (turno == 2 and cargo not in {1, 3}):
                            continue
                        if cargo == 1:
                            if uf_config != "BR":
                                continue
                            territorios = ["BR"]
                        else:
                            territorios = sorted(UFS_NOMES) if uf_config == "BR" else [uf_config]
                        for uf in territorios:
                            if (cargo == 7 and uf == "DF") or (cargo == 8 and uf != "DF"):
                                continue
                            diretorio = _diretorio(config, "u", pleito, eleicao, uf)
                            url = _url_oficial(f"{diretorio}/{uf.lower()}-c{cargo:04d}-e{eleicao:06d}-u.json")
                            chave = (eleicao, cargo, uf)
                            fonte = {
                                "ano": ano,
                                "eleicao": eleicao,
                                "turno": turno,
                                "cargo": cargo,
                                "uf": uf,
                                "url": url,
                            }
                            if chave in fontes and fontes[chave] != fonte:
                                raise ValueError(f"fonte ambígua: {chave}")
                            fontes[chave] = fonte
        return sorted(fontes.values(), key=lambda fonte: (fonte["cargo"], fonte["uf"], fonte["eleicao"]))
    except (KeyError, TypeError, ValueError, AttributeError) as erro:
        raise ValueError(f"EA11 ({contexto}): {erro}") from erro
