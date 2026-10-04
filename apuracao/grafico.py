"""Pedidos puros para o gráfico da LinhaDoTempo, sem cliente nem autenticação."""

import re
import unicodedata
from copy import deepcopy

TITULO = "% Flávio Bolsonaro e % Lula"


def _normalizar(texto: str) -> str:
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(caractere)
    ).strip()


def _coluna(cabecalho: list[str], nome: str, numero: int) -> int:
    encontrados = []
    for indice, rotulo in enumerate(cabecalho):
        texto = _normalizar(rotulo)
        candidato = re.fullmatch(r"%\s*(.+?)\s*\((\d+)\)", texto)
        if candidato and int(candidato.group(2)) == numero and _normalizar(nome) in candidato.group(1):
            encontrados.append(indice)
    if not encontrados:
        raise ValueError(f"Cabeçalho percentual de {nome} ({numero}) ausente.")
    if len(encontrados) > 1:
        raise ValueError(f"Cabeçalho percentual de {nome} ({numero}) ambíguo.")
    return encontrados[0]


def _fonte(identificador: int, coluna: int, linha: int = 0) -> dict:
    return {
        "sheetId": identificador,
        "startRowIndex": linha,
        "startColumnIndex": coluna,
        "endColumnIndex": coluna + 1,
    }


def _candidato(grafico: dict) -> bool:
    especificacao = grafico.get("spec", {})
    titulo = _normalizar(especificacao.get("title", ""))
    basico = especificacao.get("basicChart", {})
    return ("flavio" in titulo and "lula" in titulo) or (
        (not titulo or re.match(r"^\d{4}-\d{2}-\d{2} ", titulo))
        and basico.get("chartType") == "LINE"
        and not basico.get("series")
    )


