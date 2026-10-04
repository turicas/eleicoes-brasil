from apuracao.grafico import pedidos_expansao


def test_expande_intervalos_do_grafico_sem_criar_outro():
    aba = {
        "properties": {"sheetId": 2},
        "charts": [
            {
                "chartId": 10,
                "spec": {
                    "title": "% Flávio Bolsonaro e % Lula",
                    "basicChart": {
                        "domains": [{"domain": {"sourceRange": {"sources": [{"sheetId": 2, "endRowIndex": 3}]}}}],
                        "series": [{"series": {"sourceRange": {"sources": [{"sheetId": 2, "endRowIndex": 3}]}}}],
                    },
                },
            }
        ],
    }
    pedidos = pedidos_expansao(aba, 10)
    assert len(pedidos) == 1
    assert pedidos[0]["updateChartSpec"]["chartId"] == 10
    assert (
        pedidos[0]["updateChartSpec"]["spec"]["basicChart"]["domains"][0]["domain"]["sourceRange"]["sources"][0][
            "endRowIndex"
        ]
        == 10
    )
    assert (
        aba["charts"][0]["spec"]["basicChart"]["domains"][0]["domain"]["sourceRange"]["sources"][0]["endRowIndex"] == 3
    )
    assert pedidos_expansao(aba, 3) == []


def test_preserva_graficos_alheios():
    assert (
        pedidos_expansao(
            {
                "properties": {"sheetId": 2},
                "charts": [{"chartId": 10, "spec": {"title": "Meu gráfico", "basicChart": {}}}],
            },
            10,
        )
        == []
    )
