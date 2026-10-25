from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

import pytest

from .adaptador2026 import Apuracao2026
from .configuracao import contextos_eleicao, url_municipios, url_resultado
from .modelo import Contexto


@pytest.fixture
def contexto():
    return Contexto(2026, 1, 6257, 1, "br")


@pytest.fixture
def dados():
    return {
        "ele": "6257",
        "t": "1",
        "f": "o",
        "tpabr": "br",
        "cdabr": "br",
        "dg": "04/10/2026",
        "hg": "19:00:00",
        "idg": "12",
        "dv": "s",
        "dt": "04/10/2026",
        "ht": "18:59:00",
        "tf": "n",
        "and": "p",
        "md": "s",
        "s": {"ts": "100", "sa": "80", "st": "90", "pst": "90,00", "psa": "80,00"},
        "e": {"te": "200", "esa": "160"},
        "v": {"tv": "160", "vv": "100", "tvn": "20", "vb": "10", "vvc": "130", "van": "20", "vansj": "10"},
        "carg": [
            {
                "cd": "1",
                "agr": [
                    {
                        "par": [
                            {
                                "sg": "PA",
                                "cand": [
                                    {
                                        "n": "10",
                                        "nm": "Pessoa &amp; A",
                                        "nmu": "Pessoa A",
                                        "vap": "40",
                                        "pvap": "40,00",
                                        "pvapn": "30,769230",
                                        "sqcand": "101",
                                        "dvt": "Válido",
                                        "st": "2º turno",
                                        "vs": [{"tp": "s1", "nm": "Suplente"}, {"tp": "v", "nm": "Vice &amp; A"}],
                                    },
                                    {"n": "20", "nm": "Pessoa B", "nmu": "B", "vap": "60", "pvap": "60,00"},
                                ],
                            }
                        ]
                    }
                ],
            }
        ],
    }


def test_resultado(contexto, dados):
    resultado = Apuracao2026(contexto).ler(dados)
    primeiro, segundo = resultado.candidatos
    assert (primeiro.numero, segundo.numero) == ("10", "20")
    assert (primeiro.nome, primeiro.nome_urna, primeiro.vice) == ("Pessoa & A", "Pessoa A", "Vice & A")
    assert (primeiro.partido, primeiro.sequencial, primeiro.destinacao, primeiro.situacao) == (
        "PA",
        "101",
        "Válido",
        "2º turno",
    )
    assert primeiro.percentual == Decimal("0.30769230")
    assert segundo.percentual == Decimal("0.60")
    assert segundo.vice is None
    assert (resultado.secoes.total, resultado.secoes.apuradas, resultado.secoes.totalizadas) == (100, 80, 90)
    assert resultado.secoes.percentual_totalizadas == Decimal("0.90")
    assert resultado.secoes.percentual_apuradas == Decimal("0.80")
    assert (resultado.eleitorado.total, resultado.eleitorado.apurado) == (200, 160)
    assert (resultado.votos.total, resultado.votos.validos, resultado.votos.nulos, resultado.votos.brancos) == (
        160,
        100,
        20,
        10,
    )
    assert (resultado.votos.concorrentes, resultado.votos.anulados, resultado.votos.anulados_sub_judice) == (
        130,
        20,
        10,
    )
    assert (
        resultado.geracao,
        resultado.divulgacao_liberada,
        resultado.andamento,
        resultado.finalizada,
        resultado.matematicamente_definida,
    ) == ("12", True, "p", False, "s")
    assert resultado.gerada_em.utcoffset() == timedelta(hours=-3)
    assert resultado.totalizada_em.hour == 18


