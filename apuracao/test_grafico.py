from copy import deepcopy

import pytest

from .grafico import pedidos_grafico

CABECALHO = ["Data/Hora", "% Seções totalizadas", "% LULA (13)", "% FLAVIO BOLSONARO (22)"]


@pytest.fixture
def aba():
    return {"properties": {"sheetId": 73, "gridProperties": {"columnCount": 26, "rowCount": 100}}, "charts": []}


def grafico_adicionado(pedidos):
    return next(pedido["addChart"]["chart"] for pedido in pedidos if "addChart" in pedido)


def test_linhas_cores_e_json_documentado(aba):
    grafico = grafico_adicionado(pedidos_grafico(aba, CABECALHO))
    assert grafico["spec"]["title"] == "% Flávio Bolsonaro e % Lula"
    basico = grafico["spec"]["basicChart"]
    assert set(basico) == {"chartType", "legendPosition", "headerCount", "axis", "domains", "series"}
    assert basico["chartType"] == "LINE"
    assert basico["legendPosition"] == "TOP_LEGEND"
    assert basico["headerCount"] == 1
    assert basico["axis"] == [
        {"position": "BOTTOM_AXIS", "title": "Data/Hora"},
        {
            "position": "LEFT_AXIS",
            "title": "Percentual de votos",
            "viewWindowOptions": {"viewWindowMin": 0.4, "viewWindowMode": "EXPLICIT"},
        },
    ]
    assert basico["domains"] == [
        {
            "domain": {
                "sourceRange": {
                    "sources": [{"sheetId": 73, "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": 1}]
                }
            }
        }
    ]
    assert basico["series"] == [
        {
            "series": {
                "sourceRange": {
                    "sources": [{"sheetId": 73, "startRowIndex": 0, "startColumnIndex": 3, "endColumnIndex": 4}]
                }
            },
            "targetAxis": "LEFT_AXIS",
            "colorStyle": {"rgbColor": {"red": 66 / 255, "green": 133 / 255, "blue": 244 / 255}},
        },
        {
            "series": {
                "sourceRange": {
                    "sources": [{"sheetId": 73, "startRowIndex": 0, "startColumnIndex": 2, "endColumnIndex": 3}]
                }
            },
            "targetAxis": "LEFT_AXIS",
            "colorStyle": {"rgbColor": {"red": 1, "green": 0, "blue": 0}},
        },
    ]
    assert grafico["position"] == {
        "overlayPosition": {
            "anchorCell": {"sheetId": 73, "rowIndex": 1, "columnIndex": 15},
            "widthPixels": 660,
            "heightPixels": 410,
        }
    }


def test_percentual_usa_formato_das_celulas_sem_inventar_formato_do_eixo(aba):
    pedidos = pedidos_grafico(aba, CABECALHO)
    formatos = [pedido["repeatCell"] for pedido in pedidos if "repeatCell" in pedido]
    assert len(formatos) == 3
    horario = next(formato for formato in formatos if formato["range"]["startColumnIndex"] == 0)
    assert horario["cell"]["userEnteredFormat"]["numberFormat"] == {"type": "DATE_TIME", "pattern": "HH:mm:ss"}
    formatos.remove(horario)
    assert {formato["range"]["startColumnIndex"] for formato in formatos} == {2, 3}
    for formato in formatos:
        assert formato["range"]["startRowIndex"] == 1
        assert "endRowIndex" not in formato["range"]
        assert formato["cell"] == {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}}
        assert formato["fields"] == "userEnteredFormat.numberFormat"


@pytest.mark.parametrize(
    "cabecalho, colunas",
    [
        (["Data/Hora", "% FLÁVIO BOLSONARO (22)", "Outro", "% Lula (13)"], [1, 3]),
        (["Data/Hora", "% Outra pessoa (22)", "% LULA (131)", "% Flavio Bolsonaro (22)", "% LULA (13)"], [3, 4]),
        (["Data/Hora"] + ["Outro"] * 18 + ["% Lula (13)", "% flavio bolsonaro (22)"], [20, 19]),
    ],
)
def test_colunas_arbitrarias_reordenadas_e_acentos(aba, cabecalho, colunas):
    grafico = grafico_adicionado(pedidos_grafico(aba, cabecalho))
    assert [
        serie["series"]["sourceRange"]["sources"][0]["startColumnIndex"]
        for serie in grafico["spec"]["basicChart"]["series"]
    ] == colunas
    assert grafico["position"]["overlayPosition"]["anchorCell"]["columnIndex"] == max(15, len(cabecalho) + 1)


