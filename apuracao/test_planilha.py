from copy import deepcopy
from types import SimpleNamespace

import pytest

from apuracao.planilha import Planilha, TabelaPlanilha


class ErroHTTP(Exception):
    def __init__(self, status):
        self.response = SimpleNamespace(status_code=status)


class PlanilhaSimulada:
    def __init__(self, abas=None, metadados=None):
        self.titulo = "Título original"
        self.abas = deepcopy(abas or {})
        self.metadados = deepcopy(metadados or [])
        self.lotes = []
        self.leituras = []
        self.falhas = []
        self.falhas_leitura = []

    def fetch_sheet_metadata(self, params):
        self.leituras.append(params)
        if self.falhas_leitura:
            raise ErroHTTP(self.falhas_leitura.pop(0))
        return {
            "sheets": [
                {"properties": deepcopy(aba["properties"]), "charts": deepcopy(aba.get("charts", []))}
                for aba in self.abas.values()
            ],
            "developerMetadata": deepcopy(self.metadados),
        }

    def batch_update(self, corpo):
        self.lotes.append(deepcopy(corpo))
        falha = self.falhas.pop(0) if self.falhas else None
        if falha and not falha[1]:
            raise ErroHTTP(falha[0])
        for pedido in corpo["requests"]:
            self.aplicar(pedido)
        if falha:
            raise ErroHTTP(falha[0])

    def aplicar(self, pedido):
        if "updateSpreadsheetProperties" in pedido:
            atualizacao = pedido["updateSpreadsheetProperties"]
            assert atualizacao["fields"] == "title"
            self.titulo = atualizacao["properties"]["title"]
        elif "addSheet" in pedido:
            propriedades = deepcopy(pedido["addSheet"]["properties"])
            assert propriedades["sheetId"] not in self.abas
            assert propriedades["title"] not in [aba["properties"]["title"] for aba in self.abas.values()]
            self.abas[propriedades["sheetId"]] = {"properties": propriedades, "valores": {}, "formatos": {}}
        elif "createDeveloperMetadata" in pedido:
            self.metadados.append(deepcopy(pedido["createDeveloperMetadata"]["developerMetadata"]))
        elif "updateSheetProperties" in pedido:
            atualizacao = pedido["updateSheetProperties"]
            propriedades = self.abas[atualizacao["properties"]["sheetId"]]["properties"]
            for campo in atualizacao["fields"].split(","):
                if campo in ("tabColorStyle", "title"):
                    propriedades[campo] = deepcopy(atualizacao["properties"][campo])
                    continue
                prefixo, chave = campo.split(".")
                assert prefixo == "gridProperties"
                assert chave in ("rowCount", "columnCount", "frozenRowCount")
                propriedades[prefixo][chave] = atualizacao["properties"][prefixo][chave]
        elif "updateCells" in pedido:
            atualizacao = pedido["updateCells"]
            assert atualizacao["fields"] == "userEnteredValue"
            intervalo = atualizacao["range"]
            aba = self.abas[intervalo["sheetId"]]
            assert intervalo["endRowIndex"] <= aba["properties"]["gridProperties"]["rowCount"]
            assert intervalo["endColumnIndex"] <= aba["properties"]["gridProperties"]["columnCount"]
            for linha in range(intervalo["startRowIndex"], intervalo["endRowIndex"]):
                for coluna in range(intervalo["startColumnIndex"], intervalo["endColumnIndex"]):
                    aba["valores"].pop((linha, coluna), None)
            for linha, dados in enumerate(atualizacao.get("rows", []), intervalo["startRowIndex"]):
                for coluna, celula in enumerate(dados.get("values", []), intervalo["startColumnIndex"]):
                    if "userEnteredValue" in celula:
                        aba["valores"][linha, coluna] = deepcopy(celula["userEnteredValue"])
        elif "repeatCell" in pedido:
            atualizacao = pedido["repeatCell"]
            intervalo = atualizacao["range"]
            aba = self.abas[intervalo["sheetId"]]
            for linha in range(intervalo["startRowIndex"], intervalo["endRowIndex"]):
                for coluna in range(intervalo["startColumnIndex"], intervalo["endColumnIndex"]):
                    formato = aba["formatos"].setdefault((linha, coluna), {})
                    for atributo, valor in atualizacao["cell"]["userEnteredFormat"].items():
                        if atributo == "textFormat":
                            formato.setdefault(atributo, {}).update(deepcopy(valor))
                        else:
                            formato[atributo] = deepcopy(valor)
        elif "updateChartSpec" in pedido:
            atualizacao = pedido["updateChartSpec"]
            for aba in self.abas.values():
                for grafico in aba.get("charts", []):
                    if grafico["chartId"] == atualizacao["chartId"]:
                        grafico["spec"] = deepcopy(atualizacao["spec"])
        elif "autoResizeDimensions" in pedido:
            intervalo = pedido["autoResizeDimensions"]["dimensions"]
            self.abas[intervalo["sheetId"]]["auto_resize"] = deepcopy(intervalo)
        elif "updateDimensionProperties" in pedido:
            atualizacao = pedido["updateDimensionProperties"]
            intervalo = atualizacao["range"]
            aba = self.abas[intervalo["sheetId"]]
            chave = "larguras" if intervalo["dimension"] == "COLUMNS" else "alturas"
            dimensoes = aba.setdefault(chave, {})
            for indice in range(intervalo["startIndex"], intervalo["endIndex"]):
                dimensoes[indice] = atualizacao["properties"]["pixelSize"]
        else:
            pytest.fail(f"Pedido inesperado: {pedido}")


