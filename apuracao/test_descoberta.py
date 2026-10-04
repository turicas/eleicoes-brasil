import pytest

from apuracao.configuracao import codigo_eleicao
from apuracao.test_2026 import pleito


def test_codigo_para_buscar_municipios_sem_circularidade():
    dados = {"f": "o", "pl": [pleito(tipo="1", cargo="3", eleicao="6259")]}
    assert codigo_eleicao(dados, 2026, 1, 3) == 6259


def test_codigo_segundo_turno_ainda_ausente():
    dados = {"f": "o", "pl": [pleito(tipo="1", cargo="3", eleicao="6259")]}
    with pytest.raises(ValueError, match="turno"):
        codigo_eleicao(dados, 2026, 2, 3)
