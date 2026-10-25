from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from apuracao.apresentacao import tabela_presidente_por_uf
from apuracao.formatacao import UFS, pedidos_formatacao
from apuracao.modelo import Candidato, Contexto, Eleitorado, Resultado, Secoes, Votos


@pytest.fixture
def resultado():
    return Resultado(
        contexto=Contexto(2026, 2, 6258, 1, "sp"),
        gerada_em=datetime(2026, 10, 25, 17, tzinfo=timezone.utc),
        secoes=Secoes(100, 40, 50, Decimal("0.5"), Decimal("0.4")),
        eleitorado=Eleitorado(2000, 800, instalado=800, abstencoes=200),
        votos=Votos(600, 500, 50, 50),
        candidatos=(
            Candidato("22", "Candidato B", "Candidato B", None, 200, Decimal("0.4")),
            Candidato("13", "Candidato A", "Candidato A", None, 300, Decimal("0.6")),
        ),
        geracao="uma-geracao",
    )


def test_colunas_contagens_e_percentuais_tipados(resultado):
    tabela = tabela_presidente_por_uf([resultado])
    assert tabela.nome == "PresidentePorUF"
    assert tabela.linhas[0] == [
        "Região",
        "UF",
        "Urnas\nApuradas",
        "Urnas\nTotais",
        "Urnas\nApuradas %",
        "Eleitorado\nApurado",
        "Eleitorado\nTotal",
        "Eleitorado\nApurado %",
        "% LULA",
        "% FLÁVIO",
        "Votos\nLULA",
        "Votos\nFLÁVIO",
        "Abstenção\nTotal",
        "Abstenção\n%",
        "Votos\nNulos",
        "Votos\nNulos %",
        "Votos\nBrancos",
        "Votos\nBrancos %",
    ]
    assert tabela.linhas[1] == [
        "Sudeste",
        "SP",
        40,
        100,
        0.4,
        800,
        2000,
        0.4,
        0.6,
        0.4,
        300,
        200,
        200,
        0.25,
        50,
        50 / 600,
        50,
        50 / 600,
    ]
    assert tabela.colunas_percentuais == (4, 7, 8, 9, 13, 15, 17)


def test_ordena_regiao_e_sigla_incluindo_exterior(resultado):
    resultados = [
        replace(resultado, contexto=replace(resultado.contexto, abrangencia=uf.lower())) for uf in UFS | {"ZZ"}
    ]
    tabela = tabela_presidente_por_uf(list(reversed(resultados)))
    chaves = [(linha[0], linha[1]) for linha in tabela.linhas[1:]]
    assert len(chaves) == 28
    assert chaves == sorted(chaves)
    assert ("Exterior", "ZZ") in chaves
    assert [uf for regiao, uf in chaves if regiao == "Centro-Oeste"] == ["DF", "GO", "MS", "MT"]
    assert [uf for regiao, uf in chaves if regiao == "Nordeste"] == [
        "AL",
        "BA",
        "CE",
        "MA",
        "PB",
        "PE",
        "PI",
        "RN",
        "SE",
    ]


def test_percentual_de_urnas_compara_apuradas_com_total_nao_com_totalizadas(resultado):
    resultado = replace(resultado, secoes=Secoes(15686, 6, 6, Decimal("0.0003825"), Decimal(1)))
    assert tabela_presidente_por_uf([resultado]).linhas[1][4] == 6 / 15686


def test_totais_zerados_nao_inventam_percentuais(resultado):
    resultado = replace(resultado, secoes=Secoes(0, 0), eleitorado=Eleitorado(0, 0), votos=Votos(0, 0, 0, 0))
    linha = tabela_presidente_por_uf([resultado]).linhas[1]
    assert linha[4] is linha[7] is linha[8] is linha[9] is None


def test_divulgacao_bloqueada_preserva_apenas_contagens_de_cobertura(resultado):
    linha = tabela_presidente_por_uf([replace(resultado, divulgacao_liberada=False)]).linhas[1]
    assert linha[2:8] == [40, 100, 0.4, 800, 2000, 0.4]
    assert linha[8:12] == [None, None, None, None]
    assert linha[14:] == [None, None, None, None]


