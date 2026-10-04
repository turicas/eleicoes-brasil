from apuracao.ajuste_visual import monta_formatacao
from apuracao.test_formatacao import linhas


def aba(nome, identificador):
    return {
        "properties": {"sheetId": identificador, "title": nome, "gridProperties": {"rowCount": 20, "columnCount": 6}}
    }


def test_ajuste_formata_todas_as_abas_sem_alterar_valores():
    metadados = {"sheets": [aba("Presidente", 1), aba("SP", 28), aba("AC", 2), aba("LinhaDoTempo", 3), aba("Notas", 4)]}
    valores = {nome: linhas() for nome in ("Presidente", "SP", "AC")}
    valores.update({"LinhaDoTempo": [["Data/Hora", "% Lula (13)"]], "Notas": [["Anotações"]]})
    pedidos, nomes = monta_formatacao(metadados, valores)
    assert nomes == ["Presidente", "SP", "AC", "LinhaDoTempo", "Notas"]
    assert pedidos
    assert all(
        not {"updateCells", "addSheet", "deleteSheet", "updateSpreadsheetProperties"}.intersection(pedido)
        for pedido in pedidos
    )
    assert {pedido["repeatCell"]["range"]["sheetId"] for pedido in pedidos if "repeatCell" in pedido} == {
        1,
        28,
        2,
        3,
        4,
    }


def test_execucao_le_todas_as_colunas_com_nomes_escapados(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace

    from apuracao.ajuste_visual import executar

    metadados = {"sheets": [aba("Presidente", 1), aba("LinhaDoTempo", 2), aba("D'Água", 3)]}
    metadados["sheets"][1]["properties"]["gridProperties"]["columnCount"] = 28
    recebidos = []

    def valores(intervalos, params):
        assert params == {"valueRenderOption": "UNFORMATTED_VALUE"}
        recebidos.extend(intervalos)
        return {"valueRanges": [{"values": linhas()}, {"values": [["Data/Hora"]]}, {"values": [["Nota"]]}]}

    planilha = SimpleNamespace(fetch_sheet_metadata=lambda **kwargs: metadados, values_batch_get=valores)
    cliente = SimpleNamespace(set_timeout=lambda tempo: None, open_by_key=lambda identificador: planilha)
    monkeypatch.setitem(sys.modules, "gspread", SimpleNamespace(service_account=lambda **kwargs: cliente))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "credenciais-falsas.json")
    monkeypatch.chdir(tmp_path)
    executar(SimpleNamespace(planilha="id-falso", aplicar=False, grafico=False))
    assert recebidos == ["'Presidente'!A:F", "'LinhaDoTempo'!A:AB", "'D''Água'!A:F"]
