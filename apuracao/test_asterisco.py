from dataclasses import replace

import pytest

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_resultado
from apuracao.modelo import Contexto
from apuracao.planilha import Planilha
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada, aba


@pytest.fixture
def resultado(dados_2022):
    return Apuracao2022(Contexto(2022, 1, 546, 3, "ac")).ler(dados_2022)


def test_nome_marca_somente_finalizacao(resultado):
    assert tabela_resultado(replace(resultado, finalizada=True), "AC").nome == "AC*"
    assert tabela_resultado(replace(resultado, matematicamente_definida="e"), "AC").nome == "AC"
    assert tabela_resultado(replace(resultado, finalizada=True), "Presidente").nome == "Presidente"


def test_renomeia_sem_criar_aba_e_reusa_cache(resultado):
    remoto = PlanilhaSimulada({7: aba("AC", 40, 6, 7)})
    escritor = Planilha(ClienteSimulado(remoto), "ID", 2022, 1)
    tabela = tabela_resultado(replace(resultado, finalizada=True), "AC")
    escritor.publicar([tabela])
    escritor.publicar([tabela])
    assert len(remoto.abas) == 1
    assert remoto.abas[7]["properties"]["title"] == "AC*"
    assert not any("addSheet" in pedido for lote in remoto.lotes for pedido in lote["requests"])
    assert not any(
        pedido.get("updateSheetProperties", {}).get("fields") == "title" for pedido in remoto.lotes[-1]["requests"]
    )


def test_reiniciar_reconhece_aba_marcada_e_desmarca_se_tf_reverter(resultado):
    remoto = PlanilhaSimulada({7: aba("AC*", 40, 6, 7)})
    escritor = Planilha(ClienteSimulado(remoto), "ID", 2022, 1)
    escritor.publicar([tabela_resultado(resultado, "AC")])
    assert len(remoto.abas) == 1
    assert remoto.abas[7]["properties"]["title"] == "AC"


def test_ambiguidade_nao_apaga_nem_escolhe_aba(resultado):
    remoto = PlanilhaSimulada({7: aba("AC", 40, 6, 7), 8: aba("AC*", 40, 6, 8)})
    escritor = Planilha(ClienteSimulado(remoto), "ID", 2022, 1)
    with pytest.raises(ValueError, match="ambígu"):
        escritor.publicar([tabela_resultado(resultado, "AC")])
    assert remoto.lotes == []
