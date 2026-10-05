"""Soma fontes oficiais por UF, sem atribuir caráter oficial à consolidação."""

import json
from dataclasses import fields, replace
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from .formatacao import UFS
from .modelo import Candidato, Contexto, Eleitorado, Resultado, Secoes, Votos

_ABRANGENCIAS = frozenset(uf.lower() for uf in UFS) | {"zz"}


def _soma(valores: list[int | None]) -> int | None:
    return None if any(valor is None for valor in valores) else sum(valores)


def _percentual(numerador: int | None, denominador: int | None) -> Decimal | None:
    if numerador is None or not denominador:
        return None
    return Decimal(numerador) / Decimal(denominador)


def _identidade(candidato: Candidato) -> tuple[str, str]:
    if candidato.sequencial is not None:
        return "sequencial", candidato.sequencial
    return "numero", candidato.numero


def _candidatos(resultados: list[Resultado], concorrentes: int | None) -> tuple[Candidato, ...]:
    grupos: dict[tuple[str, str], list[Candidato]] = {}
    conjunto = None
    for resultado in resultados:
        candidatos = {_identidade(candidato): candidato for candidato in resultado.candidatos}
        if len(candidatos) != len(resultado.candidatos):
            raise ValueError(f"candidatos: identidade duplicada em {resultado.contexto.abrangencia}")
        numeros = {candidato.numero for candidato in resultado.candidatos}
        if len(numeros) != len(candidatos):
            raise ValueError(f"candidatos: número duplicado em {resultado.contexto.abrangencia}")
        if conjunto is None:
            conjunto = set(candidatos)
        elif set(candidatos) != conjunto:
            raise ValueError(f"candidatos: conjunto de identidades divergente em {resultado.contexto.abrangencia}")
        for identidade, candidato in candidatos.items():
            grupos.setdefault(identidade, []).append(candidato)

    agregados = []
    for identidade in sorted(grupos):
        fontes = grupos[identidade]
        metadados = {}
        for campo in ("numero", "nome", "nome_urna", "vice", "partido"):
            valores = {getattr(candidato, campo) for candidato in fontes if getattr(candidato, campo) is not None}
            if len(valores) > 1:
                raise ValueError(f"candidatos.{campo}: valores divergentes para {identidade}")
            metadados[campo] = next(iter(valores), None)
        destinacoes = {candidato.destinacao for candidato in fontes}
        votos = sum(candidato.votos for candidato in fontes)
        agregados.append(
            replace(
                fontes[0],
                **metadados,
                votos=votos,
                percentual=_percentual(votos, concorrentes),
                destinacao=next(iter(destinacoes)) if len(destinacoes) == 1 else None,
                situacao=None,
            )
        )
    return tuple(agregados)


def somar_presidente(resultados: list[Resultado]) -> Resultado:
    """Exige 27 UFs e exterior compatíveis; ausência opcional não é zero nem declaração de eleito."""
    abrangencias = [resultado.contexto.abrangencia for resultado in resultados]
    if len(abrangencias) != len(_ABRANGENCIAS) or set(abrangencias) != _ABRANGENCIAS:
        raise ValueError("abrangencia: exigidas exatamente as 27 UFs em minúsculas e zz, sem duplicatas")
    fontes = sorted(resultados, key=lambda resultado: resultado.contexto.abrangencia)
    contexto = fontes[0].contexto
    for resultado in fontes:
        atual = resultado.contexto
        if atual.ano != 2026:
            raise ValueError("ano: a soma exige 2026")
        if atual.turno not in (1, 2) or atual.turno != contexto.turno:
            raise ValueError("turno: exigido o mesmo turno, 1 ou 2")
        if atual.cargo != 1:
            raise ValueError("cargo: a soma exige presidente (1)")
        if atual.eleicao != contexto.eleicao:
            raise ValueError("eleicao: exigida a mesma eleição em todas as fontes")
        if resultado.origem != "tse":
            raise ValueError("origem: exigidas fontes oficiais já interpretadas, não agregações")

    secoes_total = sum(resultado.secoes.total for resultado in fontes)
    secoes_apuradas = sum(resultado.secoes.apuradas for resultado in fontes)
    secoes_totalizadas = _soma([resultado.secoes.totalizadas for resultado in fontes])
    votos = Votos(
        **{campo.name: _soma([getattr(resultado.votos, campo.name) for resultado in fontes]) for campo in fields(Votos)}
    )
    candidatos = _candidatos(fontes, votos.concorrentes)
    desde = min(resultado.gerada_em for resultado in fontes)
    ate = max(resultado.gerada_em for resultado in fontes)
    identificadores = [
        [resultado.contexto.abrangencia, resultado.geracao, resultado.gerada_em.isoformat()] for resultado in fontes
    ]
    geracao = "ufs-" + sha256(json.dumps(identificadores, ensure_ascii=False).encode("utf-8")).hexdigest()
    estados = {resultado.andamento for resultado in fontes}
    andamento = "f" if estados == {"f"} else "n" if estados <= {"n", None} else "p"
    return Resultado(
        contexto=Contexto(2026, contexto.turno, contexto.eleicao, 1, "br"),
        gerada_em=ate,
        secoes=Secoes(
            total=secoes_total,
            apuradas=secoes_apuradas,
            totalizadas=secoes_totalizadas,
            percentual_totalizadas=_percentual(secoes_totalizadas, secoes_total),
            percentual_apuradas=_percentual(secoes_apuradas, secoes_total),
        ),
        eleitorado=Eleitorado(
            total=sum(resultado.eleitorado.total for resultado in fontes),
            apurado=sum(resultado.eleitorado.apurado for resultado in fontes),
            nao_totalizado=_soma([resultado.eleitorado.nao_totalizado for resultado in fontes]),
        ),
        votos=votos,
        candidatos=candidatos,
        geracao=geracao,
        totalizada_em=None,
        divulgacao_liberada=all(resultado.divulgacao_liberada is True for resultado in fontes),
        andamento=andamento,
        finalizada=None,
        matematicamente_definida=None,
        origem="soma-ufs",
        fontes_desde=desde,
        fontes_ate=ate,
    )


def fontes_salvas(dados: list[dict]) -> list[Resultado]:
    """Restaura somente o formato de domínio persistido das fontes, não JSONs arbitrários do TSE."""
    resultados = []
    for item in dados:
        item = dict(item)
        for campo in ("gerada_em", "totalizada_em", "fontes_desde", "fontes_ate", "capturada_em"):
            if item.get(campo) is not None:
                item[campo] = datetime.fromisoformat(item[campo])
        item["contexto"] = Contexto(**item["contexto"])
        item["eleitorado"] = Eleitorado(**item["eleitorado"])
        item["votos"] = Votos(**item["votos"])
        secoes = item["secoes"]
        for campo in ("percentual_totalizadas", "percentual_apuradas"):
            if secoes.get(campo) is not None:
                secoes[campo] = Decimal(secoes[campo])
        item["secoes"] = Secoes(**secoes)
        candidatos = []
        for candidato in item["candidatos"]:
            if candidato.get("percentual") is not None:
                candidato["percentual"] = Decimal(candidato["percentual"])
            candidatos.append(Candidato(**candidato))
        item["candidatos"] = tuple(candidatos)
        resultados.append(Resultado(**item))
    return resultados
