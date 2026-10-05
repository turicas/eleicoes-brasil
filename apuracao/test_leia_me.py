from apuracao.leia_me import tabela_leia_me
from apuracao.planilha import Planilha
from apuracao.test_planilha import ClienteSimulado, PlanilhaSimulada, aba


def test_conteudo_fontes_e_redes_2026():
    tabela = tabela_leia_me(2026, 1, intervalo_presidente=10, intervalo_ufs=30)
    linhas = dict(tabela.linhas)
    assert tabela.nome == "LEIA-ME"
    assert tabela.indice == 0
    assert linhas["Desenvolvido por:"] == "Álvaro Justen"
    assert linhas["Código-fonte:"] == "https://github.com/turicas/eleicoes-brasil"
    assert linhas["Twitter:"] == "https://twitter.com/turicas"
    assert linhas["Bluesky:"] == "https://bsky.app/profile/turicas.bsky.social"
    assert "6257/dados/br/br-c0001-e006257-u.json" in linhas["Fonte dos dados (presidente nacional):"]
    assert "6259/dados/sp/sp-c0003-e006259-u.json" in linhas["Fonte dos dados (governador - ex. SP):"]
    assert "10s" in linhas["Consulta a cada:"] and "30s" in linhas["Consulta a cada:"]


def test_cria_leia_me_primeira_sem_tocar_resultados():
    remota = PlanilhaSimulada({1: aba("Presidente", 40, 6, 1)})
    antes = remota.abas[1]["valores"].copy()
    publicador = Planilha(ClienteSimulado(remota), "ID", 2026, 1)
    publicador.publicar([tabela_leia_me(2026, 1)])
    nova = next(item for item in remota.abas.values() if item["properties"]["title"] == "LEIA-ME")
    assert nova["properties"]["index"] == 0
    assert remota.abas[1]["valores"] == antes
    publicador.publicar([tabela_leia_me(2026, 1)])
    assert len(remota.abas) == 2


def test_preserva_revisao_editorial_e_exemplo_por_uf():
    linhas = dict(tabela_leia_me(2026, 1).linhas)
    assert linhas["Atualização dos dados:"] == "Somente quando muda na origem."
    assert "Atualização inteligente de presidente:" in linhas
    assert 'coluna "Origem" da aba LinhaDoTempo' in linhas["Origem dos resultados:"]
    assert "Cor da aba de UF verde:" in linhas
    assert "MD e TF:" not in linhas
    assert (
        "https://resultados.tse.jus.br/oficial/ele2026/6257/dados/sp/sp-c0001-e006257-u.json"
        in linhas["Fonte dos dados (presidente por UF):"]
    )


def test_exemplo_por_uf_2022_nao_usa_codigo_2026():
    linhas = dict(tabela_leia_me(2022, 2).linhas)
    assert (
        "ele2022/545/dados-simplificados/sp/sp-c0001-e000545-r.json" in linhas["Fonte dos dados (presidente por UF):"]
    )