@pytest.mark.parametrize(
    "cabecalho, mensagem",
    [
        (["Data/Hora", "% Lula (13)"], "Flávio"),
        (["Data/Hora", "% FLAVIO BOLSONARO (22)"], "Lula"),
        (CABECALHO + ["% Lula (13)"], "ambígu"),
        (CABECALHO + ["% FLÁVIO (22)"], "ambígu"),
        (["Horário"] + CABECALHO[1:], "Data/Hora"),
    ],
)
def test_cabecalho_ausente_ou_ambiguo_falha_explicitamente(aba, cabecalho, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        pedidos_grafico(aba, cabecalho)


def test_aumenta_grade_antes_de_criar_sem_restringir_linhas(aba):
    aba["properties"]["gridProperties"]["columnCount"] = 4
    pedidos = pedidos_grafico(aba, CABECALHO)
    assert pedidos[0] == {
        "updateSheetProperties": {
            "properties": {"sheetId": 73, "gridProperties": {"columnCount": 16}},
            "fields": "gridProperties.columnCount",
        }
    }


@pytest.mark.parametrize(
    "spec",
    [
        {"basicChart": {"chartType": "LINE"}},
        {"title": "", "basicChart": {"chartType": "LINE", "series": []}},
        {"title": "% FLAVIO e % LULA", "basicChart": {"chartType": "LINE", "series": [{}]}},
    ],
)
def test_reaproveita_sem_apagar_outros_nem_mutar_entrada(aba, spec):
    outro = {"chartId": 11, "spec": {"title": "Meu gráfico", "basicChart": {"chartType": "LINE"}}}
    aba["charts"] = [outro, {"chartId": 12, "spec": spec}]
    anterior = deepcopy(aba)
    pedidos = pedidos_grafico(aba, CABECALHO)
    assert aba == anterior
    assert not any("addChart" in pedido or "deleteEmbeddedObject" in pedido for pedido in pedidos)
    assert next(pedido["updateChartSpec"]["chartId"] for pedido in pedidos if "updateChartSpec" in pedido) == 12
    movimento = next(
        pedido["updateEmbeddedObjectPosition"] for pedido in pedidos if "updateEmbeddedObjectPosition" in pedido
    )
    assert movimento["objectId"] == 12
    assert movimento["fields"] == "*"
    assert movimento["newPosition"]["overlayPosition"]["anchorCell"]["columnIndex"] == 15


def test_preserva_ancora_e_offsets_do_usuario_ao_redimensionar(aba):
    posicao = {
        "overlayPosition": {
            "anchorCell": {"sheetId": 73, "rowIndex": 7, "columnIndex": 20},
            "offsetXPixels": 23,
            "offsetYPixels": 19,
            "widthPixels": 600,
            "heightPixels": 371,
        }
    }
    aba["charts"] = [{"chartId": 0, "spec": {"title": "% Flávio Bolsonaro e % Lula"}, "position": posicao}]
    pedidos = pedidos_grafico(aba, CABECALHO)
    assert not any("updateEmbeddedObjectPosition" in pedido for pedido in pedidos)
    assert aba["charts"][0]["position"] == posicao


@pytest.mark.parametrize(
    "specs",
    [
        [{"basicChart": {"chartType": "LINE"}}] * 2,
        [{"title": "Flávio e Lula"}, {"title": "Lula e FLAVIO"}],
        [{"title": "Flávio e Lula"}, {"basicChart": {"chartType": "LINE"}}],
    ],
)
def test_multiplos_candidatos_nao_escolhe_nem_apaga(aba, specs):
    aba["charts"] = [{"chartId": indice, "spec": spec} for indice, spec in enumerate(specs)]
    with pytest.raises(ValueError, match="ambígu"):
        pedidos_grafico(aba, CABECALHO)


def test_outros_graficos_preservados(aba):
    aba["charts"] = [
        {"chartId": 1, "spec": {"basicChart": {"chartType": "LINE", "series": [{}]}}},
        {"chartId": 2, "spec": {"basicChart": {"chartType": "COLUMN"}}},
        {"chartId": 3, "spec": {"title": "Lula", "basicChart": {"chartType": "LINE"}}},
    ]
    pedidos = pedidos_grafico(aba, CABECALHO)
    assert sum("addChart" in pedido for pedido in pedidos) == 1
    assert not any("updateChartSpec" in pedido or "deleteEmbeddedObject" in pedido for pedido in pedidos)


def test_idempotente_apos_aplicacao_dos_pedidos_em_metadados_falsos(aba):
    aba["properties"]["gridProperties"]["columnCount"] = 4
    for pedido in pedidos_grafico(aba, CABECALHO):
        if "updateSheetProperties" in pedido:
            aba["properties"]["gridProperties"].update(pedido["updateSheetProperties"]["properties"]["gridProperties"])
        if "addChart" in pedido:
            aba["charts"].append({"chartId": 99, **pedido["addChart"]["chart"]})
    repetidos = pedidos_grafico(aba, CABECALHO)
    assert all(set(pedido) == {"repeatCell"} for pedido in repetidos)
    assert len(aba["charts"]) == 1


def test_reaproveita_grafico_sem_series_com_titulo_automatico():
    aba = {
        "properties": {"sheetId": 2, "gridProperties": {"columnCount": 14, "rowCount": 1003}},
        "charts": [
            {
                "chartId": 389877325,
                "spec": {
                    "title": "2026-10-04 17:57:12-03:00 and 2026-10-04 18:00:33-03:00",
                    "basicChart": {"chartType": "LINE", "headerCount": 1},
                },
                "position": {
                    "overlayPosition": {
                        "anchorCell": {"sheetId": 2, "rowIndex": 1, "columnIndex": 3},
                        "widthPixels": 600,
                        "heightPixels": 371,
                    }
                },
            }
        ],
    }
    pedidos = pedidos_grafico(aba, ["Data/Hora", "% Seções totalizadas", "% LULA (13)", "% FLAVIO BOLSONARO (22)"])
    assert not any("addChart" in pedido for pedido in pedidos)
    assert any(pedido.get("updateChartSpec", {}).get("chartId") == 389877325 for pedido in pedidos)


def test_preserva_personalizacoes_do_spec_e_fontes_existentes(aba):
    grafico = grafico_adicionado(pedidos_grafico(aba, CABECALHO))
    spec = grafico["spec"]
    spec.update(fontName="Source Code Pro", subtitle="Personalizado", maximized=True)
    basico = spec["basicChart"]
    basico["lineSmoothing"] = True
    basico["axis"][1]["viewWindowOptions"].update(viewWindowMin=0.1, viewWindowMax=0.8)
    basico["axis"][1]["format"] = {"bold": True}
    basico["domains"][0]["reversed"] = True
    basico["domains"][0]["domain"]["sourceRange"]["sources"][0]["endRowIndex"] = 100
    basico["series"][0]["lineStyle"] = {"width": 4, "type": "DASHED"}
    aba["charts"] = [{"chartId": 12, **grafico}]
    anterior = deepcopy(aba)
    pedidos = pedidos_grafico(aba, CABECALHO)
    atualizado = next(pedido["updateChartSpec"]["spec"] for pedido in pedidos if "updateChartSpec" in pedido)
    assert atualizado["subtitle"] == "Personalizado"
    assert atualizado["fontName"] == "Source Code Pro"
    assert atualizado["maximized"] is True
    assert atualizado["basicChart"]["lineSmoothing"] is True
    assert atualizado["basicChart"]["domains"] == basico["domains"]
    assert atualizado["basicChart"]["series"][0]["lineStyle"] == basico["series"][0]["lineStyle"]
    assert atualizado["basicChart"]["axis"][1]["format"] == {"bold": True}
    assert atualizado["basicChart"]["axis"][1]["viewWindowOptions"] == {
        "viewWindowMin": 0.4,
        "viewWindowMax": 0.8,
        "viewWindowMode": "EXPLICIT",
    }
    assert aba == anterior
