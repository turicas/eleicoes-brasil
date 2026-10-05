from portal_eleitos.relatorio import avaliar, resumir


def cargo(estado="finalizado", vagas=2, quantidade=2, coleta="sucesso", tf=True):
    return {
        "cargo": {"codigo": 5, "nome": "Senador"},
        "turno": 1,
        "estado": estado,
        "tf": tf,
        "vagas": vagas,
        "eleitos": [{} for _ in range(quantidade)],
        "fonte": {"estado_coleta": coleta, "gerado_em": "2026-10-05T01:00:00-03:00"},
    }


def test_so_final_com_lista_compativel_esta_concluido():
    assert avaliar(cargo())["situacao"] == "concluido"
    assert avaliar(cargo(vagas=3))["situacao"] == "revisar"
    assert avaliar(cargo(vagas=None))["situacao"] == "revisar"
    assert avaliar(cargo(coleta="ultima-versao-valida"))["situacao"] == "atualizacao-falhou"


def test_pendente_e_segundo_turno_nao_sao_falhas():
    assert avaliar(cargo("pendente", quantidade=0, tf=False))["situacao"] == "aguardando-tse"
    assert avaliar(cargo("segundo-turno", vagas=1, quantidade=0))["situacao"] == "aguardando-segundo-turno"
    assert avaliar(cargo("sem-eleitos", quantidade=0))["situacao"] == "sem-atribuicao"


def test_resumo_informa_se_pode_parar_rodada():
    relatorio = resumir({"AC": {"cargos": [cargo()]}, "SP": {"cargos": [cargo("pendente", quantidade=0, tf=False)]}})
    assert relatorio["pode_encerrar_primeiro_turno"] is False
    assert relatorio["contagens"] == {"concluido": 1, "aguardando-tse": 1}
    assert relatorio["resultados"][1]["uf"] == "SP"
    assert resumir({"AC": {"cargos": [cargo()]}})["pode_encerrar_primeiro_turno"] is True
