from dataclasses import replace

from apuracao.acompanhamento import RotinaApuracao, cria_parser
from apuracao.adaptador2022 import Apuracao2022
from apuracao.formatacao import UFS
from apuracao.modelo import Contexto, Secoes
from apuracao.test_acompanhamento import Publicador


def test_opcao_melhor_cobertura():
    args = cria_parser().parse_args(["2026", "1", "--presidente-automatico"])
    assert args.presidente_automatico


def test_nacional_aproveitado_mesmo_falha_uf(dados_2022, tmp_path, monkeypatch):
    base = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)

    class Coletor:
        def coletar(self, contexto, adaptador, url):
            if contexto.abrangencia == "zz":
                raise OSError("exterior indisponível")
            return replace(base, contexto=contexto, geracao=contexto.abrangencia, secoes=Secoes(2800, 70, 70))

        def historico(self, contexto, adaptador):
            return []

    coletor = Coletor()
    publisher = Publicador()
    rotina = RotinaApuracao(
        2026,
        1,
        "presidente",
        "ID",
        tmp_path,
        coletor=coletor,
        coletor_factory=lambda: coletor,
        planilha=publisher,
        presidente_automatico=True,
    )
    rotina._contextos = [Contexto(2026, 1, 6257, 1, area) for area in sorted([area.lower() for area in UFS] + ["zz"])]
    monkeypatch.setattr(rotina._limite, "aguardar", lambda: None)
    try:
        rotina.run()
        assert len(publisher.lotes) == 1
        assert publisher.lotes[0][0].cor_aba == "preto"
        assert ["Seções totalizadas", 70, "Seções totais", 2800, "% Seções totalizadas", 0.025] in publisher.lotes[0][
            0
        ].linhas
    finally:
        rotina.close()


def test_historico_identifica_origem_sem_percentual_na_coluna_textual(dados_2022):
    from apuracao.apresentacao import tabela_historico

    base = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    tabela = tabela_historico([base], incluir_origem=True)
    assert tabela.linhas[0][-1] == "Origem"
    assert tabela.linhas[1][-1] == "Nacional TSE"
    assert len(tabela.linhas[0]) - 1 not in tabela.colunas_percentuais