class ClienteSimulado:
    def __init__(self, planilha):
        self.planilha = planilha
        self.aberturas = []
        self.timeout = None

    def set_timeout(self, timeout):
        self.timeout = timeout

    def open_by_key(self, identificador):
        self.aberturas.append(identificador)
        return self.planilha


def aba(nome, linhas=10, colunas=5, identificador=0):
    return {
        "properties": {
            "sheetId": identificador,
            "title": nome,
            "gridProperties": {"rowCount": linhas, "columnCount": colunas, "frozenRowCount": 0},
        },
        "valores": {(8, 4): {"stringValue": "Sobra"}},
        "formatos": {(0, 0): {"backgroundColor": {"red": 1}}, (8, 4): {"numberFormat": {"type": "TEXT"}}},
    }


def escritor(planilha, **opcoes):
    cliente = ClienteSimulado(planilha)
    return Planilha(cliente, "planilha-do-usuário", 2026, 1, sleep=lambda segundos: None, **opcoes), cliente


def test_planilha_vazia_cria_abas_contexto_e_valores_tipados():
    remota = PlanilhaSimulada()
    publicador, cliente = escritor(remota, timeout=12)
    publicador.publicar(
        [TabelaPlanilha("Apuração", [["Votos", "Percentual"], [123, 0.125], [None, "=IMPORTXML()"], [True]])]
    )
    assert cliente.aberturas == ["planilha-do-usuário"]
    assert cliente.timeout == 12
    assert len(remota.lotes) == 1
    criada = next(iter(remota.abas.values()))
    assert criada["properties"]["title"] == "Apuração"
    assert criada["properties"]["gridProperties"] == {"rowCount": 4, "columnCount": 2, "frozenRowCount": 1}
    assert criada["valores"][1, 0] == {"numberValue": 123}
    assert criada["valores"][1, 1] == {"numberValue": 0.125}
    assert criada["valores"][2, 1] == {"stringValue": "=IMPORTXML()"}
    assert criada["valores"][3, 0] == {"boolValue": True}
    assert (2, 0) not in criada["valores"]
    assert len(remota.metadados) == 1
    assert remota.metadados[0]["location"] == {"spreadsheet": True}
    assert "gridProperties" in remota.leituras[0]["fields"]
    assert "developerMetadata" in remota.leituras[0]["fields"]


def test_parcial_preserva_aba_alheia_formatos_e_limpa_sobras():
    remota = PlanilhaSimulada({0: aba("Apuração"), 1: aba("Anotações", identificador=1)})
    alheia = deepcopy(remota.abas[1])
    formatos = deepcopy(remota.abas[0]["formatos"])
    publicador, _ = escritor(remota)
    publicador.publicar([TabelaPlanilha("Apuração", [["Cabeçalho"], [2]]), TabelaPlanilha("Histórico", [["Hora"]])])
    assert remota.abas[1] == alheia
    assert remota.abas[0]["formatos"] == formatos
    assert remota.abas[0]["valores"] == {(0, 0): {"stringValue": "Cabeçalho"}, (1, 0): {"numberValue": 2}}
    assert remota.abas[0]["properties"]["gridProperties"]["frozenRowCount"] == 0
    pedidos = remota.lotes[0]["requests"]
    atualizacao = next(
        pedido["updateCells"]
        for pedido in pedidos
        if pedido.get("updateCells", {}).get("range", {}).get("sheetId") == 0
    )
    assert atualizacao["range"]["endRowIndex"] == 10
    assert atualizacao["range"]["endColumnIndex"] == 5


def test_republicacao_e_idempotente_sem_duplicar_abas_ou_metadados():
    remota = PlanilhaSimulada()
    publicador, _ = escritor(remota)
    tabelas = [TabelaPlanilha("Apuração", [["Candidato", "%"], ["Pessoa", 0.4]], (1,))]
    publicador.publicar(tabelas)
    estado = deepcopy((remota.abas, remota.metadados))
    publicador.publicar(tabelas)
    assert (remota.abas, remota.metadados) == estado
    assert not any(
        "addSheet" in pedido or "createDeveloperMetadata" in pedido for pedido in remota.lotes[-1]["requests"]
    )


