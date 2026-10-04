import html
from decimal import Decimal

from .base import Apuracao
from .modelo import Candidato, Eleitorado, Resultado, Secoes, Votos


class Apuracao2022(Apuracao):
    ano = 2022

    def ler(self, dados: dict) -> Resultado:
        for campo, esperado in (("ele", self.contexto.eleicao), ("t", self.contexto.turno), ("f", "o")):
            if campo in dados and str(dados[campo]) != str(esperado):
                self._erro(campo, f"esperado {esperado}")
        return Resultado(
            contexto=self.contexto,
            gerada_em=self._data(dados, "dg", "hg"),
            secoes=Secoes(int(dados["s"]), int(dados["sa"])),
            eleitorado=Eleitorado(int(dados["e"]), int(dados["ea"])),
            votos=Votos(int(dados["tv"]), int(dados["vv"]), int(dados["tvn"]), int(dados["vb"])),
            candidatos=tuple(
                Candidato(
                    numero=html.unescape(candidato["n"]),
                    nome=html.unescape(candidato["nm"]),
                    nome_urna=html.unescape(candidato["nm"]),
                    vice=html.unescape(candidato["nv"]),
                    votos=int(candidato["vap"]),
                    percentual=Decimal(candidato["pvap"].replace(",", ".")) / 100,
                )
                for candidato in dados["cand"]
            ),
        )
