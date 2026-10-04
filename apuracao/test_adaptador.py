from dataclasses import is_dataclass
from datetime import datetime
from decimal import Decimal

from apuracao.adaptador2022 import Apuracao2022
from apuracao.modelo import Contexto


def test_2022_retorna_objetos_tipados(dados_2022):
    contexto = Contexto(2022, 1, 544, 1, "br")
    resultado = Apuracao2022(contexto).ler(dados_2022)
    assert is_dataclass(resultado)
    assert resultado.contexto == contexto
    assert resultado.gerada_em == datetime.fromisoformat("2022-10-02T18:30:00-03:00")
    assert resultado.secoes.total == 100
    assert resultado.secoes.apuradas == 50
    assert resultado.eleitorado.total == 200
    assert resultado.eleitorado.apurado == 100
    assert resultado.votos.validos == 90
    assert resultado.votos.nulos == 5
    assert resultado.votos.brancos == 5
    assert resultado.votos.total == 100
    assert all(is_dataclass(candidato) for candidato in resultado.candidatos)
    assert resultado.candidatos[0].nome_urna == "LULA"
    assert resultado.candidatos[0].numero == "13"
    assert resultado.candidatos[0].percentual == Decimal("0.60")
    assert resultado.candidatos[1].vice == "VICE B & C"
    assert resultado.votos.anulados is None
    assert resultado.secoes.totalizadas is None


def test_ponte_preserva_saida_valida(dados_2022):
    from apuracao.apresentacao import dados_legados
    from apuracao.apuracao import read_data

    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    assert dados_legados(resultado) == read_data(dados_2022)
