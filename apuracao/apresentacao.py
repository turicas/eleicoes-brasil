from datetime import datetime

from .cor_aba import cor_resultado
from .formatacao import UFS, nome_canonico
from .modelo import Candidato, Resultado
from .planilha import TabelaPlanilha

_REGIOES_POR_UF = {
    sigla: regiao
    for regiao, siglas in (
        ("Centro-Oeste", ("DF", "GO", "MS", "MT")),
        ("Exterior", ("ZZ",)),
        ("Nordeste", ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE")),
        ("Norte", ("AC", "AM", "AP", "PA", "RO", "RR", "TO")),
        ("Sudeste", ("ES", "MG", "RJ", "SP")),
        ("Sul", ("PR", "RS", "SC")),
    )
    for sigla in siglas
}


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


def tabela_resultado(resultado: Resultado, nome: str, *, definicao_oficial: Resultado | None = None) -> TabelaPlanilha:
    definicao = definicao_oficial or resultado
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
                "Eleitorado que falta apurar",
                (
                    resultado.eleitorado.nao_totalizado
                    if resultado.contexto.ano == 2026
                    else resultado.eleitorado.total - resultado.eleitorado.apurado
                ),
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
            ["Totalização final", definicao.finalizada],
            ["Matematicamente definida", definicao.matematicamente_definida],
        ]
    )
    if definicao_oficial is not None:
        linhas.extend(
            [
                ["Fonte da definição", "JSON nacional do TSE"],
                ["Atualização da definição", str(definicao_oficial.gerada_em)],
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
    canonico = nome_canonico(nome)
    if canonico in UFS:
        nome = canonico + ("*" if resultado.finalizada is True else "")
    return TabelaPlanilha(nome, linhas, (4,), cor_resultado(definicao))


def tabela_presidente_por_uf(resultados: list[Resultado]) -> TabelaPlanilha:
    """Apresenta votos presidenciais e cobertura por região/UF; ausência e divisão por zero ficam vazias."""
    linhas = [
        [
            "Região",
            "UF",
            "Urnas\nApuradas",
            "Urnas\nTotais",
            "Urnas\nApuradas %",
            "Eleitorado\nApurado",
            "Eleitorado\nTotal",
            "Eleitorado\nApurado %",
            "% LULA",
            "% FLÁVIO",
            "Votos\nLULA",
            "Votos\nFLÁVIO",
            "Abstenção\nTotal",
            "Abstenção\n%",
            "Votos\nNulos",
            "Votos\nNulos %",
            "Votos\nBrancos",
            "Votos\nBrancos %",
        ]
    ]
    contexto = resultados[0].contexto if resultados else None
    vistos = set()
    for resultado in resultados:
        atual = resultado.contexto
        if (
            atual.ano != 2026
            or atual.cargo != 1
            or resultado.origem != "tse"
            or (atual.ano, atual.turno, atual.eleicao) != (contexto.ano, contexto.turno, contexto.eleicao)
        ):
            raise ValueError("Resultados por UF exigem o mesmo contexto presidencial oficial de 2026")
        sigla = atual.abrangencia.upper()
        if sigla not in _REGIOES_POR_UF:
            raise ValueError(f"Abrangência presidencial inválida: {sigla}")
        if sigla in vistos:
            raise ValueError(f"Abrangência presidencial duplicada: {sigla}")
        vistos.add(sigla)
        secoes = resultado.secoes
        eleitorado = resultado.eleitorado
        percentual_secoes = secoes.apuradas / secoes.total if secoes.total else None
        candidatos = {candidato.numero: candidato for candidato in resultado.candidatos}
        percentuais = []
        votos = []
        for numero in ("13", "22"):
            candidato = candidatos.get(numero)
            votos.append(candidato.votos if candidato is not None and resultado.divulgacao_liberada else None)
            percentual = None
            if candidato is not None and resultado.divulgacao_liberada and resultado.votos.validos:
                percentual = float(candidato.percentual) if candidato.percentual is not None else None
            percentuais.append(percentual)
        divulgada = resultado.divulgacao_liberada
        total_votos = resultado.votos.total
        nulos = resultado.votos.nulos if divulgada else None
        brancos = resultado.votos.brancos if divulgada else None
        linhas.append(
            [
                _REGIOES_POR_UF[sigla],
                sigla,
                secoes.apuradas,
                secoes.total,
                percentual_secoes,
                eleitorado.apurado,
                eleitorado.total,
                eleitorado.apurado / eleitorado.total if eleitorado.total else None,
                *percentuais,
                *votos,
                eleitorado.abstencoes,
                (
                    eleitorado.abstencoes / eleitorado.instalado
                    if eleitorado.abstencoes is not None and eleitorado.instalado
                    else None
                ),
                nulos,
                nulos / total_votos if nulos is not None and total_votos else None,
                brancos,
                brancos / total_votos if brancos is not None and total_votos else None,
            ]
        )
    linhas[1:] = sorted(linhas[1:], key=lambda linha: (linha[0], linha[1]))
    return TabelaPlanilha("PresidentePorUF", linhas, (4, 7, 8, 9, 13, 15, 17))


def _identidade(candidato: Candidato) -> str:
    return candidato.sequencial or candidato.numero


def tabela_historico(resultados: list[Resultado], *, incluir_origem: bool = False) -> TabelaPlanilha:
    """Monta a linha do tempo sem pontos sem votos válidos; preserva zeros legítimos dos candidatos."""
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
    if incluir_origem:
        linhas[0].append("Origem")
    vistos = set()
    for resultado in ordenados:
        if resultado.votos.validos == 0:
            continue
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
        if incluir_origem:
            linhas[-1].append("Soma UFs + exterior" if resultado.origem == "soma-ufs" else "Nacional TSE")
    limite_percentuais = len(linhas[0]) - int(incluir_origem)
    return TabelaPlanilha("LinhaDoTempo", linhas, tuple(range(1, limite_percentuais)))


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
