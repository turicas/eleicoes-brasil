from apuracao.formatacao import pedidos_formatacao


def linhas(candidatos=2):
    return (
        [["candidato", "vice", "numero", "votos_apurados", "perc", "dif. próx."]]
        + [["Pessoa", "Vice", "13", 1000, 0.5, 100] for _ in range(candidatos)]
        + [
            [],
            ["Atualização do TSE", "hora"],
            ["Eleição", 6259, "Turno", 1],
            ["Eleitorado de seções apuradas", 1000, "Eleitorado total", 2000],
            ["Seções totalizadas", 5, "Seções totais", 10],
            ["Votos válidos", 1000],
        ]
    )


def celulas(pedidos):
    formatos = {}
    for pedido in pedidos:
        if "repeatCell" not in pedido:
            continue
        atualizacao = pedido["repeatCell"]
        intervalo = atualizacao["range"]
        for linha in range(intervalo["startRowIndex"], intervalo["endRowIndex"]):
            for coluna in range(intervalo["startColumnIndex"], intervalo["endColumnIndex"]):
                formato = formatos.setdefault((linha, coluna), {})
                for campo, valor in atualizacao["cell"]["userEnteredFormat"].items():
                    if campo == "textFormat":
                        formato.setdefault(campo, {}).update(valor)
                    else:
                        formato[campo] = valor
    return formatos


def test_formatacao_por_semantica_com_fundo_cinza():
    pedidos = pedidos_formatacao(28, "SP", linhas(), 20, 6)
    assert all(
        not {"updateCells", "updateSpreadsheetProperties", "deleteSheet"}.intersection(pedido) for pedido in pedidos
    )
    formatos = celulas(pedidos)
    assert formatos[0, 0]["textFormat"]["bold"] is True
    assert formatos[1, 3]["numberFormat"] == {"type": "NUMBER", "pattern": "#,##0"}
    assert formatos[1, 5]["numberFormat"]["pattern"] == "#,##0"
    assert formatos[1, 4]["numberFormat"] == {"type": "PERCENT", "pattern": "0.00%"}
    assert formatos[5, 1]["numberFormat"]["pattern"] == "0"
    assert formatos[6, 0]["backgroundColorStyle"]["rgbColor"]["red"] == 239 / 255
    assert formatos[6, 1]["numberFormat"]["pattern"] == "#,##0"
    assert formatos[6, 2]["textFormat"]["bold"] is True
    assert formatos[6, 3]["numberFormat"]["pattern"] == "#,##0"
    assert formatos[7, 0]["backgroundColorStyle"] == formatos[6, 0]["backgroundColorStyle"]
    assert formatos[8, 1]["numberFormat"]["pattern"] == "#,##0"
    assert formatos[8, 4]["numberFormat"]["type"] != "PERCENT"


def test_mudar_candidatos_remove_formato_antigo():
    formatos = celulas(pedidos_formatacao(28, "SP", linhas(5), 24, 6))
    assert formatos[6, 0]["textFormat"]["bold"] is False
    assert formatos[6, 0]["backgroundColorStyle"]["rgbColor"] == {"red": 1, "green": 1, "blue": 1}
    assert formatos[9, 0]["backgroundColorStyle"]["rgbColor"]["red"] == 239 / 255


def test_fonte_e_auto_resize_em_todas_as_abas():
    for nome, valores in (
        ("SP", linhas()),
        ("Presidente", linhas()),
        ("LinhaDoTempo", [["Data/Hora"]]),
        ("Notas", [["Oi"]]),
    ):
        pedidos = pedidos_formatacao(1, nome, valores, 20, 30)
        formatos = celulas(pedidos)
        assert formatos[19, 29]["textFormat"]["fontFamily"] == "Source Code Pro"
        assert formatos[19, 29]["textFormat"]["fontSize"] == 10
        assert pedidos[-1] == {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": 1,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 30,
                }
            }
        }
        assert not any(
            pedido.get("updateDimensionProperties", {}).get("range", {}).get("dimension") == "COLUMNS"
            for pedido in pedidos
        )


def test_aba_alheia_recebe_apenas_fonte_e_auto_resize():
    pedidos = pedidos_formatacao(5, "Anotações", [["Oi"]], 10, 8)
    assert len(pedidos) == 2
    assert (
        pedidos[0]["repeatCell"]["fields"]
        == "userEnteredFormat.textFormat.fontFamily,userEnteredFormat.textFormat.fontSize"
    )
    assert celulas(pedidos)[0, 0] == {"textFormat": {"fontFamily": "Source Code Pro", "fontSize": 10}}


def test_historico_formata_serial_com_hora_e_colunas_percentuais():
    valores = [["Data/Hora", "% Seções totalizadas", "% Lula (13)", "Outro"], [46300.75, 0.5, 0.45, 7]]
    formatos = celulas(pedidos_formatacao(6, "LinhaDoTempo", valores, 20, 8))
    assert formatos[1, 0]["numberFormat"] == {"type": "DATE_TIME", "pattern": "HH:mm:ss"}
    assert formatos[1, 1]["numberFormat"] == {"type": "PERCENT", "pattern": "0.00%"}
    assert formatos[19, 2]["numberFormat"]["type"] == "PERCENT"
    assert "numberFormat" not in formatos[1, 3]


def test_progresso_em_f_na_linha_semantica_de_secoes():
    for rotulo in ("Seções totalizadas", "Seções apuradas"):
        valores = linhas()
        valores[7] = [rotulo, 5, "Seções totais", 10, "Progresso", 0.5]
        formatos = celulas(pedidos_formatacao(1, "Presidente", valores, 20, 6))
        assert formatos[7, 5]["numberFormat"] == {"type": "PERCENT", "pattern": "0.00%"}
        assert formatos[7, 0]["backgroundColorStyle"]["rgbColor"]["red"] == 239 / 255


def test_sem_candidatos_nao_formata_percentual_resumo():
    formatos = celulas(pedidos_formatacao(1, "SP", linhas(0), 12, 6))
    assert all(formato.get("numberFormat", {}).get("type") != "PERCENT" for formato in formatos.values())