def test_atualizacao_preserva_formatos_percentuais_manuais():
    remota = PlanilhaSimulada({0: aba("Apuração")})
    remota.abas[0]["formatos"][1, 1] = {
        "backgroundColor": {"blue": 1},
        "numberFormat": {"type": "PERCENT", "pattern": "0.0%"},
    }
    anterior = deepcopy(remota.abas[0]["formatos"])
    publicador, _ = escritor(remota)
    publicador.publicar([TabelaPlanilha("Apuração", [["Votos", "%", "Taxa"], [25, 0.25, 0.75]], (1, 2))])
    assert remota.abas[0]["formatos"] == anterior


def test_dimensoes_crescem_conforme_dados_sem_limite_fixo():
    remota = PlanilhaSimulada({0: aba("Apuração", linhas=1, colunas=1)})
    publicador, _ = escritor(remota)
    publicador.publicar([TabelaPlanilha("Apuração", [["Título"], list(range(14))] + [[1]] * 1000)])
    assert remota.abas[0]["properties"]["gridProperties"] == {"rowCount": 1002, "columnCount": 14, "frozenRowCount": 0}
    assert remota.abas[0]["valores"][1, 13] == {"numberValue": 13}


def test_tabela_vazia_limpa_valores_e_cria_grade_minima():
    remota = PlanilhaSimulada({0: aba("Apuração")})
    publicador, _ = escritor(remota)
    publicador.publicar([TabelaPlanilha("Apuração", []), TabelaPlanilha("Vazia", [])])
    assert remota.abas[0]["valores"] == {}
    criada = next(item for item in remota.abas.values() if item["properties"]["title"] == "Vazia")
    assert criada["properties"]["gridProperties"]["rowCount"] == 1
    assert criada["properties"]["gridProperties"]["columnCount"] == 1


@pytest.mark.parametrize("ano,turno", [(2022, 1), (2026, 2)])
def test_contexto_diferente_falha_antes_de_escrever(ano, turno):
    remota = PlanilhaSimulada()
    publicador, cliente = escritor(remota)
    publicador.publicar([TabelaPlanilha("Apuração", [[1]])])
    estado = deepcopy((remota.abas, remota.metadados))
    outro = Planilha(cliente, "planilha-do-usuário", ano, turno, sleep=lambda segundos: None)
    with pytest.raises(ValueError, match="contexto"):
        outro.publicar([TabelaPlanilha("Outra", [[2]])])
    assert len(remota.lotes) == 1
    assert (remota.abas, remota.metadados) == estado


@pytest.mark.parametrize("status,aplicado", [(429, False), (500, False), (503, True)])
def test_retry_rele_metadados_e_nao_duplica_criacao_com_resposta_perdida(status, aplicado):
    remota = PlanilhaSimulada()
    remota.falhas = [(status, aplicado)]
    esperas = []
    cliente = ClienteSimulado(remota)
    publicador = Planilha(cliente, "id", 2026, 1, sleep=esperas.append)
    publicador.publicar([TabelaPlanilha("Apuração", [["Valor"], [123]])])
    assert len(remota.leituras) == 2
    assert len(remota.lotes) == 2
    assert len(remota.abas) == len(remota.metadados) == 1
    assert len(esperas) == 1
    if aplicado:
        assert not any(
            "addSheet" in pedido or "createDeveloperMetadata" in pedido for pedido in remota.lotes[1]["requests"]
        )


def test_retry_limitado_com_backoff_e_erros_permanentes_sem_retry():
    remota = PlanilhaSimulada()
    remota.falhas = [(503, False)] * 5
    esperas = []
    publicador = Planilha(ClienteSimulado(remota), "id", 2026, 1, max_tentativas=3, sleep=esperas.append)
    with pytest.raises(ErroHTTP):
        publicador.publicar([TabelaPlanilha("Apuração", [[1]])])
    assert len(remota.lotes) == 3
    assert esperas == [1, 2]
    remota.falhas = [(403, False)]
    with pytest.raises(ErroHTTP):
        publicador.publicar([TabelaPlanilha("Apuração", [[1]])])
    assert len(remota.lotes) == 4
    assert esperas == [1, 2]


def test_retry_de_leitura_tambem_limitado():
    remota = PlanilhaSimulada()
    remota.falhas_leitura = [502]
    publicador, _ = escritor(remota)
    publicador.publicar([TabelaPlanilha("Apuração", [[1]])])
    assert len(remota.leituras) == 2
    assert len(remota.lotes) == 1


@pytest.mark.parametrize(
    "tabelas",
    [
        [TabelaPlanilha("Repetida", []), TabelaPlanilha("Repetida", [])],
        [TabelaPlanilha("", [])],
        [TabelaPlanilha("Apuração", [[1]], (-1,))],
        [TabelaPlanilha("Apuração", [[1]], (1,))],
        [TabelaPlanilha("Apuração", [[float("nan")]])],
        [TabelaPlanilha("Apuração", [[object()]])],
    ],
)
def test_dados_invalidos_falham_antes_de_escrever(tabelas):
    remota = PlanilhaSimulada()
    publicador, _ = escritor(remota)
    with pytest.raises((ValueError, TypeError)):
        publicador.publicar(tabelas)
    assert remota.lotes == []
