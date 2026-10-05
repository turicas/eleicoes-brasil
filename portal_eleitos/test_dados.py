"""Exemplos sintéticos do leiaute oficial, sem afirmar resultados eleitorais reais."""

from copy import deepcopy

import pytest

from portal_eleitos.dados import UFS_NOMES, descobrir_fontes, normalizar_resultado


def candidato(situacao="Eleito", sequencial="123", votos="42", nome="Ágata"):
    return {
        "n": "00123",
        "sqcand": sequencial,
        "nm": "Ágata da Silva",
        "nmu": nome,
        "vap": votos,
        "st": situacao,
        "dvt": "Válido",
        "e": "s",
        "dt": "01/01/1980",
    }


def resultado(cargo=7, uf="AC", candidatos=None):
    return {
        "f": "o",
        "ele": "6259",
        "t": "1",
        "tpabr": "br" if uf == "BR" else "uf",
        "cdabr": uf,
        "tf": "s",
        "and": "f",
        "dg": "04/10/2026",
        "hg": "23:01:02",
        "idg": "000123",
        "dt": "04/10/2026",
        "ht": "23:00:00",
        "esae": "n",
        "mnae": [],
        "carg": [
            {
                "cd": str(cargo),
                "nmn": "Deputado estadual",
                "nv": "24",
                "agr": [
                    {
                        "par": [
                            {
                                "n": "09",
                                "sg": "TESTE",
                                "nm": "Partido de teste",
                                "cand": candidatos or [candidato()],
                            }
                        ]
                    }
                ],
            }
        ],
    }


def normalizar(dados, cargo=7, uf="ac"):
    return normalizar_resultado(
        dados,
        ano=2026,
        eleicao=6259,
        turno=1,
        cargo=cargo,
        uf=uf,
        url=f"https://resultados.tse.jus.br/oficial/ele2026/6259/dados/{uf.lower()}/{uf.lower()}-c{cargo:04d}-e006259-u.json",
        capturado_em="2026-10-05T02:02:00+00:00",
        hash_bruto="a" * 64,
    )


def test_normalizacao_proveniencia_foto_e_pureza():
    dados = resultado()
    original = deepcopy(dados)
    documento = normalizar(dados)
    assert dados == original
    assert documento["cargo"] == {"codigo": 7, "nome": "Deputado estadual"}
    assert documento["abrangencia_disputa"] == {"tipo": "uf", "codigo": "AC"}
    assert documento["vagas"] == 24
    assert documento["tf"] is True
    assert documento["estado"] == "finalizado"
    assert documento["eleicao"] == 6259 and documento["turno"] == 1
    assert documento["fonte"]["gerado_em"] == "2026-10-04T23:01:02-03:00"
    assert documento["fonte"]["totalizado_em"] == "2026-10-04T23:00:00-03:00"
    assert documento["fonte"]["idg"] == "000123"
    assert documento["fonte"]["estado_coleta"] == "sucesso"
    eleito = documento["eleitos"][0]
    assert eleito["sequencial_tse"] == "123"
    assert eleito["numero"] == "00123"
    assert eleito["partido"] == {"numero": "09", "sigla": "TESTE", "nome": "Partido de teste"}
    assert eleito["votos"] == 42 and eleito["destinacao_votos"] == "Válido"
    assert "dt" not in eleito and "nascimento" not in eleito
    assert eleito["foto"] == {
        "estado": "pendente",
        "url": None,
        "sha256": None,
        "largura": None,
        "altura": None,
        "formato": "webp",
        "fonte_tse": "https://resultados.tse.jus.br/oficial/ele2026/6259/fotos/ac/123.jpeg",
    }


def test_situacoes_exatas_e_ordenacao_sem_inferencia():
    candidatos = [
        candidato("Eleito por média", "3", "5", "B"),
        candidato("Eleito por QP", "2", "5", "A"),
        candidato("Eleito", "1", "9"),
        candidato("Suplente"),
        candidato("Não eleito"),
        candidato("eleito"),
        candidato("Eleito "),
        candidato(None),
        candidato("Desconhecida"),
    ]
    documento = normalizar(resultado(candidatos=candidatos))
    assert [eleito["sequencial_tse"] for eleito in documento["eleitos"]] == ["1", "2", "3"]
    assert [eleito["situacao"] for eleito in documento["eleitos"]] == ["Eleito", "Eleito por QP", "Eleito por média"]


def test_pendente_segundo_turno_e_sem_eleitos():
    dados = resultado(candidatos=[candidato("2º turno")])
    dados.update(tf="n", md="s", esae=None, dt="", ht="")
    assert normalizar(dados)["estado"] == "segundo-turno"
    dados["md"] = "e"
    documento = normalizar(dados)
    assert documento["estado"] == "pendente" and documento["eleitos"] == []
    assert documento["fonte"]["totalizado_em"] is None
    dados.update(tf="s", md=None, esae="s", mnae=["Motivo oficial de teste"])
    documento = normalizar(dados)
    assert documento["estado"] == "sem-eleitos"
    assert documento["motivos"] == ["Motivo oficial de teste"]
    del dados["carg"][0]["nv"]
    assert normalizar(dados)["vagas"] is None


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("f", "s"),
        ("ele", "1"),
        ("t", "2"),
        ("cdabr", "SP"),
        ("tpabr", "mu"),
        ("tf", "talvez"),
        ("md", "x"),
        ("esae", "x"),
        ("and", "x"),
        ("dg", "31/02/2026"),
        ("hg", "25:00:00"),
    ],
)
def test_erros_contextuais(campo, valor):
    dados = resultado()
    dados[campo] = valor
    with pytest.raises(ValueError, match=r"6259.*7.*AC"):
        normalizar(dados)


