from apuracao.coleta import Coletor
from apuracao.test_coleta import SessaoFalsa, resposta


def test_consulta_tse_adiciona_cache_busting(tmp_path, monkeypatch):
    monkeypatch.setattr("apuracao.coleta.time.time_ns", lambda: 123456789)
    url = "https://resultados.tse.jus.br/oficial/teste.json?existente=1"
    sessao = SessaoFalsa(resposta({"idg": "1"}))
    assert Coletor(tmp_path, session=sessao).buscar_json(url) == {"idg": "1"}
    assert sessao.chamadas[0][0] == url + "&_=123456789"
    assert sessao.chamadas[0][1]["headers"] == {"Cache-Control": "no-cache", "Pragma": "no-cache"}
