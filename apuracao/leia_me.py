"""Autoria, fontes e interpretação da planilha, sem pressupor cadência da publicação do TSE."""

import argparse
import os
import sys
from pathlib import Path

from .configuracao import codigo_eleicao, contextos_eleicao, url_municipios, url_resultado
from .modelo import Contexto
from .planilha import Planilha, TabelaPlanilha

CATALOGO = "https://www.tse.jus.br/eleicoes/eleicoes-2026-content/arquivos/divulgacao-de-resultados"
EA20 = CATALOGO + "/tse-ea20-arquivo-de-resultado-unificado/@@download/file"


def tabela_leia_me(
    ano: int,
    turno: int,
    *,
    intervalo_presidente: float | None = None,
    intervalo_ufs: float | None = None,
    governadores: list[Contexto] | None = None,
) -> TabelaPlanilha:
    if ano == 2026 and turno == 2 and not governadores:
        raise ValueError("O segundo turno exige as abrangências de governador publicadas no EA11")
    if governadores is not None and any(
        contexto.ano != ano or contexto.turno != turno or contexto.cargo != 3 for contexto in governadores
    ):
        raise ValueError("Contextos de governador incompatíveis com a edição")
    exemplo = (
        "sp"
        if not governadores or any(item.abrangencia == "sp" for item in governadores)
        else min(item.abrangencia for item in governadores)
    )
    if ano == 2026:
        codigo_presidente, codigo_estadual = (6257, 6259) if turno == 1 else (6258, 6260)
        presidente = url_resultado(Contexto(ano, turno, codigo_presidente, 1, "br"))
        governador = url_resultado(
            next(item for item in governadores if item.abrangencia == exemplo)
            if governadores
            else Contexto(ano, turno, codigo_estadual, 3, exemplo)
        )
    else:
        presidente = url_resultado(contextos_eleicao({}, ano, turno, 1)[0])
        governador = url_resultado(
            next(item for item in contextos_eleicao({}, ano, turno, 3) if item.abrangencia == "sp")
        )
    exemplo_presidente_uf = presidente.replace("/br/", "/sp/").replace("/br-c", "/sp-c")
    frequencia = "Configurável no gerenciador; consulte os parâmetros da execução."
    if intervalo_presidente is not None and intervalo_ufs is not None:
        frequencia = f"{intervalo_presidente:g}s (presidente), {intervalo_ufs:g}s (governador)"
    linhas = [
        ["Desenvolvido por:", "Álvaro Justen"],
        ["Código-fonte:", "https://github.com/turicas/eleicoes-brasil"],
        ["Twitter:", "https://twitter.com/turicas"],
        ["Bluesky:", "https://bsky.app/profile/turicas.bsky.social"],
        ["Edição:", f"Eleições {ano}, {turno}º turno"],
        ["Fonte dos dados (presidente nacional):", presidente],
        [f"Fonte dos dados (governador - ex. {exemplo.upper()}):", governador],
        [
            "Fonte dos dados (presidente por UF):",
            f"Mesmo padrão do nacional, substituindo br pela sigla da UF; exterior: zz. Exemplo (SP): {exemplo_presidente_uf}",
        ],
        ["Configuração das eleições:", "https://resultados.tse.jus.br/oficial/comum/config/ele-c.json"],
        ["Dicionário de dados:", EA20 if ano == 2026 else "Leiaute histórico de 2022; consulte o código-fonte."],
        [
            "Detalhes sobre divulgação de dados:",
            (
                "https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados"
                if ano == 2026
                else "https://www.tse.jus.br/eleicoes/eleicoes-2022/interessados-na-divulgacao-de-resultados-2022"
            ),
        ],
        ["Consulta a cada:", frequencia],
        ["Atualização dos dados:", "Somente quando muda na origem."],
        [
            "Atualização inteligente de presidente:",
            "Compara o nacional com a soma das 27 UFs + exterior; escolhe maior cobertura de seções totalizadas, nacional em empate (evita longas demoras para atualização).",
        ],
        [
            "Origem dos resultados:",
            'A soma por UF é uma agregação própria de fontes de horários distintos, não o consolidado nacional oficial. A origem (se foi usado o dado consolidado nacional ou a consolidação por UF) fica na coluna "Origem" da aba LinhaDoTempo.',
        ],
        [
            "Horários:",
            "Se a origem for o nacional consolidado, é o horário de geração do TSE; se for a soma das UFs, é o horário da coleta.",
        ],
        ["Abas das UFs:", "Resultados de governador (não são os votos presidenciais por UF)."],
        ["Cor da aba de UF verde:", "Eleito matematicamente definido."],
        ["Cor da aba de UF azul:", "Segundo turno matematicamente definido."],
        ["Cor da aba de UF preta:", "Ainda sem definição matemática."],
        ["Asterisco no nome da UF:", "Totalização final informada pelo TSE (tf=s); não basta ter 100% das seções."],
        [
            "Eleitorado que falta apurar:",
            (
                "Em 2026: eleitorado das seções não totalizadas (e.esnt). Não é quantidade de votos garantidos e não inclui seções não instaladas já totalizadas."
                if ano == 2026
                else "Eleitorado total menos eleitorado de seções apuradas, conforme o formato histórico de 2022."
            ),
        ],
    ]
    if ano == 2026:
        linhas.append(
            [
                "PresidentePorUF:",
                "Votos presidenciais e cobertura das 27 UFs e do exterior (ZZ), em ordem alfabética por região e sigla. Atualiza pelas fontes regionais mesmo quando o nacional é escolhido. Urnas apuradas são seções apuradas do TSE (s.sa).",
            ]
        )
    if governadores:
        linhas.append(
            ["Governos acompanhados:", ", ".join(sorted({item.abrangencia.upper() for item in governadores}))]
        )
    return TabelaPlanilha("LEIA-ME", linhas, indice=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ano", type=int, choices=(2022, 2026))
    parser.add_argument("turno", type=int, choices=(1, 2))
    parser.add_argument("planilha")
    parser.add_argument("--intervalo-presidente", type=float)
    parser.add_argument("--intervalo-ufs", type=float)
    args = parser.parse_args(argv)
    try:
        import gspread

        credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or str(
            Path(__file__).parent / "credentials" / f"eleicoes-{args.ano}-brasil-io-sheets.json"
        )
        client = gspread.service_account(filename=credentials, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        governadores = None
        if args.ano == 2026:
            from .acompanhamento import URL_CONFIGURACAO
            from .coleta import Coletor

            coletor = Coletor(Path(__file__).parent / "data", timeout=10, tentativas=1)
            try:
                configuracao = coletor.buscar_json(URL_CONFIGURACAO)
                codigo = codigo_eleicao(configuracao, args.ano, args.turno, 3)
                municipios = coletor.buscar_json(url_municipios(args.ano, codigo, configuracao.get("arq")))
                governadores = contextos_eleicao(configuracao, args.ano, args.turno, 3, municipios)
            finally:
                coletor.session.close()
        tabela = tabela_leia_me(
            args.ano,
            args.turno,
            intervalo_presidente=args.intervalo_presidente,
            intervalo_ufs=args.intervalo_ufs,
            governadores=governadores,
        )
        Planilha(client, args.planilha, args.ano, args.turno).publicar([tabela])
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as erro:  # noqa: BLE001 - fronteira CLI com diagnóstico
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
