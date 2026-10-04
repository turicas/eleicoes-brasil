"""Publicação idempotente em abas de uma planilha existente, sem autenticação própria."""

import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class TabelaPlanilha:
    """Valores literais de uma aba; percentuais são frações e colunas usam índices a partir de zero."""

    nome: str
    linhas: list[list]
    colunas_percentuais: tuple[int, ...] = ()


class Planilha:
    """Atualiza apenas abas nomeadas; o cliente deve oferecer set_timeout, open_by_key e a API de lotes.

    O contexto fica em developerMetadata DOCUMENT. Escritores concorrentes exigem coordenação externa:
    a releitura protege repetições após falha transitória, não mudanças simultâneas de contexto.
    """

    CHAVE_CONTEXTO = "apuracao.contexto"
    CAMPOS_METADADOS = "sheets(properties(sheetId,title,gridProperties)),developerMetadata"

    def __init__(
        self,
        client,
        identificador: str,
        ano: int,
        turno: int,
        *,
        timeout: float = 30,
        max_tentativas: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if not isinstance(ano, int) or isinstance(ano, bool) or ano <= 0 or turno not in (1, 2):
            raise ValueError("Ano e turno inválidos.")
        if not isinstance(max_tentativas, int) or isinstance(max_tentativas, bool) or max_tentativas < 1:
            raise ValueError("O número máximo de tentativas deve ser positivo.")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("O timeout HTTP deve ser finito e positivo.")
        client.set_timeout(timeout)
        self.client = client
        self.identificador = identificador
        self.ano = ano
        self.turno = turno
        self.max_tentativas = max_tentativas
        self.sleep = sleep
        self._planilha = None

    def publicar(self, tabelas: list[TabelaPlanilha], *, titulo: str | None = None) -> None:
        """Substitui valores e limpa sobras em um lote, preservando formatos não solicitados.

        As dimensões existentes nunca encolhem. A aba inteira indicada pertence ao publicador quanto
        aos valores; abas não indicadas e seus formatos permanecem intactos. Sem tabelas, não faz I/O.
        """
        self._validar_tabelas(tabelas)
        if not tabelas:
            return
        for tentativa in range(self.max_tentativas):
            try:
                if self._planilha is None:
                    self._planilha = self.client.open_by_key(self.identificador)
                metadados = self._planilha.fetch_sheet_metadata(params={"fields": self.CAMPOS_METADADOS})
                pedidos = self._montar_pedidos(metadados, tabelas)
                if titulo is not None:
                    pedidos.append(
                        {"updateSpreadsheetProperties": {"properties": {"title": titulo}, "fields": "title"}}
                    )
                self._planilha.batch_update({"requests": pedidos})
                return
            except KeyboardInterrupt:
                raise
            except Exception as erro:
                status = getattr(getattr(erro, "response", None), "status_code", None)
                transitorio = status == 429 or (isinstance(status, int) and 500 <= status <= 599)
                if not transitorio or tentativa + 1 == self.max_tentativas:
                    raise
                self.sleep(min(2**tentativa, 30))

    @staticmethod
    def _valor(valor) -> dict:
        if valor is None:
            return {}
        if isinstance(valor, bool):
            return {"userEnteredValue": {"boolValue": valor}}
        if isinstance(valor, int):
            return {"userEnteredValue": {"numberValue": valor}}
        if isinstance(valor, float):
            if not math.isfinite(valor):
                raise ValueError("Valores numéricos devem ser finitos.")
            return {"userEnteredValue": {"numberValue": valor}}
        if isinstance(valor, str):
            return {"userEnteredValue": {"stringValue": valor}}
        raise TypeError(f"Tipo de célula não suportado: {type(valor).__name__}.")

    @classmethod
    def _validar_tabelas(cls, tabelas: list[TabelaPlanilha]) -> None:
        nomes = set()
        for tabela in tabelas:
            if not tabela.nome or tabela.nome in nomes:
                raise ValueError("Os nomes das abas devem ser únicos e não vazios.")
            nomes.add(tabela.nome)
            largura = max((len(linha) for linha in tabela.linhas), default=0)
            for coluna in tabela.colunas_percentuais:
                if not isinstance(coluna, int) or isinstance(coluna, bool) or not 0 <= coluna < largura:
                    raise ValueError("Índice de coluna percentual fora dos dados.")
            for linha in tabela.linhas:
                for valor in linha:
                    cls._valor(valor)

    def _montar_pedidos(self, metadados: dict, tabelas: list[TabelaPlanilha]) -> list[dict]:
        pedidos = []
        contexto = {"ano": self.ano, "turno": self.turno}
        registrados = [
            item
            for item in metadados.get("developerMetadata", [])
            if item.get("metadataKey") == self.CHAVE_CONTEXTO and item.get("location", {}).get("spreadsheet")
        ]
        for registro in registrados:
            try:
                contexto_registrado = json.loads(registro.get("metadataValue", ""))
            except (ValueError, TypeError) as erro:
                raise ValueError("O contexto registrado na planilha é inválido.") from erro
            if contexto_registrado != contexto:
                raise ValueError(f"A planilha pertence a outro contexto: {contexto_registrado}.")
        if not registrados:
            pedidos.append(
                {
                    "createDeveloperMetadata": {
                        "developerMetadata": {
                            "metadataKey": self.CHAVE_CONTEXTO,
                            "metadataValue": json.dumps(contexto, separators=(",", ":")),
                            "location": {"spreadsheet": True},
                            "visibility": "DOCUMENT",
                        }
                    }
                }
            )
        propriedades = [aba["properties"] for aba in metadados.get("sheets", [])]
        abas = {aba["title"]: aba for aba in propriedades}
        proximo_identificador = max((aba["sheetId"] for aba in propriedades), default=-1) + 1
        for tabela in tabelas:
            linhas = max(1, len(tabela.linhas))
            colunas = max(1, max((len(linha) for linha in tabela.linhas), default=0))
            existente = abas.get(tabela.nome)
            if existente is None:
                identificador = proximo_identificador
                proximo_identificador += 1
                pedidos.append(
                    {
                        "addSheet": {
                            "properties": {
                                "sheetId": identificador,
                                "title": tabela.nome,
                                "gridProperties": {"rowCount": linhas, "columnCount": colunas, "frozenRowCount": 1},
                            }
                        }
                    }
                )
            else:
                identificador = existente["sheetId"]
                grade = existente["gridProperties"]
                linhas = max(linhas, grade["rowCount"])
                colunas = max(colunas, grade["columnCount"])
                alteracoes = {}
                if linhas != grade["rowCount"]:
                    alteracoes["rowCount"] = linhas
                if colunas != grade["columnCount"]:
                    alteracoes["columnCount"] = colunas
                if alteracoes:
                    pedidos.append(
                        {
                            "updateSheetProperties": {
                                "properties": {"sheetId": identificador, "gridProperties": alteracoes},
                                "fields": ",".join(f"gridProperties.{campo}" for campo in alteracoes),
                            }
                        }
                    )
            pedidos.append(
                {
                    "updateCells": {
                        "range": {
                            "sheetId": identificador,
                            "startRowIndex": 0,
                            "endRowIndex": linhas,
                            "startColumnIndex": 0,
                            "endColumnIndex": colunas,
                        },
                        "rows": [{"values": [self._valor(valor) for valor in linha]} for linha in tabela.linhas],
                        "fields": "userEnteredValue",
                    }
                }
            )
            if len(tabela.linhas) > 1:
                for coluna in sorted(set(tabela.colunas_percentuais)):
                    pedidos.append(
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": identificador,
                                    "startRowIndex": 1,
                                    "endRowIndex": len(tabela.linhas),
                                    "startColumnIndex": coluna,
                                    "endColumnIndex": coluna + 1,
                                },
                                "cell": {
                                    "userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}
                                },
                                "fields": "userEnteredFormat.numberFormat",
                            }
                        }
                    )
        return pedidos
