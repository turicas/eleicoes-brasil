from .modelo import Resultado


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