def test_zero_e_opcionais(contexto, dados):
    dados["dv"] = "n"
    dados["dt"] = dados["ht"] = ""
    for campo in ("tf", "and", "md", "idg"):
        dados.pop(campo)
    dados["s"] = {"ts": "0", "sa": "0"}
    dados["e"] = {"te": "0", "esa": "0"}
    dados["v"] = {campo: "0" for campo in ("tv", "vv", "tvn", "vb")}
    dados["carg"][0]["agr"] = []
    resultado = Apuracao2026(contexto).ler(dados)
    assert resultado.candidatos == ()
    assert resultado.votos.anulados is None
    assert resultado.votos.anulados_sub_judice is None
    assert resultado.votos.concorrentes is None
    assert resultado.secoes.totalizadas is None
    assert resultado.finalizada is None
    assert resultado.totalizada_em is None
    assert resultado.divulgacao_liberada is False


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("ele", "999"),
        ("t", "2"),
        ("f", "s"),
        ("tpabr", "uf"),
        ("cdabr", "sp"),
        ("dv", "x"),
        ("tf", "x"),
        ("md", "x"),
        ("and", "x"),
        ("dg", "inválida"),
    ],
)
def test_identidade_e_estado_invalidos(contexto, dados, campo, valor):
    dados[campo] = valor
    with pytest.raises(ValueError, match=rf"{campo}.*6257.*br"):
        Apuracao2026(contexto).ler(dados)


def test_cargo_incompativel(contexto, dados):
    dados["carg"][0]["cd"] = "3"
    with pytest.raises(ValueError, match=r"carg.*6257.*br"):
        Apuracao2026(contexto).ler(dados)


@pytest.mark.parametrize("valor", ["-1", "1.5", True, 1.5, "abc"])
def test_contagem_invalida(contexto, dados, valor):
    dados["v"]["tv"] = valor
    with pytest.raises(ValueError, match=r"v.tv.*6257.*br"):
        Apuracao2026(contexto).ler(dados)


@pytest.mark.parametrize("valor", ["-1", "NaN", "Infinity", "101", "abc"])
def test_percentual_invalido(contexto, dados, valor):
    dados["carg"][0]["agr"][0]["par"][0]["cand"][0]["pvapn"] = valor
    with pytest.raises(ValueError, match=r"pvapn.*6257.*br"):
        Apuracao2026(contexto).ler(dados)


def test_campo_ausente(contexto, dados):
    del dados["e"]["esa"]
    with pytest.raises(ValueError, match=r"e.esa.*6257.*br"):
        Apuracao2026(contexto).ler(dados)


def test_ano_invalido():
    with pytest.raises(ValueError, match="ano"):
        Apuracao2026(Contexto(2022, 1, 544, 1, "br"))


def pleito(ciclo="ele2026", data="04/10/2026", tipo="8", cargo="1", abrangencia="br", turno="1", eleicao="6257"):
    return {
        "c": ciclo,
        "dt": data,
        "e": [
            {"cd": eleicao, "cdt2": "6258", "tp": tipo, "t": turno, "abr": [{"cd": abrangencia, "cp": [{"cd": cargo}]}]}
        ],
    }


def test_filtra_ciclos_suplementares_e_municipal():
    dados = {
        "f": "o",
        "pl": [
            pleito(),
            pleito(ciclo="ele2024"),
            pleito(data="01/12/2025"),
            pleito(tipo="9"),
            pleito(tipo="2"),
            pleito(tipo="3", cargo="11", eleicao="6261"),
        ],
    }
    assert contextos_eleicao(dados, 2026, 1, 1) == [Contexto(2026, 1, 6257, 1, "br")]


def test_segundo_turno_exige_eleicao_explicita():
    with pytest.raises(ValueError, match="(?i)segundo turno|2º turno"):
        contextos_eleicao({"f": "o", "pl": [pleito()]}, 2026, 2, 1)
    assert contextos_eleicao({"f": "o", "pl": [pleito(turno="2", eleicao="6258")]}, 2026, 2, 1) == [
        Contexto(2026, 2, 6258, 1, "br")
    ]


def test_governador_expande_municipios():
    dados = {"f": "o", "pl": [pleito(tipo="1", cargo="3", eleicao="6259")]}
    municipios = {"f": "o", "abr": [{"cd": "SP"}, {"cd": "AC"}, {"cd": "zz"}]}
    assert contextos_eleicao(dados, 2026, 1, 3, municipios) == [
        Contexto(2026, 1, 6259, 3, "sp"),
        Contexto(2026, 1, 6259, 3, "ac"),
    ]
    with pytest.raises(ValueError, match="municipios|municípios"):
        contextos_eleicao(dados, 2026, 1, 3)


