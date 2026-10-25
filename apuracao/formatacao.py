"""Padrão visual semântico das abas de resultado, independente do ano e das linhas do resumo."""

UFS = frozenset(
    [
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
    ]
)
_QUANTIDADES = frozenset(
    (
        "Eleitorado de seções apuradas",
        "Eleitorado total",
        "Eleitorado que falta apurar",
        "Seções totalizadas",
        "Seções totais",
        "Seções apuradas",
        "Votos válidos",
        "Votos nulos",
        "Votos brancos",
        "Votos anulados",
        "Votos anulados sub judice",
        "Votos a concorrentes",
        "Total de votos",
    )
)
_CINZA = {"red": 239 / 255, "green": 239 / 255, "blue": 239 / 255}
_BRANCO = {"red": 1, "green": 1, "blue": 1}


def nome_canonico(nome: str) -> str:
    return nome[:-1] if nome.endswith("*") and nome[:-1] in UFS else nome


def pedidos_formatacao(
    identificador: int, nome: str, linhas: list[list], total_linhas: int, total_colunas: int
) -> list[dict]:
    """Altera apenas atributos visuais administrados, removendo resíduos quando o resumo muda de posição."""
    nome = nome_canonico(nome)
    pedidos = []

    def formato(inicio: int, fim: int, coluna: int, limite: int, atributos: dict, campos: str):
        if inicio >= fim:
            return
        pedidos.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": identificador,
                        "startRowIndex": inicio,
                        "endRowIndex": fim,
                        "startColumnIndex": coluna,
                        "endColumnIndex": limite,
                    },
                    "cell": {"userEnteredFormat": atributos},
                    "fields": campos,
                }
            }
        )

    fonte = {"textFormat": {"fontFamily": "Source Code Pro", "fontSize": 10}}
    formato(
        0,
        total_linhas,
        0,
        total_colunas,
        fonte,
        "userEnteredFormat.textFormat.fontFamily,userEnteredFormat.textFormat.fontSize",
    )
    auto_resize = {
        "autoResizeDimensions": {
            "dimensions": {"sheetId": identificador, "dimension": "COLUMNS", "startIndex": 0, "endIndex": total_colunas}
        }
    }
    if nome == "LEIA-ME":
        formato(0, total_linhas, 0, 1, {"textFormat": {"bold": True}}, "userEnteredFormat.textFormat.bold")
        formato(
            0,
            total_linhas,
            1,
            2,
            {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"},
            "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment",
        )
        pedidos.extend(
            [
                {
                    "updateDimensionProperties": {
                        "range": {"sheetId": identificador, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                        "properties": {"pixelSize": 800},
                        "fields": "pixelSize",
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {"sheetId": identificador, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": identificador,
                            "dimension": "ROWS",
                            "startIndex": 0,
                            "endIndex": total_linhas,
                        }
                    }
                },
            ]
        )
        return pedidos
    if nome == "PresidentePorUF":
        formato(
            0,
            1,
            0,
            total_colunas,
            {"textFormat": {"bold": True}, "wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE"},
            "userEnteredFormat.textFormat.bold,userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment",
        )
        pedidos.append(
            {
                "autoResizeDimensions": {
                    "dimensions": {"sheetId": identificador, "dimension": "ROWS", "startIndex": 0, "endIndex": 1}
                }
            }
        )
        formato(
            1,
            total_linhas,
            2,
            total_colunas,
            {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}},
            "userEnteredFormat.numberFormat",
        )
        for coluna in (4, 7, 8, 9, 13, 15, 17):
            formato(
                1,
                total_linhas,
                coluna,
                coluna + 1,
                {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}},
                "userEnteredFormat.numberFormat",
            )
        return pedidos + [auto_resize]
    if nome == "LinhaDoTempo":
        formato(
            1,
            total_linhas,
            0,
            1,
            {"numberFormat": {"type": "DATE_TIME", "pattern": "HH:mm:ss"}},
            "userEnteredFormat.numberFormat",
        )
        for coluna, rotulo in enumerate(linhas[0] if linhas else []):
            if isinstance(rotulo, str) and rotulo.strip().startswith("%"):
                formato(
                    1,
                    total_linhas,
                    coluna,
                    coluna + 1,
                    {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}},
                    "userEnteredFormat.numberFormat",
                )
        return pedidos + [auto_resize]
    if nome != "Presidente" and nome not in UFS:
        return pedidos + [auto_resize]
    if not linhas or linhas[0][:6] != ["candidato", "vice", "numero", "votos_apurados", "perc", "dif. próx."]:
        raise ValueError(f"Cabeçalho de resultado incompatível na aba {nome}")
    if total_colunas < 6 or total_linhas < len(linhas):
        raise ValueError(f"Dimensões insuficientes na aba {nome}")

    formato(
        0,
        total_linhas,
        0,
        6,
        {
            "textFormat": {"bold": False},
            "backgroundColorStyle": {"rgbColor": _BRANCO},
            "horizontalAlignment": "LEFT",
            "numberFormat": {"type": "NUMBER", "pattern": "0"},
        },
        "userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColorStyle,"
        "userEnteredFormat.horizontalAlignment,userEnteredFormat.numberFormat",
    )
    formato(0, 1, 0, 6, {"textFormat": {"bold": True}}, "userEnteredFormat.textFormat.bold")
    try:
        fim_candidatos = next(indice for indice, linha in enumerate(linhas[1:], start=1) if not linha)
    except StopIteration:
        raise ValueError(f"Separador do resumo ausente na aba {nome}") from None
    for coluna in (3, 5):
        formato(
            1,
            fim_candidatos,
            coluna,
            coluna + 1,
            {
                "numberFormat": {"type": "NUMBER", "pattern": "#,##0"},
                "horizontalAlignment": "RIGHT",
            },
            "userEnteredFormat.numberFormat,userEnteredFormat.horizontalAlignment",
        )
    formato(
        1,
        fim_candidatos,
        4,
        5,
        {
            "numberFormat": {"type": "PERCENT", "pattern": "0.00%"},
            "horizontalAlignment": "RIGHT",
        },
        "userEnteredFormat.numberFormat,userEnteredFormat.horizontalAlignment",
    )
    for indice in range(fim_candidatos + 1, len(linhas)):
        linha = linhas[indice]
        if not linha:
            continue
        for coluna in (0, 2, 4):
            if len(linha) <= coluna or not isinstance(linha[coluna], str) or not linha[coluna]:
                continue
            formato(
                indice,
                indice + 1,
                coluna,
                coluna + 1,
                {"textFormat": {"bold": True}},
                "userEnteredFormat.textFormat.bold",
            )
            if len(linha) > coluna + 1:
                atributos = {"horizontalAlignment": "RIGHT"}
                if linha[coluna] in _QUANTIDADES:
                    atributos["numberFormat"] = {"type": "NUMBER", "pattern": "#,##0"}
                formato(
                    indice,
                    indice + 1,
                    coluna + 1,
                    coluna + 2,
                    atributos,
                    ",".join(f"userEnteredFormat.{campo}" for campo in atributos),
                )
        if linha[0] in ("Eleitorado de seções apuradas", "Seções totalizadas", "Seções apuradas"):
            formato(
                indice,
                indice + 1,
                0,
                4,
                {"backgroundColorStyle": {"rgbColor": _CINZA}},
                "userEnteredFormat.backgroundColorStyle",
            )
        if linha[0] in ("Seções totalizadas", "Seções apuradas") and len(linha) > 5:
            formato(
                indice,
                indice + 1,
                5,
                6,
                {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}, "horizontalAlignment": "RIGHT"},
                "userEnteredFormat.numberFormat,userEnteredFormat.horizontalAlignment",
            )
    pedidos.append(
        {
            "updateDimensionProperties": {
                "range": {"sheetId": identificador, "dimension": "ROWS", "startIndex": 0, "endIndex": total_linhas},
                "properties": {"pixelSize": 21},
                "fields": "pixelSize",
            }
        }
    )
    pedidos.append(
        {
            "updateSheetProperties": {
                "properties": {"sheetId": identificador, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        }
    )
    return pedidos + [auto_resize]