def test_candidato_ausente_nao_vira_zero(resultado):
    linha = tabela_presidente_por_uf([replace(resultado, candidatos=resultado.candidatos[:1])]).linhas[1]
    assert linha[8] is linha[10] is None
    assert linha[9] == 0.4 and linha[11] == 200


@pytest.mark.parametrize("campo,valor", [("cargo", 3), ("turno", 1), ("eleicao", 9999)])
def test_rejeita_mistura_de_contextos(resultado, campo, valor):
    outro = replace(resultado, contexto=replace(resultado.contexto, abrangencia="rj", **{campo: valor}))
    with pytest.raises(ValueError, match="contexto"):
        tabela_presidente_por_uf([resultado, outro])


def test_rejeita_uf_duplicada(resultado):
    with pytest.raises(ValueError, match="duplicada"):
        tabela_presidente_por_uf([resultado, resultado])


def test_formato_de_quantidades_e_percentuais_sem_reaplicar_valores(resultado):
    tabela = tabela_presidente_por_uf([resultado])
    pedidos = pedidos_formatacao(8, tabela.nome, tabela.linhas, 29, 18)
    percentuais = [
        pedido["repeatCell"]
        for pedido in pedidos
        if pedido.get("repeatCell", {}).get("cell", {}).get("userEnteredFormat", {}).get("numberFormat", {}).get("type")
        == "PERCENT"
    ]
    assert {pedido["range"]["startColumnIndex"] for pedido in percentuais} == {4, 7, 8, 9, 13, 15, 17}
    assert all(pedido["range"]["startRowIndex"] == 1 for pedido in percentuais)
    assert "#,##0" in str(pedidos)
    assert "WRAP" in str(pedidos)
    assert any(
        pedido.get("autoResizeDimensions", {}).get("dimensions", {}).get("dimension") == "ROWS" for pedido in pedidos
    )
    assert all("updateCells" not in pedido for pedido in pedidos)


def test_ausencia_de_abstencao_nao_vira_zero(resultado):
    resultado = replace(resultado, eleitorado=Eleitorado(2000, 800))
    assert tabela_presidente_por_uf([resultado]).linhas[1][12:14] == [None, None]


def test_percentuais_sem_base_ficam_vazios(resultado):
    resultado = replace(resultado, eleitorado=Eleitorado(2000, 0, instalado=0, abstencoes=0), votos=Votos(0, 0, 0, 0))
    linha = tabela_presidente_por_uf([resultado]).linhas[1]
    assert linha[12] == linha[14] == linha[16] == 0
    assert linha[13] is linha[15] is linha[17] is None


def test_agregacao_preserva_abstencao_e_base_sem_inventar_ausencia(resultado):
    from apuracao.agregacao import somar_presidente

    fontes = [replace(resultado, contexto=replace(resultado.contexto, abrangencia=uf.lower())) for uf in UFS | {"ZZ"}]
    soma = somar_presidente(fontes)
    assert soma.eleitorado.abstencoes == 28 * 200
    assert soma.eleitorado.instalado == 28 * 800
    fontes[0] = replace(fontes[0], eleitorado=Eleitorado(2000, 800))
    soma = somar_presidente(fontes)
    assert soma.eleitorado.abstencoes is None
    assert soma.eleitorado.instalado is None


def test_historico_antigo_sem_abstencao_continua_legivel(resultado):
    import json
    from dataclasses import asdict

    from apuracao.agregacao import fontes_salvas

    dados = json.loads(json.dumps(asdict(resultado), default=str))
    dados["eleitorado"].pop("abstencoes")
    dados["eleitorado"].pop("instalado")
    (restaurado,) = fontes_salvas([dados])
    assert restaurado.eleitorado.abstencoes is None
    assert restaurado.eleitorado.instalado is None
