"""Ajuste pontual de formato e gráfico numa planilha existente."""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .apresentacao import data_planilha
from .formatacao import pedidos_formatacao


def monta_formatacao(metadados: dict, valores: dict[str, list[list]]) -> tuple[list[dict], list[str]]:
    pedidos = []
    nomes = []
    for aba in metadados.get("sheets", []):
        propriedades = aba["properties"]
        nome = propriedades["title"]
        grade = propriedades["gridProperties"]
        pedidos.extend(
            pedidos_formatacao(propriedades["sheetId"], nome, valores[nome], grade["rowCount"], grade["columnCount"])
        )
        nomes.append(nome)
    return pedidos, nomes


def pedidos_horas(identificador: int, historico: list[list]) -> list[dict]:
    pedidos = []
    for indice, linha in enumerate(historico[1:], start=1):
        if not linha or not isinstance(linha[0], str):
            continue
        data = datetime.fromisoformat(linha[0])
        if data.tzinfo is None:
            raise ValueError(f"Timestamp sem fuso na linha {indice + 1}")
        pedidos.append(
            {
                "updateCells": {
                    "start": {"sheetId": identificador, "rowIndex": indice, "columnIndex": 0},
                    "rows": [{"values": [{"userEnteredValue": {"numberValue": data_planilha(data)}}]}],
                    "fields": "userEnteredValue",
                }
            }
        )
    return pedidos


def cria_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aplica formato sem alterar valores, ou prepara o gráfico presidencial."
    )
    parser.add_argument("planilha", metavar="ID")
    parser.add_argument("--aplicar", action="store_true", help="Envia o lote; sem esta opção apenas inspeciona")
    parser.add_argument("--grafico", action="store_true", help="Prepara apenas o gráfico Lula/Flávio na LinhaDoTempo")
    return parser


def executar(args) -> None:
    import gspread

    credenciais = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credenciais:
        raise ValueError("Defina GOOGLE_APPLICATION_CREDENTIALS")
    client = gspread.service_account(filename=credenciais, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    client.set_timeout(30)
    planilha = client.open_by_key(args.planilha)
    metadados = planilha.fetch_sheet_metadata(
        params={"fields": "properties,sheets(properties,charts),developerMetadata"}
    )
    if args.grafico:
        from .grafico import pedidos_grafico

        aba = next((aba for aba in metadados["sheets"] if aba["properties"]["title"] == "LinhaDoTempo"), None)
        if aba is None:
            raise ValueError("Aba LinhaDoTempo ausente")
        historico = planilha.values_get("'LinhaDoTempo'!A:N", params={"valueRenderOption": "UNFORMATTED_VALUE"}).get(
            "values", []
        )
        cabecalho = historico[0] if historico else []
        pedidos = pedidos_horas(aba["properties"]["sheetId"], historico) + pedidos_grafico(aba, cabecalho)
        nomes = ["LinhaDoTempo"]
    else:
        nomes = [aba["properties"]["title"] for aba in metadados["sheets"]]
        intervalos = []
        for aba in metadados["sheets"]:
            propriedades = aba["properties"]
            coluna = propriedades["gridProperties"]["columnCount"]
            letras = ""
            while coluna:
                coluna, resto = divmod(coluna - 1, 26)
                letras = chr(65 + resto) + letras
            nome = propriedades["title"].replace("'", "''")
            intervalos.append(f"'{nome}'!A:{letras}")
        respostas = planilha.values_batch_get(intervalos, params={"valueRenderOption": "UNFORMATTED_VALUE"}).get(
            "valueRanges", []
        )
        if len(respostas) != len(nomes):
            raise ValueError("Quantidade inesperada de respostas de valores")
        valores = {nome: resposta.get("values", []) for nome, resposta in zip(nomes, respostas, strict=True)}
        pedidos, nomes = monta_formatacao(metadados, valores)
    pasta = Path("data/analise-apuracao-2026")
    pasta.mkdir(parents=True, exist_ok=True)
    sufixo = "grafico" if args.grafico else "formatacao"
    (pasta / f"antes-{sufixo}.json").write_text(json.dumps(metadados, ensure_ascii=False, indent=2))
    (pasta / f"pedidos-{sufixo}.json").write_text(json.dumps({"requests": pedidos}, ensure_ascii=False, indent=2))
    if args.aplicar and pedidos:
        planilha.batch_update({"requests": pedidos})
    verbo = "Aplicado" if args.aplicar else "Planejado"
    print(f"{verbo}: {len(nomes)} abas, {len(pedidos)} pedidos em um lote: {', '.join(nomes)}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = cria_parser().parse_args(argv)
    try:
        executar(args)
    except KeyboardInterrupt:
        return 130
    except Exception as erro:  # noqa: BLE001 - fronteira de execução com diagnóstico explícito
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
