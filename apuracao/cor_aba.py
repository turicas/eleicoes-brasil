"""Cores de abas baseadas exclusivamente na definição oficial da disputa."""

from .modelo import Resultado

CORES = {
    "verde": {"red": 0, "green": 156 / 255, "blue": 59 / 255},
    "azul": {"red": 0, "green": 0, "blue": 1},
    "preto": {"red": 0, "green": 0, "blue": 0},
}


def cor_resultado(resultado: Resultado) -> str | None:
    if resultado.origem != "tse":
        return None
    if resultado.matematicamente_definida == "e":
        return "verde"
    if resultado.matematicamente_definida == "s":
        return "azul"
    if resultado.finalizada:
        situacoes = {candidato.situacao for candidato in resultado.candidatos}
        if "Eleito" in situacoes:
            return "verde"
        if "2º turno" in situacoes:
            return "azul"
    return "preto"


def pedido_cor(identificador: int, cor: str) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": identificador, "tabColorStyle": {"rgbColor": CORES[cor]}},
            "fields": "tabColorStyle",
        }
    }
