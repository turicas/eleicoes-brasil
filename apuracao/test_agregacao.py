from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from .agregacao import somar_presidente
from .formatacao import UFS
from .modelo import Candidato, Contexto, Eleitorado, Resultado, Secoes, Votos


@pytest.fixture
def resultados():
    instante = datetime(2026, 10, 4, 18, tzinfo=timezone(timedelta(hours=-3)))
    return [
        Resultado(
            contexto=Contexto(2026, 1, 619, 1, abrangencia),
            gerada_em=instante + timedelta(seconds=indice),
            secoes=Secoes(10, 6, 5, Decimal("0.99"), Decimal("0.99")),
            eleitorado=Eleitorado(100, 60),
            votos=Votos(60, 50, 6, 4, 40, 7, 3),
            candidatos=(
                Candidato("13", "Pessoa A", "A", "Vice A", 30, Decimal("0.01"), "100", "PA", "válido", "eleito"),
                Candidato("22", "Pessoa B", "B", "Vice B", 10, Decimal("0.99"), "200", "PB", "válido", "não eleito"),
            ),
            geracao=str(indice),
            totalizada_em=instante,
            andamento="f",
            finalizada=True,
            matematicamente_definida="s",
        )
        for indice, abrangencia in enumerate(sorted({uf.lower() for uf in UFS} | {"zz"}))
    ]


def test_soma_inclui_exterior_e_recalcula_percentuais(resultados):
    resultados[-1] = replace(
        resultados[-1],
        secoes=Secoes(20, 10, 8),
        eleitorado=Eleitorado(200, 100),
        votos=Votos(120, 100, 12, 8, 80, 14, 6),
        candidatos=tuple(replace(candidato, votos=candidato.votos * 2) for candidato in resultados[-1].candidatos),
    )
    agregado = somar_presidente(resultados)
    assert agregado.contexto == Contexto(2026, 1, 619, 1, "br")
    assert agregado.secoes == Secoes(290, 172, 143, Decimal(143) / 290, Decimal(172) / 290)
    assert agregado.eleitorado == Eleitorado(2900, 1720)
    assert agregado.votos == Votos(1740, 1450, 174, 116, 1160, 203, 87)
    assert [candidato.votos for candidato in agregado.candidatos] == [870, 290]
    assert [candidato.percentual for candidato in agregado.candidatos] == [Decimal("0.75"), Decimal("0.25")]
    assert agregado.candidatos[0].nome == "Pessoa A"
    assert agregado.candidatos[0].nome_urna == "A"
    assert agregado.candidatos[0].vice == "Vice A"
    assert agregado.candidatos[0].partido == "PA"
    assert all(candidato.situacao is None for candidato in agregado.candidatos)
    assert agregado.finalizada is None
    assert agregado.matematicamente_definida is None
    assert agregado.totalizada_em is None
    assert agregado.andamento == "f"


def test_proveniencia_tempos_e_geracao_independem_da_ordem(resultados):
    agregado = somar_presidente(resultados)
    assert agregado.origem == "soma-ufs"
    assert agregado.fontes_desde == min(resultado.gerada_em for resultado in resultados)
    assert agregado.fontes_ate == max(resultado.gerada_em for resultado in resultados)
    assert agregado.gerada_em == agregado.fontes_ate
    assert agregado.geracao.startswith("ufs-")
    assert len(agregado.geracao) == 68
    assert somar_presidente(list(reversed(resultados))) == agregado
    resultados[0] = replace(resultados[0], geracao="nova geração")
    assert somar_presidente(resultados).geracao != agregado.geracao
    geracao_alterada = somar_presidente(resultados).geracao
    resultados[0] = replace(resultados[0], gerada_em=resultados[0].gerada_em + timedelta(seconds=1))
    assert somar_presidente(resultados).geracao != geracao_alterada
    assert somar_presidente(resultados).gerada_em == agregado.gerada_em


@pytest.mark.parametrize("turno", [1, 2])
def test_aceita_turnos_e_identidade_por_numero(resultados, turno):
    resultados = [
        replace(
            resultado,
            contexto=replace(resultado.contexto, turno=turno),
            candidatos=tuple(replace(candidato, sequencial=None) for candidato in resultado.candidatos),
        )
        for resultado in resultados
    ]
    agregado = somar_presidente(resultados)
    assert agregado.contexto.turno == turno
    assert [candidato.sequencial for candidato in agregado.candidatos] == [None, None]
    assert [candidato.votos for candidato in agregado.candidatos] == [840, 280]


@pytest.mark.parametrize("campo,valor", [("ano", 2022), ("turno", 3), ("cargo", 3), ("eleicao", 620)])
def test_rejeita_contextos_incompativeis(resultados, campo, valor):
    resultados[0] = replace(resultados[0], contexto=replace(resultados[0].contexto, **{campo: valor}))
    with pytest.raises(ValueError, match=campo):
        somar_presidente(resultados)


