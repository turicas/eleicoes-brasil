from apuracao.planilha import Planilha, TabelaPlanilha
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada, aba


def test_publicacao_remapeia_grafico_junto_a_valores():
    remota = PlanilhaSimulada({2: aba("LinhaDoTempo", 100, 8, 2)})
    remota.abas[2]["charts"] = [
        {
            "chartId": 10,
            "spec": {
                "title": "% Flávio Bolsonaro e % Lula",
                "basicChart": {
                    "series": [
                        {
                            "series": {
                                "sourceRange": {"sources": [{"sheetId": 2, "startColumnIndex": 6, "endColumnIndex": 7}]}
                            }
                        },
                        {
                            "series": {
                                "sourceRange": {"sources": [{"sheetId": 2, "startColumnIndex": 2, "endColumnIndex": 3}]}
                            }
                        },
                    ]
                },
            },
        }
    ]
    writer = Planilha(ClienteSimulado(remota), "ID", 2026, 1)
    writer.publicar(
        [
            TabelaPlanilha(
                "LinhaDoTempo",
                [["Data/Hora", "% Seções totalizadas", "% LULA (13)", "% FLAVIO BOLSONARO (22)"], [1, 0.5, 0.4, 0.5]],
            )
        ]
    )
    pedidos = remota.lotes[-1]["requests"]
    spec = next(pedido["updateChartSpec"]["spec"] for pedido in pedidos if "updateChartSpec" in pedido)
    assert spec["basicChart"]["series"][0]["series"]["sourceRange"]["sources"][0]["startColumnIndex"] == 3
    assert not any("repeatCell" in pedido or "autoResizeDimensions" in pedido for pedido in pedidos)
