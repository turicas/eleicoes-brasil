import pytest

from apuracao.configuracao import contextos_eleicao, url_resultado


@pytest.fixture
def configuracao_segundo_turno():
    return {
        "f": "o",
        "pl": [
            {
                "c": "ele2026",
                "dt": "25/10/2026",
                "e": [
                    {"cd": "6258", "t": "2", "tp": "8", "abr": [{"cd": "br", "cp": [{"cd": "1"}]}]},
                    {
                        "cd": "6260",
                        "t": "2",
                        "tp": "1",
                        "abr": [{"cd": sigla, "cp": [{"cd": "3"}]} for sigla in ("am", "rn", "df", "es", "ac", "to")],
                    },
                    {"cd": "9999", "t": "1", "tp": "4", "abr": [{"cd": "sp", "cp": [{"cd": "11"}]}]},
                ],
            }
        ],
    }


def test_segundo_turno_descobre_presidente_e_apenas_governos_em_disputa(configuracao_segundo_turno):
    (presidente,) = contextos_eleicao(configuracao_segundo_turno, 2026, 2, 1)
    governadores = contextos_eleicao(configuracao_segundo_turno, 2026, 2, 3)
    assert presidente.eleicao == 6258
    assert presidente.abrangencia == "br"
    assert {contexto.abrangencia for contexto in governadores} == {"ac", "am", "df", "es", "rn", "to"}
    assert all(contexto.eleicao == 6260 and contexto.turno == 2 for contexto in governadores)
    assert url_resultado(presidente).endswith("/6258/dados/br/br-c0001-e006258-u.json")


def test_segundo_turno_respeita_cargos_publicados_por_abrangencia(configuracao_segundo_turno):
    eleicao = configuracao_segundo_turno["pl"][0]["e"][1]
    eleicao["abr"].append({"cd": "sp", "cp": [{"cd": "5"}]})
    governadores = contextos_eleicao(configuracao_segundo_turno, 2026, 2, 3)
    assert "sp" not in {contexto.abrangencia for contexto in governadores}
