from datetime import datetime

from .modelo import Candidato, Resultado
from .planilha import TabelaPlanilha


def percentual(valor: int, total: int) -> str:
    return f"{100 * (valor / total):02.02f}%" if total else ""


def dados_legados(resultado: Resultado) -> dict:
    """Ponte temporária para preservar as tabelas publicadas em 2022."""
    candidatos = [
        {
            "candidato": candidato.nome_urna,
            "vice": candidato.vice,
            "numero": candidato.numero,
            "votos_apurados": candidato.votos,
            "perc": f"{candidato.percentual * 100:02.02f}%",
            "dif. próx.": (
                candidato.votos - resultado.candidatos[indice + 1].votos
                if indice + 1 < len(resultado.candidatos)
                else None
            ),
        }
        for indice, candidato in enumerate(resultado.candidatos)
    ]
    atualizado = str(resultado.gerada_em)
    return {
        "updated_at": atualizado,
        "eleitorado": resultado.eleitorado.total,
        "eleitorado_apurado": resultado.eleitorado.apurado,
        "secoes": resultado.secoes.total,
        "secoes_apuradas": resultado.secoes.apuradas,
        "total_nulos": resultado.votos.nulos,
        "total_brancos": resultado.votos.brancos,
        "total_validos": resultado.votos.validos,
        "total_votos": resultado.votos.total,
        "apuracao": candidatos,
        "title": (
            f"[{percentual(resultado.secoes.apuradas, resultado.secoes.total)}] "
            f"Apuração Eleições {resultado.contexto.ano} (atualizado: {atualizado})"
        ),
    }


def linhas_resultado(resultado: Resultado) -> list[list]:
    data = dados_legados(resultado)
    header = ["candidato", "vice", "numero", "votos_apurados", "perc", "dif. próx."]
    lines = [header] + [[row[field] for field in header] for row in data["apuracao"]]
    lines.extend([[], [], [], [], []])
    lines.append(["Eleitorado apurado", "Eleitorado total", "Percentual"])
    lines.append(
        [data["eleitorado_apurado"], data["eleitorado"], percentual(data["eleitorado_apurado"], data["eleitorado"])]
    )
    lines.append(["Seções apuradas", "Seções totais", "Percentual"])
    lines.append([data["secoes_apuradas"], data["secoes"], percentual(data["secoes_apuradas"], data["secoes"])])
    lines.append(["Votos válidos", "(%)", "Nulos", "(%)", "Brancos", "(%)", "Totais"])
    lines.append(
        [
            data["total_validos"],
            percentual(data["total_validos"], data["total_votos"]),
            data["total_nulos"],
            percentual(data["total_nulos"], data["total_votos"]),
            data["total_brancos"],
            percentual(data["total_brancos"], data["total_votos"]),
            data["total_votos"],
        ]
    )
    return lines


def tabela_resultado(resultado: Resultado, nome: str) -> TabelaPlanilha:
    candidatos = sorted(resultado.candidatos, key=lambda candidato: (-candidato.votos, candidato.numero))
    linhas = [["candidato", "vice", "numero", "votos_apurados", "perc", "dif. próx."]]
    for indice, candidato in enumerate(candidatos):
        diferenca = candidato.votos - candidatos[indice + 1].votos if indice + 1 < len(candidatos) else None
        linhas.append(
            [
                candidato.nome_urna,
                candidato.vice,
                candidato.numero,
                candidato.votos if resultado.divulgacao_liberada else None,
                (
                    float(candidato.percentual)
                    if resultado.divulgacao_liberada and candidato.percentual is not None
                    else None
                ),
                diferenca if resultado.divulgacao_liberada else None,
            ]
        )
    linhas.extend(
        [
            [],
            ["Atualização do TSE", str(resultado.gerada_em)],
            ["Identificador da geração", resultado.geracao],
            ["Eleição", resultado.contexto.eleicao, "Turno", resultado.contexto.turno],
            ["Divulgação", "Liberada" if resultado.divulgacao_liberada else "Aguardando liberação pelo TSE"],
            [
                "Eleitorado de seções apuradas",
                resultado.eleitorado.apurado,
                "Eleitorado total",
                resultado.eleitorado.total,
            ],
            [
                "Seções totalizadas",
                resultado.secoes.totalizadas,
                "Seções totais",
                resultado.secoes.total,
                "% Seções totalizadas",
                (
                    float(resultado.secoes.percentual_totalizadas)
                    if resultado.secoes.percentual_totalizadas is not None
                    else (
                        resultado.secoes.totalizadas / resultado.secoes.total
                        if resultado.secoes.totalizadas is not None and resultado.secoes.total
                        else None
                    )
                ),
            ],
            [
                "Seções apuradas",
                resultado.secoes.apuradas,
                None,
                None,
                "% Seções apuradas / total",
                resultado.secoes.apuradas / resultado.secoes.total if resultado.secoes.total else None,
            ],
            ["Andamento da totalização", resultado.andamento],
            ["Totalização final", resultado.finalizada],
            ["Matematicamente definida", resultado.matematicamente_definida],
        ]
    )
    if resultado.origem == "soma-ufs":
        linhas.extend(
            [
                ["Origem", "Soma de 27 UFs + exterior, não consolidado nacional do TSE"],
                ["Horário da coleta", str(resultado.capturada_em) if resultado.capturada_em else None],
                ["Fonte mais antiga", str(resultado.fontes_desde)],
                ["Fonte mais recente", str(resultado.fontes_ate)],
            ]
        )
    if resultado.divulgacao_liberada:
        linhas.extend(
            [
                ["Votos válidos", resultado.votos.validos],
                ["Votos nulos", resultado.votos.nulos],
                ["Votos brancos", resultado.votos.brancos],
                ["Votos anulados", resultado.votos.anulados],
                ["Votos anulados sub judice", resultado.votos.anulados_sub_judice],
                ["Votos a concorrentes", resultado.votos.concorrentes],
                ["Total de votos", resultado.votos.total],
            ]
        )
    return TabelaPlanilha(nome, linhas, (4,))


