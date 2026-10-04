import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def legado():
    spec = importlib.util.spec_from_file_location("apuracao_legado", Path(__file__).with_name("apuracao.py"))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_leitura_existente(legado, dados_2022):
    resultado = legado.read_data(dados_2022)
    assert resultado["updated_at"] == "2022-10-02 18:30:00-03:00"
    assert resultado["secoes_apuradas"] == 50
    assert resultado["apuracao"] == [
        {
            "candidato": "LULA",
            "vice": "VICE A",
            "numero": "13",
            "votos_apurados": 54,
            "perc": "60.00%",
            "dif. próx.": 18,
        },
        {
            "candidato": "JAIR BOLSONARO",
            "vice": "VICE B & C",
            "numero": "22",
            "votos_apurados": 36,
            "perc": "40.00%",
            "dif. próx.": None,
        },
    ]
    assert resultado["title"] == "[50.00%] Apuração Eleições 2022 (atualizado: 2022-10-02 18:30:00-03:00)"


def test_tabela_existente(legado, dados_2022):
    linhas = legado.first_sheet_rows(legado.read_data(dados_2022))
    assert linhas[:3] == [
        ["candidato", "vice", "numero", "votos_apurados", "perc", "dif. próx."],
        ["LULA", "VICE A", "13", 54, "60.00%", 18],
        ["JAIR BOLSONARO", "VICE B & C", "22", 36, "40.00%", None],
    ]
    assert linhas[3:8] == [[], [], [], [], []]
    assert linhas[8:] == [
        ["Eleitorado apurado", "Eleitorado total", "Percentual"],
        [100, 200, "50.00%"],
        ["Seções apuradas", "Seções totais", "Percentual"],
        [50, 100, "50.00%"],
        ["Votos válidos", "(%)", "Nulos", "(%)", "Brancos", "(%)", "Totais"],
        [90, "90.00%", 5, "5.00%", 5, "5.00%", 100],
    ]


def test_historico_existente(legado, dados_2022, tmp_path):
    arquivo = tmp_path / "br-c0001-e000544-r-2022-10-02 18:30:00-03:00.json"
    arquivo.write_text(json.dumps(dados_2022))
    assert legado.second_sheet_rows([arquivo]) == [
        ["Data/Hora", "% Seções apuradas", "% Bolsonaro", "% Lula"],
        ["18:30:00", 0.5, 0.4, 0.6],
    ]


def test_url_existente(legado):
    assert legado.make_url(544, "BR", 1) == (
        "https://resultados.tse.jus.br/oficial/ele2022/544/dados-simplificados/br/br-c0001-e000544-r.json"
    )
