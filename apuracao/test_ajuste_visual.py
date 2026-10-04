from apuracao.ajuste_visual import monta_formatacao
from apuracao.test_formatacao import linhas


def aba(nome, identificador):
    return {
        "properties": {"sheetId": identificador, "title": nome, "gridProperties": {"rowCount": 20, "columnCount": 6}}
    }


def test_ajuste_so_formata_resultados_preserva_valores_e_historico():
    metadados = {"sheets": [aba("Presidente", 1), aba("SP", 28), aba("AC", 2), aba("LinhaDoTempo", 3), aba("Notas", 4)]}
    valores = {nome: linhas() for nome in ("Presidente", "SP", "AC")}
    pedidos, nomes = monta_formatacao(metadados, valores)
    assert nomes == ["Presidente", "SP", "AC"]
    assert pedidos
    assert all(
        not {"updateCells", "addSheet", "deleteSheet", "updateSpreadsheetProperties"}.intersection(pedido)
        for pedido in pedidos
    )
    assert {pedido["repeatCell"]["range"]["sheetId"] for pedido in pedidos if "repeatCell" in pedido} == {1, 28, 2}