def _identidade(candidato: Candidato) -> str:
    return candidato.sequencial or candidato.numero


def tabela_historico(resultados: list[Resultado]) -> TabelaPlanilha:
    if len({resultado.contexto for resultado in resultados}) > 1:
        raise ValueError("O histórico não pode misturar contextos eleitorais")
    ordenados = sorted(resultados, key=hora_historico)
    candidatos = {}
    for resultado in ordenados:
        for candidato in resultado.candidatos:
            candidatos.setdefault(_identidade(candidato), candidato)
    identidades = sorted(
        candidatos,
        key=lambda identidade: (
            {"13": 0, "22": 1}.get(candidatos[identidade].numero, 2),
            candidatos[identidade].numero,
            identidade,
        ),
    )
    historico_2022 = bool(ordenados) and ordenados[0].contexto.ano == 2022
    rotulo = "% Seções apuradas" if historico_2022 else "% Seções totalizadas"
    linhas = [
        ["Data/Hora", rotulo]
        + [f"% {candidatos[identidade].nome_urna} ({candidatos[identidade].numero})" for identidade in identidades]
    ]
    vistos = set()
    for resultado in ordenados:
        chave = resultado.geracao or resultado.gerada_em
        if chave in vistos:
            continue
        vistos.add(chave)
        percentuais = {
            _identidade(candidato): float(candidato.percentual) if candidato.percentual is not None else None
            for candidato in resultado.candidatos
        }
        totalizadas = resultado.secoes.percentual_totalizadas
        if historico_2022 and resultado.secoes.total:
            totalizadas = resultado.secoes.apuradas / resultado.secoes.total
        linhas.append(
            [
                data_planilha(hora_historico(resultado)),
                float(totalizadas) if totalizadas is not None else None,
            ]
            + [percentuais.get(identidade) if resultado.divulgacao_liberada else None for identidade in identidades]
        )
    return TabelaPlanilha("LinhaDoTempo", linhas, tuple(range(1, len(linhas[0]))))


def titulo_resultado(resultado: Resultado) -> str:
    """Usa o progresso disponível na fonte, sem confundir apuradas e totalizadas."""
    if resultado.contexto.ano == 2022:
        progresso = resultado.secoes.apuradas / resultado.secoes.total if resultado.secoes.total else None
    else:
        progresso = resultado.secoes.percentual_totalizadas
        if progresso is None and resultado.secoes.totalizadas is not None and resultado.secoes.total:
            progresso = resultado.secoes.totalizadas / resultado.secoes.total
    prefixo = f"[{progresso * 100:.2f}%] " if progresso is not None else ""
    horario = hora_historico(resultado)
    rotulo = "coletado" if resultado.origem == "soma-ufs" else "atualizado"
    origem = " - soma UFs + exterior" if resultado.origem == "soma-ufs" else ""
    return f"{prefixo}Apuração Eleições {resultado.contexto.ano}{origem} ({rotulo}: {horario})"


def data_planilha(data: datetime) -> float:
    """Serial local do Sheets: conserva o dia, mas permite mostrar apenas HH:mm:ss."""
    local = data.replace(tzinfo=None)
    return (local - datetime(1899, 12, 30)).total_seconds() / 86400  # noqa: DTZ001


def hora_historico(resultado: Resultado) -> datetime:
    return resultado.capturada_em if resultado.origem == "soma-ufs" and resultado.capturada_em else resultado.gerada_em