@pytest.mark.parametrize(
    "alteracao",
    ["eleito_parcial", "sem_eleitos_parcial", "sem_eleitos_com_eleito", "cargo", "vagas", "votos", "duplicado"],
)
def test_inconsistencias_nao_publicam(alteracao):
    dados = resultado()
    if alteracao == "eleito_parcial":
        dados["tf"] = "n"
    elif alteracao == "sem_eleitos_parcial":
        dados.update(tf="n", esae="s")
    elif alteracao == "sem_eleitos_com_eleito":
        dados["esae"] = "s"
    elif alteracao == "cargo":
        dados["carg"][0]["cd"] = "8"
    elif alteracao == "vagas":
        dados["carg"][0]["nv"] = "-1"
    elif alteracao == "votos":
        dados["carg"][0]["agr"][0]["par"][0]["cand"][0]["vap"] = "-1"
    else:
        dados["carg"][0]["agr"][0]["par"][0]["cand"] *= 2
    with pytest.raises(ValueError):
        normalizar(dados)


def configuracao():
    return {
        "f": "o",
        "arq": [{"tp": "u", "dir": "<base>/<ambiente>/<ciclo>/<cd_eleicao>/dados/<uf>"}],
        "pl": [
            {
                "cd": "1",
                "c": "ele2026",
                "dt": "04/10/2026",
                "e": [
                    {
                        "cd": "6259",
                        "cdt2": "6260",
                        "t": "1",
                        "tp": "1",
                        "abr": [{"cd": "br", "cp": [{"cd": str(cargo)} for cargo in (3, 5, 6, 7, 8)]}],
                    },
                    {"cd": "6261", "t": "1", "tp": "8", "abr": [{"cd": "br", "cp": [{"cd": "1"}]}]},
                ],
            }
        ],
    }


def test_descoberta_nacional_estadual_e_df():
    config = configuracao()
    original = deepcopy(config)
    fontes = descobrir_fontes(config, 2026, 1)
    assert config == original and len(UFS_NOMES) == 27
    assert len(fontes) == 109
    assert {fonte["uf"] for fonte in fontes if fonte["cargo"] == 3} == set(UFS_NOMES)
    assert {(fonte["uf"], fonte["cargo"]) for fonte in fontes if fonte["cargo"] in (7, 8)} == {
        (uf, 8 if uf == "DF" else 7) for uf in UFS_NOMES
    }
    presidente = next(fonte for fonte in fontes if fonte["cargo"] == 1)
    assert presidente == {
        "ano": 2026,
        "eleicao": 6261,
        "turno": 1,
        "cargo": 1,
        "uf": "BR",
        "url": "https://resultados.tse.jus.br/oficial/ele2026/6261/dados/br/br-c0001-e006261-u.json",
    }
    assert descobrir_fontes(config, 2026, 2) == []
    assert descobrir_fontes(config, 2022, 1) == []


def test_segundo_turno_so_com_eleicao_e_cargos_explicitos():
    config = configuracao()
    config["pl"][0]["e"].append(
        {
            "cd": "6260",
            "t": "2",
            "tp": "1",
            "abr": [
                {"cd": "ac", "cp": [{"cd": "3"}, {"cd": "5"}]},
            ],
        }
    )
    fontes = descobrir_fontes(config, 2026, 2)
    assert [(fonte["cargo"], fonte["uf"], fonte["eleicao"]) for fonte in fontes] == [(3, "AC", 6260)]
    config["pl"][0]["e"][0]["tp"] = "2"
    assert len(descobrir_fontes(config, 2026, 1)) == 1


@pytest.mark.parametrize(
    "diretorio",
    [
        "https://evil.invalid/<uf>",
        "http://resultados.tse.jus.br/<uf>",
        "https://resultados.tse.jus.br@evil.invalid/<uf>",
        "<base>/oficial/../segredo/<uf>",
        "<base>/<desconhecido>/<uf>",
    ],
)
def test_descoberta_rejeita_urls_inseguras(diretorio):
    config = configuracao()
    config["arq"][0]["dir"] = diretorio
    with pytest.raises(ValueError):
        descobrir_fontes(config, 2026, 1)


def test_config_simulada_e_uf_invalida():
    config = configuracao()
    config["f"] = "s"
    with pytest.raises(ValueError):
        descobrir_fontes(config, 2026, 1)
    config["f"] = "o"
    config["pl"][0]["e"][0]["abr"][0]["cd"] = "XX"
    with pytest.raises(ValueError):
        descobrir_fontes(config, 2026, 1)


def test_segundo_turno_formal_sem_md_preserva_estado():
    dados = resultado(cargo=3, candidatos=[candidato(situacao="2º turno")])
    assert normalizar(dados, cargo=3)["estado"] == "segundo-turno"
    assert normalizar(dados, cargo=3)["eleitos"] == []