@pytest.mark.parametrize("abrangencia", ["br", "xx", "AC", "zz"])
def test_rejeita_abrangencias_invalidas_e_repetidas(resultados, abrangencia):
    resultados[0] = replace(resultados[0], contexto=replace(resultados[0].contexto, abrangencia=abrangencia))
    with pytest.raises(ValueError, match="abrang"):
        somar_presidente(resultados)


@pytest.mark.parametrize("ausente", ["zz", "sp"])
def test_nao_reaproveita_soma_quando_falta_fonte(resultados, ausente):
    somar_presidente(resultados)
    incompletos = [resultado for resultado in resultados if resultado.contexto.abrangencia != ausente]
    with pytest.raises(ValueError, match="abrang"):
        somar_presidente(incompletos)


def test_rejeita_lista_vazia():
    with pytest.raises(ValueError, match="abrang"):
        somar_presidente([])


@pytest.mark.parametrize("alteracao", ["ausente", "extra", "duplicado", "sequencial"])
def test_exige_mesmo_conjunto_de_candidatos(resultados, alteracao):
    candidatos = resultados[0].candidatos
    if alteracao == "ausente":
        candidatos = candidatos[:1]
    elif alteracao == "extra":
        candidatos += (replace(candidatos[0], sequencial="300", numero="33"),)
    elif alteracao == "duplicado":
        candidatos += (candidatos[0],)
    else:
        candidatos = (replace(candidatos[0], sequencial="300"), candidatos[1])
    resultados[0] = replace(resultados[0], candidatos=candidatos)
    with pytest.raises(ValueError, match="candidato"):
        somar_presidente(resultados)


@pytest.mark.parametrize("campo", ["numero", "nome", "nome_urna", "vice", "partido"])
def test_rejeita_metadados_inconsistentes_do_candidato(resultados, campo):
    candidatos = resultados[0].candidatos
    resultados[0] = replace(resultados[0], candidatos=(replace(candidatos[0], **{campo: "divergente"}), candidatos[1]))
    with pytest.raises(ValueError, match=campo):
        somar_presidente(resultados)


def test_ordem_dos_candidatos_nao_altera_soma(resultados):
    esperado = somar_presidente(resultados)
    resultados[0] = replace(resultados[0], candidatos=tuple(reversed(resultados[0].candidatos)))
    assert somar_presidente(resultados) == esperado


def test_metadados_opcionais_e_destinacao_conservadores(resultados):
    candidatos = resultados[0].candidatos
    resultados[0] = replace(
        resultados[0], candidatos=(replace(candidatos[0], vice=None, partido=None, destinacao="anulado"), candidatos[1])
    )
    candidato = somar_presidente(resultados).candidatos[0]
    assert candidato.vice == "Vice A"
    assert candidato.partido == "PA"
    assert candidato.destinacao is None


@pytest.mark.parametrize("campo", ["concorrentes", "anulados", "anulados_sub_judice"])
def test_votos_opcionais_incompletos_nao_viram_zero(resultados, campo):
    resultados[0] = replace(resultados[0], votos=replace(resultados[0].votos, **{campo: None}))
    agregado = somar_presidente(resultados)
    assert getattr(agregado.votos, campo) is None
    if campo == "concorrentes":
        assert all(candidato.percentual is None for candidato in agregado.candidatos)


def test_totalizadas_ausentes_nao_viram_zero(resultados):
    resultados[0] = replace(resultados[0], secoes=replace(resultados[0].secoes, totalizadas=None))
    agregado = somar_presidente(resultados)
    assert agregado.secoes.totalizadas is None
    assert agregado.secoes.percentual_totalizadas is None
    assert agregado.secoes.apuradas == 168


def test_denominadores_zerados(resultados):
    resultados = [
        replace(
            resultado,
            secoes=Secoes(0, 0, 0),
            votos=Votos(0, 0, 0, 0, 0),
            candidatos=tuple(replace(candidato, votos=0) for candidato in resultado.candidatos),
        )
        for resultado in resultados
    ]
    agregado = somar_presidente(resultados)
    assert agregado.secoes.percentual_apuradas is None
    assert agregado.secoes.percentual_totalizadas is None
    assert all(candidato.percentual is None for candidato in agregado.candidatos)


@pytest.mark.parametrize(
    "estados,esperado",
    [(["f"] * 28, "f"), (["n"] * 28, "n"), (["n"] * 27 + ["f"], "p"), (["p"] * 28, "p"), ([None] * 28, "n")],
)
def test_andamento_conservador(resultados, estados, esperado):
    resultados = [replace(resultado, andamento=estado) for resultado, estado in zip(resultados, estados, strict=True)]
    assert somar_presidente(resultados).andamento == esperado


def test_divulgacao_so_quando_todas_fontes_liberam(resultados):
    assert somar_presidente(resultados).divulgacao_liberada is True
    resultados[0] = replace(resultados[0], divulgacao_liberada=False)
    assert somar_presidente(resultados).divulgacao_liberada is False


def test_rejeita_fontes_que_ja_sao_agregacoes(resultados):
    resultados[0] = replace(resultados[0], origem="soma-ufs")
    with pytest.raises(ValueError, match="origem"):
        somar_presidente(resultados)
