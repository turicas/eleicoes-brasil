import html
import re
from decimal import Decimal, InvalidOperation

from .base import Apuracao
from .modelo import Candidato, Eleitorado, Resultado, Secoes, Votos


class Apuracao2026(Apuracao):
    ano = 2026

    def _inteiro(self, valor, campo: str) -> int:
        if isinstance(valor, bool) or not isinstance(valor, (str, int)) or not re.fullmatch(r"[0-9]+", str(valor)):
            self._erro(campo, "esperado inteiro não negativo")
        return int(valor)

    def _numero(self, dados: dict, chave: str, caminho: str, opcional: bool = False) -> int | None:
        if opcional and dados.get(chave) is None:
            return None
        return self._inteiro(self._campo(dados, chave, caminho), caminho)

    def _percentual(self, dados: dict, chave: str, caminho: str, opcional: bool = False) -> Decimal | None:
        chave_usada = chave + "n" if dados.get(chave + "n") is not None else chave
        campo = f"{caminho}.{chave_usada}"
        if opcional and dados.get(chave_usada) is None:
            return None
        valor = self._campo(dados, chave_usada, campo)
        if isinstance(valor, bool) or not isinstance(valor, (str, int, float, Decimal)):
            self._erro(campo, "esperado percentual decimal")
        try:
            percentual = Decimal(str(valor).replace(",", "."))
        except InvalidOperation as erro:
            raise ValueError(
                f"{campo}: percentual inválido (eleicao={self.contexto.eleicao}, abrangencia={self.contexto.abrangencia})"
            ) from erro
        if not percentual.is_finite() or not 0 <= percentual <= 100:
            self._erro(campo, "percentual fora do intervalo 0 a 100")
        return percentual / 100

    def _texto(self, dados: dict, chave: str, caminho: str, opcional: bool = False) -> str | None:
        if opcional and dados.get(chave) is None:
            return None
        valor = self._campo(dados, chave, caminho)
        if not isinstance(valor, str):
            self._erro(caminho, "esperado texto")
        return html.unescape(valor)

    def _lista(self, dados: dict, chave: str, caminho: str, opcional: bool = False) -> list[dict]:
        valor = dados.get(chave, []) if opcional else self._campo(dados, chave, caminho)
        if not isinstance(valor, list) or any(not isinstance(item, dict) for item in valor):
            self._erro(caminho, "esperada lista de objetos")
        return valor

    def _estado(self, dados: dict, chave: str, permitidos: str, opcional: bool = False) -> str | None:
        if opcional and dados.get(chave) is None:
            return None
        valor = self._campo(dados, chave, chave)
        if valor not in tuple(permitidos):
            self._erro(chave, f"esperado um de {permitidos}")
        return valor

    def ler(self, dados: dict) -> Resultado:
        if self._campo(dados, "f", "f") != "o":
            self._erro("f", "apenas resultados oficiais são aceitos")
        for campo, esperado in (("ele", self.contexto.eleicao), ("t", self.contexto.turno)):
            if self._numero(dados, campo, campo) != esperado:
                self._erro(campo, f"esperado {esperado}")
        for campo, esperado in (
            ("tpabr", "br" if self.contexto.abrangencia == "br" else "uf"),
            ("cdabr", self.contexto.abrangencia),
        ):
            if self._campo(dados, campo, campo) != esperado:
                self._erro(campo, f"esperado {esperado}")
        cargos = self._lista(dados, "carg", "carg")
        if len(cargos) != 1 or self._numero(cargos[0], "cd", "carg.cd") != self.contexto.cargo:
            self._erro("carg.cd", f"esperado cargo {self.contexto.cargo}")
        candidatos = []
        for indice_agr, agrupamento in enumerate(self._lista(cargos[0], "agr", "carg.agr")):
            caminho_agr = f"carg.agr[{indice_agr}]"
            for indice_par, partido in enumerate(self._lista(agrupamento, "par", f"{caminho_agr}.par")):
                caminho_par = f"{caminho_agr}.par[{indice_par}]"
                sigla = self._texto(partido, "sg", f"{caminho_par}.sg")
                for indice_cand, candidato in enumerate(self._lista(partido, "cand", f"{caminho_par}.cand")):
                    caminho = f"{caminho_par}.cand[{indice_cand}]"
                    vice = None
                    for suplente in self._lista(candidato, "vs", f"{caminho}.vs", opcional=True):
                        if self._campo(suplente, "tp", f"{caminho}.vs.tp") == "v":
                            vice = self._texto(suplente, "nm", f"{caminho}.vs.nm")
                            break
                    numero = self._campo(candidato, "n", f"{caminho}.n")
                    self._inteiro(numero, f"{caminho}.n")
                    sequencial = self._numero(candidato, "sqcand", f"{caminho}.sqcand", opcional=True)
                    candidatos.append(
                        Candidato(
                            numero=str(numero),
                            nome=self._texto(candidato, "nm", f"{caminho}.nm"),
                            nome_urna=self._texto(candidato, "nmu", f"{caminho}.nmu"),
                            vice=vice,
                            votos=self._numero(candidato, "vap", f"{caminho}.vap"),
                            percentual=self._percentual(candidato, "pvap", caminho),
                            sequencial=str(sequencial) if sequencial is not None else None,
                            partido=sigla,
                            destinacao=self._texto(candidato, "dvt", f"{caminho}.dvt", opcional=True),
                            situacao=self._texto(candidato, "st", f"{caminho}.st", opcional=True),
                        )
                    )
        grupos = {}
        for chave in ("s", "e", "v"):
            grupo = self._campo(dados, chave, chave)
            if not isinstance(grupo, dict):
                self._erro(chave, "esperado objeto")
            grupos[chave] = grupo
        secoes, eleitorado, votos = grupos["s"], grupos["e"], grupos["v"]
        geracao = self._numero(dados, "idg", "idg", opcional=True)
        finalizada = self._estado(dados, "tf", "sn", opcional=True)
        return Resultado(
            contexto=self.contexto,
            gerada_em=self._data(dados, "dg", "hg"),
            secoes=Secoes(
                total=self._numero(secoes, "ts", "s.ts"),
                apuradas=self._numero(secoes, "sa", "s.sa"),
                totalizadas=self._numero(secoes, "st", "s.st", opcional=True),
                percentual_totalizadas=self._percentual(secoes, "pst", "s", opcional=True),
                percentual_apuradas=self._percentual(secoes, "psa", "s", opcional=True),
            ),
            eleitorado=Eleitorado(
                self._numero(eleitorado, "te", "e.te"),
                self._numero(eleitorado, "esa", "e.esa"),
                self._numero(eleitorado, "esnt", "e.esnt", opcional=True),
                instalado=self._numero(eleitorado, "esi", "e.esi", opcional=True),
                abstencoes=self._numero(eleitorado, "a", "e.a", opcional=True),
            ),
            votos=Votos(
                total=self._numero(votos, "tv", "v.tv"),
                validos=self._numero(votos, "vv", "v.vv"),
                nulos=self._numero(votos, "tvn", "v.tvn"),
                brancos=self._numero(votos, "vb", "v.vb"),
                concorrentes=self._numero(votos, "vvc", "v.vvc", opcional=True),
                anulados=self._numero(votos, "van", "v.van", opcional=True),
                anulados_sub_judice=self._numero(votos, "vansj", "v.vansj", opcional=True),
            ),
            candidatos=tuple(candidatos),
            geracao=str(geracao) if geracao is not None else None,
            totalizada_em=self._data(dados, "dt", "ht", opcional=True),
            divulgacao_liberada=self._estado(dados, "dv", "sn") == "s",
            andamento=self._estado(dados, "and", "npf", opcional=True),
            finalizada=finalizada == "s" if finalizada is not None else None,
            matematicamente_definida=self._estado(dados, "md", "esn", opcional=True),
        )
