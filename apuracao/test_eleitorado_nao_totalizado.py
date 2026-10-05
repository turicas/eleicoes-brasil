from apuracao.adaptador2026 import Apuracao2026
from apuracao.apresentacao import tabela_resultado
from apuracao.test_2026 import contexto as contexto_fixture
from apuracao.test_2026 import dados as dados_fixture

contexto = contexto_fixture
dados = dados_fixture


def test_secoes_nao_instaladas_nao_sao_pendencias(contexto, dados):
    dados["e"].update(te="200", esa="190", esnt="0", esni="10")
    resultado = Apuracao2026(contexto).ler(dados)
    linha = next(
        linha
        for linha in tabela_resultado(resultado, "Presidente").linhas
        if linha and linha[0] == "Eleitorado de seções apuradas"
    )
    assert linha[-1] == 0
    assert resultado.eleitorado.nao_totalizado == 0


def test_campo_ausente_nao_inventa_pendencia(contexto, dados):
    dados["e"].pop("esnt", None)
    resultado = Apuracao2026(contexto).ler(dados)
    linha = next(
        linha
        for linha in tabela_resultado(resultado, "Presidente").linhas
        if linha and linha[0] == "Eleitorado de seções apuradas"
    )
    assert linha[-1] is None
