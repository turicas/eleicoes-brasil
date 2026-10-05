from apuracao.formatacao import pedidos_formatacao


def test_formato_leia_me_preserva_layout_editorial():
    pedidos = pedidos_formatacao(30, "LEIA-ME", [["Autoria", "Álvaro Justen"]], 22, 2)
    assert any(
        pedido.get("updateDimensionProperties", {}).get("properties", {}).get("pixelSize") == 800 for pedido in pedidos
    )
    assert any(
        pedido.get("repeatCell", {}).get("cell", {}).get("userEnteredFormat", {}).get("wrapStrategy") == "WRAP"
        for pedido in pedidos
    )
    assert any(
        pedido.get("repeatCell", {}).get("cell", {}).get("userEnteredFormat", {}).get("textFormat", {}).get("bold")
        is True
        for pedido in pedidos
    )
    assert any(
        pedido.get("autoResizeDimensions", {}).get("dimensions", {}).get("dimension") == "ROWS" for pedido in pedidos
    )
