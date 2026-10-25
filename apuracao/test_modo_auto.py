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


class ExecutorControlado:
    def __init__(self):
        self.pendente = False
        self.futuros = []

    def submit(self, executar, contexto, **kwargs):
        from concurrent.futures import Future

        futuro = Future()
        if not self.pendente:
            try:
                futuro.set_result(executar(contexto, **kwargs))
            except Exception as erro:
                futuro.set_exception(erro)
        self.futuros.append(futuro)
        return futuro

    def shutdown(self, **kwargs):
        for futuro in self.futuros:
            futuro.cancel()


def rotina_segundo_turno(dados_2022, tmp_path, monkeypatch):
    from apuracao import acompanhamento

    base = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)

    class Coletor:
        nacional_disponivel = True
        nacional_totalizadas = 20
        regional_disponivel = True

        def coletar(self, contexto, adaptador, url):
            if contexto.abrangencia == "br":
                if not self.nacional_disponivel:
                    raise OSError("nacional indisponível")
                total, totalizadas = 2800, self.nacional_totalizadas
            else:
                if not self.regional_disponivel:
                    raise OSError("regional indisponível")
                total, totalizadas = 100, 2
            return replace(
                base,
                contexto=contexto,
                geracao=f"{contexto.abrangencia}-{totalizadas}",
                secoes=Secoes(total, totalizadas, totalizadas),
            )

        def historico(self, contexto, adaptador):
            return []

    coletor = Coletor()
    publicador = Publicador()
    rotina = RotinaApuracao(
        2026,
        2,
        "presidente",
        "ID",
        tmp_path,
        coletor=coletor,
        coletor_factory=lambda: coletor,
        planilha=publicador,
        presidente_automatico=True,
    )
    rotina._contextos = [Contexto(2026, 2, 6258, 1, area) for area in sorted([uf.lower() for uf in UFS] + ["zz"])]
    rotina._executor = ExecutorControlado()
    monkeypatch.setattr(rotina._limite, "aguardar", lambda: None)
    monkeypatch.setattr(
        acompanhamento,
        "wait",
        lambda futuros, **kwargs: (
            {futuro for futuro in futuros if futuro.done()},
            {futuro for futuro in futuros if not futuro.done()},
        ),
    )
    return rotina, coletor, publicador


def test_segundo_turno_preserva_soma_completa_enquanto_rodada_regional_pendente(dados_2022, tmp_path, monkeypatch):
    rotina, coletor, publicador = rotina_segundo_turno(dados_2022, tmp_path, monkeypatch)
    try:
        rotina.run()
        rotina._executor.pendente = True
        coletor.nacional_totalizadas = 25
        rotina.run()
        linhas = publicador.lotes[-1][0].linhas
        totalizacao = next(linha for linha in linhas if linha and linha[0] == "Seções totalizadas")
        assert totalizacao[1] == 56
        assert any(linha and linha[0] == "Origem" for linha in linhas)
    finally:
        rotina.close()


def test_segundo_turno_preserva_soma_se_nacional_falha_entre_rodadas(dados_2022, tmp_path, monkeypatch):
    rotina, coletor, publicador = rotina_segundo_turno(dados_2022, tmp_path, monkeypatch)
    try:
        rotina.run()
        rotina._executor.pendente = True
        coletor.nacional_disponivel = False
        rotina.run()
        assert len(publicador.lotes) == 1
    finally:
        rotina.close()


def test_segundo_turno_preserva_nacional_se_todas_fontes_falham_depois(dados_2022, tmp_path, monkeypatch):
    rotina, coletor, publicador = rotina_segundo_turno(dados_2022, tmp_path, monkeypatch)
    coletor.regional_disponivel = False
    try:
        rotina.run()
        coletor.nacional_disponivel = False
        rotina.run()
        assert len(publicador.lotes) == 1
    finally:
        rotina.close()
