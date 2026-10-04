from dataclasses import replace

from apuracao.acompanhamento import RotinaApuracao
from apuracao.adaptador2022 import Apuracao2022
from apuracao.modelo import Contexto


def test_agregado_preserva_historico_nacional(dados_2022, tmp_path):
    nacional = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    nacional = replace(nacional, contexto=Contexto(2026, 1, 6257, 1, "br"), geracao="nacional")
    agregado = replace(nacional, origem="soma-ufs", geracao="ufs-nova", gerada_em=nacional.gerada_em.replace(minute=31))

    class Coletor:
        def historico(self, contexto, adaptador):
            assert contexto.abrangencia == "br"
            return [nacional]

    rotina = RotinaApuracao(
        2026, 1, "presidente", "ID", tmp_path, coletor=Coletor(), planilha=object(), presidente_por_uf=True
    )
    rotina._ler_historico_somas = lambda: [agregado]
    rotina._registrar_historico(agregado)
    assert rotina._historico == [nacional, agregado]


def test_nacional_tambem_preserva_historico_agregado(dados_2022, tmp_path):
    nacional = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    nacional = replace(nacional, contexto=Contexto(2026, 1, 6257, 1, "br"), geracao="nacional")
    agregado = replace(nacional, origem="soma-ufs", geracao="ufs-nova", gerada_em=nacional.gerada_em.replace(minute=31))

    class Coletor:
        def historico(self, contexto, adaptador):
            return [nacional]

    rotina = RotinaApuracao(2026, 1, "presidente", "ID", tmp_path, coletor=Coletor(), planilha=object())
    rotina._ler_historico_somas = lambda: [agregado]
    rotina._registrar_historico(nacional)
    assert {item.geracao for item in rotina._historico} == {"nacional", "ufs-nova"}
