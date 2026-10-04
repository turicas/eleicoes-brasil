from dataclasses import replace

import pytest

from apuracao.acompanhamento import RotinaApuracao, cria_parser
from apuracao.adaptador2022 import Apuracao2022
from apuracao.formatacao import UFS
from apuracao.modelo import Contexto
from apuracao.test_acompanhamento import Publicador


class ColetorFontes:
    def __init__(self, resultado):
        self.resultado = resultado
        self.urls = []
        self.falhar = False

    def coletar(self, contexto, adaptador, url):
        self.urls.append(url)
        if contexto.abrangencia == "zz" and self.falhar:
            raise OSError("exterior indisponível")
        return replace(self.resultado, contexto=contexto, geracao=contexto.abrangencia)

    def historico(self, contexto, adaptador):
        return []


def test_cli_opcao_presidente_por_uf():
    assert cria_parser().parse_args(["2026", "1", "--presidente-por-uf"]).presidente_por_uf


def test_modo_ufs_exige_todas_as_fontes_sem_usar_nacional(dados_2022, tmp_path, monkeypatch):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    resultado = replace(resultado, contexto=Contexto(2026, 1, 6257, 1, "br"))
    coletor = ColetorFontes(resultado)
    publicador = Publicador()
    rotina = RotinaApuracao(
        2026,
        1,
        "presidente",
        "ID",
        tmp_path,
        coletor=coletor,
        coletor_factory=lambda coletor=coletor: coletor,
        planilha=publicador,
        presidente_por_uf=True,
    )
    rotina._contextos = [Contexto(2026, 1, 6257, 1, area) for area in sorted([uf.lower() for uf in UFS] + ["zz"])]
    monkeypatch.setattr(rotina._limite, "aguardar", lambda: None)
    try:
        rotina.run()
        assert len(publicador.lotes) == 1
        assert len(coletor.urls) == 28
        assert not any("/br/br-" in url for url in coletor.urls)
        assert publicador.lotes[0][0].nome == "Presidente"
        assert any(linha and linha[0] == "Origem" for linha in publicador.lotes[0][0].linhas)
        coletor.falhar = True
        with pytest.raises(ValueError, match="zz"):
            rotina.run()
        assert len(publicador.lotes) == 1
    finally:
        rotina.close()


def test_historico_soma_retoma_depois_reiniciar(dados_2022, tmp_path, monkeypatch):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    resultado = replace(resultado, contexto=Contexto(2026, 1, 6257, 1, "br"))
    fontes = [Contexto(2026, 1, 6257, 1, area) for area in sorted([uf.lower() for uf in UFS] + ["zz"])]
    for indice in range(2):
        coletor = ColetorFontes(resultado)
        if indice:
            coletor.resultado = replace(resultado, gerada_em=resultado.gerada_em.replace(minute=31))
        publicador = Publicador()
        rotina = RotinaApuracao(
            2026,
            1,
            "presidente",
            "ID",
            tmp_path,
            coletor=coletor,
            coletor_factory=lambda coletor=coletor: coletor,
            planilha=publicador,
            presidente_por_uf=True,
        )
        rotina._contextos = fontes
        monkeypatch.setattr(rotina._limite, "aguardar", lambda: None)
        try:
            rotina.run()
            assert len(publicador.lotes[0][1].linhas) == indice + 2
        finally:
            rotina.close()
