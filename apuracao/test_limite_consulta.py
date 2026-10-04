import pytest

from apuracao.acompanhamento import LimiteConsultas


def test_limita_inicio_das_consultas_sem_espera_real():
    tempos = [0.0]
    esperas = []

    def esperar(duracao):
        esperas.append(duracao)
        tempos[0] += duracao

    limite = LimiteConsultas(20, relogio=lambda: tempos[0], espera=esperar)
    for _ in range(4):
        limite.aguardar()
    assert esperas == pytest.approx([0.05, 0.05, 0.05])
