from apuracao.grafico import pedidos_grafico


def test_grafico_remapeia_fontes_apos_mudar_ordem():
    def fonte(coluna):
        return {
            "sourceRange": {
                "sources": [
                    {
                        "sheetId": 2,
                        "startColumnIndex": coluna,
                        "endColumnIndex": coluna + 1,
                        "startRowIndex": 0,
                        "endRowIndex": 1003,
                    }
                ]
            }
        }

    aba = {
        "properties": {"sheetId": 2, "gridProperties": {"columnCount": 14}},
        "charts": [
            {
                "chartId": 10,
                "spec": {
                    "title": "% Flávio Bolsonaro e % Lula",
                    "basicChart": {
                        "domains": [{"domain": fonte(0)}],
                        "series": [{"series": fonte(6), "colorStyle": {"rgbColor": {"blue": 1}}}, {"series": fonte(2)}],
                    },
                },
                "position": {
                    "overlayPosition": {
                        "anchorCell": {"sheetId": 2, "columnIndex": 2},
                        "widthPixels": 765,
                        "heightPixels": 475,
                    }
                },
            }
        ],
    }
    pedidos = pedidos_grafico(aba, ["Data/Hora", "% Seções totalizadas", "% LULA (13)", "% FLAVIO BOLSONARO (22)"])
    spec = next(pedido["updateChartSpec"]["spec"] for pedido in pedidos if "updateChartSpec" in pedido)
    assert [
        serie["series"]["sourceRange"]["sources"][0]["startColumnIndex"] for serie in spec["basicChart"]["series"]
    ] == [3, 2]
    assert not any("updateEmbeddedObjectPosition" in pedido for pedido in pedidos)
