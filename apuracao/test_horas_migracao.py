from apuracao.ajuste_visual import pedidos_horas


def test_converte_iso_antigo_em_serial_sem_perder_dia():
    pedidos = pedidos_horas(2, [["Data/Hora"], ["2026-10-04 18:30:00-03:00"], [46300.5]])
    assert len(pedidos) == 1
    atualizacao = pedidos[0]["updateCells"]
    assert atualizacao["fields"] == "userEnteredValue"
    assert atualizacao["start"] == {"sheetId": 2, "rowIndex": 1, "columnIndex": 0}
    valor = atualizacao["rows"][0]["values"][0]["userEnteredValue"]["numberValue"]
    assert valor == 46299 + 18.5 / 24


def test_serial_existente_nao_muda():
    assert pedidos_horas(2, [["Data/Hora"], [46300.5]]) == []