def test_governador_ufs_com_cargo():
    dados = {"f": "o", "pl": [pleito(tipo="1", cargo="3", abrangencia="SP", turno="2", eleicao="6260")]}
    dados["pl"][0]["e"][0]["abr"].append({"cd": "ac", "cp": [{"cd": "5"}]})
    assert contextos_eleicao(dados, 2026, 2, 3) == [Contexto(2026, 2, 6260, 3, "sp")]
    dados["pl"][0]["e"][0]["abr"][0]["cd"] = "zz"
    with pytest.raises(ValueError, match="abr"):
        contextos_eleicao(dados, 2026, 2, 3)


def test_configuracao_simulada():
    with pytest.raises(ValueError, match="f"):
        contextos_eleicao({"f": "s", "pl": [pleito()]}, 2026, 1, 1)


@pytest.mark.parametrize(
    "turno,cargo,eleicao,quantidade", [(1, 1, 544, 1), (2, 1, 545, 1), (1, 3, 546, 27), (2, 3, 547, 12)]
)
def test_compatibilidade_2022(turno, cargo, eleicao, quantidade):
    contextos = contextos_eleicao({}, 2022, turno, cargo)
    assert len(contextos) == quantidade
    assert all(contexto.eleicao == eleicao for contexto in contextos)
    if cargo == 3 and turno == 2:
        assert [contexto.abrangencia for contexto in contextos] == [
            "al",
            "am",
            "ba",
            "es",
            "ms",
            "pb",
            "pe",
            "ro",
            "rs",
            "sc",
            "se",
            "sp",
        ]


def test_urls(contexto):
    assert (
        url_resultado(contexto) == "https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json"
    )
    assert url_municipios(2026, 6259) == "https://resultados.tse.jus.br/oficial/ele2026/6259/config/mun-e006259-cm.json"
    assert (
        url_resultado(Contexto(2022, 2, 547, 3, "sp"))
        == "https://resultados.tse.jus.br/oficial/ele2022/547/dados-simplificados/sp/sp-c0003-e000547-r.json"
    )
    diretorios = [
        {"tp": "u", "dir": "<base>/<ambiente>/<ciclo>/<cd_eleicao>/dados/<uf>/"},
        {"tp": "cm", "dir": "<base>/<ambiente>/<ciclo>/<cd_eleicao>/config"},
    ]
    assert url_resultado(contexto, diretorios) == url_resultado(contexto)
    assert url_municipios(2026, 6259, diretorios) == url_municipios(2026, 6259)


@pytest.mark.parametrize(
    "template", ["<base>/<desconhecido>", "<base>/<cd_pleito>", "https://resultados.tse.jus.br/simulado/<ciclo>"]
)
def test_template_invalido(contexto, template):
    with pytest.raises(ValueError):
        url_resultado(contexto, [{"tp": "u", "dir": template}])


def test_uf_e_identidade_resultado(dados):
    dados["ele"] = "6259"
    dados["tpabr"] = "uf"
    dados["cdabr"] = "sp"
    dados["carg"][0]["cd"] = "3"
    contexto = Contexto(2026, 1, 6259, 3, "sp")
    assert Apuracao2026(contexto).ler(dados).contexto == contexto


def test_ordem_entre_agrupamentos(contexto, dados):
    partido = dados["carg"][0]["agr"][0]["par"][0]
    segundo = partido["cand"].pop()
    dados["carg"][0]["agr"].append({"par": [{"sg": "PB", "cand": [deepcopy(segundo)]}]})
    assert [candidato.numero for candidato in Apuracao2026(contexto).ler(dados).candidatos] == ["10", "20"]


def test_percentual_json_numerico(contexto, dados):
    dados["carg"][0]["agr"][0]["par"][0]["cand"][0]["pvapn"] = 30.76923
    assert Apuracao2026(contexto).ler(dados).candidatos[0].percentual == Decimal("0.3076923")


def test_abstencao_e_eleitorado_instalado(contexto, dados):
    dados["e"].update({"a": "40", "esi": "160"})
    resultado = Apuracao2026(contexto).ler(dados)
    assert resultado.eleitorado.abstencoes == 40
    assert resultado.eleitorado.instalado == 160


def test_ausencia_de_abstencao_e_preservada(contexto, dados):
    resultado = Apuracao2026(contexto).ler(dados)
    assert resultado.eleitorado.abstencoes is None
    assert resultado.eleitorado.instalado is None
