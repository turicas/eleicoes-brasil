from copy import deepcopy

import pytest

from apuracao.planilha import TabelaPlanilha
from apuracao.test_planilha import ErroHTTP, PlanilhaSimulada, aba, escritor


def redimensionamentos(lote):
    return [
        pedido["autoResizeDimensions"]["dimensions"] for pedido in lote["requests"] if "autoResizeDimensions" in pedido
    ]


def dimensoes(identificador, colunas):
    return {"sheetId": identificador, "dimension": "COLUMNS", "startIndex": 0, "endIndex": colunas}


def test_ajusta_todas_as_abas_a_cada_dez_publicacoes_sem_reformatar():
    remota = PlanilhaSimulada({0: aba("Apuração"), 1: aba("Anotações", identificador=1, colunas=3)})
    publicador, cliente = escritor(remota)
    tabelas = [TabelaPlanilha("Apuração", [["Votos", "%"], [10, 0.5]], (1,))]
    formatos = {identificador: deepcopy(dados["formatos"]) for identificador, dados in remota.abas.items()}
    for numero in range(1, 21):
        publicador.publicar(tabelas)
        esperados = [dimensoes(0, 5), dimensoes(1, 3)] if numero in (10, 20) else []
        assert redimensionamentos(remota.lotes[-1]) == esperados
        assert len(remota.lotes) == numero
        assert not any(
            "repeatCell" in pedido or "updateDimensionProperties" in pedido for pedido in remota.lotes[-1]["requests"]
        )
    assert len(remota.leituras) == 3
    assert cliente.aberturas == ["planilha-do-usuário"]
    assert {identificador: dados["formatos"] for identificador, dados in remota.abas.items()} == formatos


def test_rele_metadados_no_decimo_lote_e_usa_dimensoes_apos_expansao_e_criacao():
    remota = PlanilhaSimulada({0: aba("Apuração"), 1: aba("Anotações", identificador=1)})
    publicador, _ = escritor(remota)
    for _ in range(9):
        publicador.publicar([TabelaPlanilha("Apuração", [[1]])])
    remota.abas[0]["properties"]["gridProperties"]["columnCount"] = 8
    remota.abas[1]["properties"]["gridProperties"]["columnCount"] = 12
    remota.abas[7] = aba("Manual", identificador=7, colunas=9)
    alheias = {identificador: deepcopy(remota.abas[identificador]) for identificador in (1, 7)}
    publicador.publicar([TabelaPlanilha("Apuração", [[1] * 11]), TabelaPlanilha("Nova", [["A", "B", "C"]])])
    pedidos = remota.lotes[-1]["requests"]
    assert redimensionamentos(remota.lotes[-1]) == [
        dimensoes(0, 11),
        dimensoes(1, 12),
        dimensoes(7, 9),
        dimensoes(8, 3),
    ]
    assert all("autoResizeDimensions" in pedido for pedido in pedidos[-4:])
    assert len(remota.leituras) == 2
    assert len(remota.lotes) == 10
    for identificador, anterior in alheias.items():
        assert remota.abas[identificador]["valores"] == anterior["valores"]
        assert remota.abas[identificador]["formatos"] == anterior["formatos"]
    assert not any(pedido.get("repeatCell", {}).get("range", {}).get("sheetId") in (0, 1, 7) for pedido in pedidos)


def test_criacao_preserva_ajuste_inicial_fora_do_intervalo():
    remota = PlanilhaSimulada()
    publicador, _ = escritor(remota)
    publicador.publicar([TabelaPlanilha("Nova", [["A", "B"]])])
    assert redimensionamentos(remota.lotes[-1]) == [dimensoes(0, 2)]
    publicador.publicar([TabelaPlanilha("Nova", [[1, 2]])])
    assert redimensionamentos(remota.lotes[-1]) == []


@pytest.mark.parametrize("intervalo", [0, -1, True, False, 1.5, "10", None])
def test_intervalo_invalido_nao_abre_planilha(intervalo):
    remota = PlanilhaSimulada()
    with pytest.raises(ValueError, match="positivo"):
        escritor(remota, ajuste_colunas_a_cada=intervalo)
    assert remota.leituras == remota.lotes == []


def test_intervalo_configuravel_e_publicacao_vazia_nao_conta():
    remota = PlanilhaSimulada({0: aba("Apuração")})
    publicador, _ = escritor(remota, ajuste_colunas_a_cada=2)
    publicador.publicar([], titulo="Não publica")
    assert remota.leituras == remota.lotes == []
    publicador.publicar([TabelaPlanilha("Apuração", [[1]])])
    for _ in range(10):
        publicador.publicar([])
    assert redimensionamentos(remota.lotes[-1]) == []
    publicador.publicar([TabelaPlanilha("Apuração", [[2]])])
    assert redimensionamentos(remota.lotes[-1]) == [dimensoes(0, 5)]


@pytest.mark.parametrize("aplicada", [False, True])
def test_tentativas_transitorias_nao_adiantam_ajuste(aplicada):
    remota = PlanilhaSimulada({0: aba("Apuração")})
    publicador, _ = escritor(remota)
    tabelas = [TabelaPlanilha("Apuração", [[1]])]
    for _ in range(8):
        publicador.publicar(tabelas)
    remota.falhas = [(503, aplicada)]
    publicador.publicar(tabelas)
    assert all(redimensionamentos(lote) == [] for lote in remota.lotes)
    publicador.publicar(tabelas)
    assert redimensionamentos(remota.lotes[-1]) == [dimensoes(0, 5)]
    publicador.publicar(tabelas)
    assert redimensionamentos(remota.lotes[-1]) == []


@pytest.mark.parametrize("status", [400, 503])
def test_publicacao_sem_sucesso_nao_avanca_contador(status):
    remota = PlanilhaSimulada({0: aba("Apuração")})
    publicador, _ = escritor(remota, max_tentativas=1)
    tabelas = [TabelaPlanilha("Apuração", [[1]])]
    for _ in range(9):
        publicador.publicar(tabelas)
    remota.falhas = [(status, False)]
    with pytest.raises(ErroHTTP):
        publicador.publicar(tabelas)
    assert redimensionamentos(remota.lotes[-1]) == [dimensoes(0, 5)]
    publicador.publicar(tabelas)
    assert redimensionamentos(remota.lotes[-1]) == [dimensoes(0, 5)]
    publicador.publicar(tabelas)
    assert redimensionamentos(remota.lotes[-1]) == []


def test_retentativa_do_decimo_lote_rele_todas_as_abas():
    remota = PlanilhaSimulada({0: aba("Apuração")})
    publicador, _ = escritor(remota)
    tabelas = [TabelaPlanilha("Apuração", [[1]])]
    for _ in range(9):
        publicador.publicar(tabelas)

    def aguardar(segundos):
        remota.abas[4] = aba("Manual", identificador=4, colunas=7)

    publicador.sleep = aguardar
    remota.falhas = [(429, False)]
    publicador.publicar(tabelas)
    assert redimensionamentos(remota.lotes[-2]) == [dimensoes(0, 5)]
    assert redimensionamentos(remota.lotes[-1]) == [dimensoes(0, 5), dimensoes(4, 7)]
    assert len(remota.leituras) == 3
    publicador.publicar(tabelas)
    assert redimensionamentos(remota.lotes[-1]) == []