def pedidos_grafico(aba: dict, cabecalho: list[str]) -> list[dict]:
    """Cria ou reaproveita um único gráfico, preservando outros e a âncora existente.

    Os intervalos são abertos para novas linhas. A API não oferece formato numérico
    no eixo básico: formata as células de origem e fixa o mínimo Y em 40%.
    A API também não expõe rotação dos rótulos do eixo X.
    """
    if not cabecalho or _normalizar(cabecalho[0]) != "data/hora":
        raise ValueError("A coluna A deve conter o cabeçalho Data/Hora.")
    coluna_flavio = _coluna(cabecalho, "Flávio", 22)
    coluna_lula = _coluna(cabecalho, "Lula", 13)
    candidatos = [grafico for grafico in aba.get("charts", []) if _candidato(grafico)]
    if len(candidatos) > 1:
        raise ValueError("Seleção de gráfico ambígua: há mais de um gráfico de Flávio/Lula ou LINE vazio.")
    existente = candidatos[0] if candidatos else None
    identificador = aba["properties"]["sheetId"]
    especificacao = {
        "title": TITULO,
        "basicChart": {
            "chartType": "LINE",
            "legendPosition": "TOP_LEGEND",
            "headerCount": 1,
            "axis": [
                {"position": "BOTTOM_AXIS", "title": "Data/Hora"},
                {
                    "position": "LEFT_AXIS",
                    "title": "Percentual de votos",
                    "viewWindowOptions": {"viewWindowMin": 0.4, "viewWindowMode": "EXPLICIT"},
                },
            ],
            "domains": [{"domain": {"sourceRange": {"sources": [_fonte(identificador, 0)]}}}],
            "series": [
                {
                    "series": {"sourceRange": {"sources": [_fonte(identificador, coluna)]}},
                    "targetAxis": "LEFT_AXIS",
                    "colorStyle": {"rgbColor": cor},
                }
                for coluna, cor in (
                    (coluna_flavio, {"red": 66 / 255, "green": 133 / 255, "blue": 244 / 255}),
                    (coluna_lula, {"red": 1, "green": 0, "blue": 0}),
                )
            ],
        },
    }
    if existente:
        anterior = deepcopy(existente.get("spec", {}))
        basico_anterior = anterior.get("basicChart", {})
        basico = especificacao["basicChart"]
        for chave in ("axis", "domains", "series"):
            antigos = basico_anterior.get(chave, [])
            for indice, item in enumerate(basico[chave]):
                if chave == "axis":
                    original = next((eixo for eixo in antigos if eixo.get("position") == item["position"]), {})
                elif chave == "series":
                    fontes = item["series"]["sourceRange"]["sources"]
                    original = next(
                        (
                            serie
                            for serie in antigos
                            if any(
                                fonte.get("sheetId") == fontes[0]["sheetId"]
                                and fonte.get("startColumnIndex") == fontes[0]["startColumnIndex"]
                                for fonte in serie.get("series", {}).get("sourceRange", {}).get("sources", [])
                            )
                        ),
                        {},
                    )
                else:
                    original = antigos[indice] if indice < len(antigos) else {}
                combinado = deepcopy(original)
                for campo, valor in item.items():
                    if campo in ("domain", "series") and combinado.get(campo, {}).get("sourceRange"):
                        continue
                    if campo == "viewWindowOptions":
                        combinado.setdefault(campo, {}).update(valor)
                    else:
                        combinado[campo] = valor
                basico[chave][indice] = combinado
        basico_anterior.update(basico)
        especificacao["basicChart"] = basico_anterior
        anterior.update(especificacao)
        especificacao = anterior
    posicao = deepcopy(existente.get("position", {})) if existente else {}
    if not posicao:
        posicao = {
            "overlayPosition": {
                "anchorCell": {"sheetId": identificador, "rowIndex": 1, "columnIndex": max(15, len(cabecalho) + 1)}
            }
        }
    sobreposta = posicao.get("overlayPosition")
    if sobreposta is not None:
        sobreposta.setdefault("widthPixels", 660)
        sobreposta.setdefault("heightPixels", 410)
    colunas = len(cabecalho)
    if sobreposta is not None and sobreposta["anchorCell"]["sheetId"] == identificador:
        colunas = max(colunas, sobreposta["anchorCell"].get("columnIndex", 0) + 1)
    pedidos = []
    if colunas > aba["properties"]["gridProperties"]["columnCount"]:
        pedidos.append(
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": identificador, "gridProperties": {"columnCount": colunas}},
                    "fields": "gridProperties.columnCount",
                }
            }
        )
    for coluna in (0, coluna_flavio, coluna_lula):
        numero = (
            {"type": "DATE_TIME", "pattern": "HH:mm:ss"} if coluna == 0 else {"type": "PERCENT", "pattern": "0.00%"}
        )
        pedidos.append(
            {
                "repeatCell": {
                    "range": _fonte(identificador, coluna, linha=1),
                    "cell": {"userEnteredFormat": {"numberFormat": numero}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
        )
    if existente is None:
        pedidos.append({"addChart": {"chart": {"spec": especificacao, "position": posicao}}})
    else:
        if existente.get("spec") != especificacao:
            pedidos.append({"updateChartSpec": {"chartId": existente["chartId"], "spec": especificacao}})
        if existente.get("position") != posicao:
            pedidos.append(
                {
                    "updateEmbeddedObjectPosition": {
                        "objectId": existente["chartId"],
                        "newPosition": posicao,
                        "fields": "*",
                    }
                }
            )
    return pedidos


def pedidos_expansao(aba: dict, total_linhas: int) -> list[dict]:
    """Expande apenas fontes do gráfico administrado quando o Sheets materializa intervalos abertos."""
    pedidos = []
    for grafico in aba.get("charts", []):
        titulo = _normalizar(grafico.get("spec", {}).get("title", ""))
        if "flavio" not in titulo or "lula" not in titulo:
            continue
        spec = deepcopy(grafico["spec"])
        basico = spec.get("basicChart", {})
        fontes = [item.get("domain", {}) for item in basico.get("domains", [])]
        fontes.extend(item.get("series", {}) for item in basico.get("series", []))
        mudou = False
        for fonte in fontes:
            for intervalo in fonte.get("sourceRange", {}).get("sources", []):
                if intervalo.get("sheetId") != aba["properties"]["sheetId"]:
                    continue
                limite = intervalo.get("endRowIndex")
                if limite is not None and limite < total_linhas:
                    intervalo["endRowIndex"] = total_linhas
                    mudou = True
        if mudou:
            pedidos.append({"updateChartSpec": {"chartId": grafico["chartId"], "spec": spec}})
    return pedidos


def pedidos_remapeamento(aba: dict, cabecalho: list[str]) -> list[dict]:
    """Atualiza só as fontes das séries administradas, preservando customizações do gráfico."""
    grafico = next(
        (
            item
            for item in aba.get("charts", [])
            if "flavio" in _normalizar(item.get("spec", {}).get("title", ""))
            and "lula" in _normalizar(item.get("spec", {}).get("title", ""))
        ),
        None,
    )
    if grafico is None:
        return []
    spec = deepcopy(grafico["spec"])
    series = spec.get("basicChart", {}).get("series", [])
    if len(series) != 2:
        raise ValueError("Gráfico presidencial precisa ter exatamente duas séries")
    mudou = False
    for serie, coluna in zip(series, (_coluna(cabecalho, "Flávio", 22), _coluna(cabecalho, "Lula", 13)), strict=True):
        for intervalo in serie["series"]["sourceRange"]["sources"]:
            if intervalo.get("sheetId") == aba["properties"]["sheetId"] and intervalo.get("startColumnIndex") != coluna:
                intervalo.update(startColumnIndex=coluna, endColumnIndex=coluna + 1)
                mudou = True
    return [{"updateChartSpec": {"chartId": grafico["chartId"], "spec": spec}}] if mudou else []
