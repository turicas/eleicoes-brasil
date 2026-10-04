import argparse
import sys

URL_CONFIGURACAO = "https://resultados.tse.jus.br/oficial/comum/config/ele-c.json"


def _caminho(valor: str):
    from pathlib import Path

    return Path(valor)


def cria_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta a apuração oficial e prepara uma planilha existente.")
    parser.add_argument("ano", type=int, choices=(2022, 2026))
    parser.add_argument("turno", type=int, choices=(1, 2))
    parser.add_argument("tipo", choices=("presidente", "governador"))
    parser.add_argument("planilha", nargs="?", metavar="ID", help="ID da planilha; obrigatório sem --print-only")
    parser.add_argument(
        "--print-only", action="store_true", help="Emite JSON sem acessar Google; salva brutos localmente"
    )
    parser.add_argument("--data-path", type=_caminho, default=None, metavar="DIR")
    parser.add_argument(
        "--uf",
        choices=(
            "AC",
            "AL",
            "AM",
            "AP",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MG",
            "MS",
            "MT",
            "PA",
            "PB",
            "PE",
            "PI",
            "PR",
            "RJ",
            "RN",
            "RO",
            "RR",
            "RS",
            "SC",
            "SE",
            "SP",
            "TO",
        ),
        type=str.upper,
        help="Restringe a atualização de governador a uma UF",
    )
    return parser


def executar(args, *, coletor=None, client=None) -> int:
    import json
    import os
    from dataclasses import asdict
    from pathlib import Path

    from .adaptador2022 import Apuracao2022
    from .adaptador2026 import Apuracao2026
    from .apresentacao import tabela_historico, tabela_resultado, titulo_resultado
    from .coleta import Coletor
    from .configuracao import contextos_eleicao, url_municipios, url_resultado
    from .planilha import Planilha

    if not args.print_only and not args.planilha:
        raise ValueError("Informe o ID da planilha ou use --print-only")
    if args.uf and args.tipo != "governador":
        raise ValueError("--uf só se aplica a governador")
    if coletor is None:
        coletor = Coletor(args.data_path or Path(__file__).parent / "data")
    cargo = 1 if args.tipo == "presidente" else 3
    configuracao = coletor.buscar_json(URL_CONFIGURACAO) if args.ano == 2026 else {}
    diretorios = configuracao.get("arq") or None
    municipios = None
    if args.ano == 2026 and cargo == 3:
        from .configuracao import codigo_eleicao

        codigo = codigo_eleicao(configuracao, args.ano, args.turno, cargo)
        municipios = coletor.buscar_json(url_municipios(args.ano, codigo, diretorios))
    contextos = contextos_eleicao(configuracao, args.ano, args.turno, cargo, municipios)
    if args.uf:
        contextos = [contexto for contexto in contextos if contexto.abrangencia == args.uf.lower()]
        if not contextos:
            raise ValueError(f"Não há disputa de governador para {args.uf} neste turno")
    classe = Apuracao2022 if args.ano == 2022 else Apuracao2026
    resultados = []
    tabelas = []
    falhou = False
    for contexto in contextos:
        adaptador = classe(contexto)
        try:
            resultado = coletor.coletar(contexto, adaptador, url_resultado(contexto, diretorios))
            nome = "Presidente" if cargo == 1 else contexto.abrangencia.upper()
            tabelas_contexto = [tabela_resultado(resultado, nome)]
            if cargo == 1:
                tabelas_contexto.append(tabela_historico(coletor.historico(contexto, adaptador)))
        except KeyboardInterrupt:
            raise
        except (ValueError, OSError, KeyError) as erro:
            if cargo == 1:
                raise
            print(f"Falha em {contexto.abrangencia.upper()}: {erro}", file=sys.stderr)
            falhou = True
            continue
        resultados.append(resultado)
        tabelas.extend(tabelas_contexto)
    if args.print_only:
        print(json.dumps([asdict(resultado) for resultado in resultados], default=str, ensure_ascii=False, indent=2))
    elif tabelas:
        if client is None:
            import gspread

            credenciais = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if not credenciais:
                raise ValueError("Defina GOOGLE_APPLICATION_CREDENTIALS com o caminho do arquivo da conta de serviço")
            client = gspread.service_account(
                filename=credenciais, scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
        titulo = titulo_resultado(resultados[0]) if cargo == 1 else None
        Planilha(client, args.planilha, args.ano, args.turno).publicar(tabelas, titulo=titulo)
    return 1 if falhou else 0


def main(argv: list[str] | None = None) -> int:
    parser = cria_parser()
    args = parser.parse_args(argv)
    if not args.print_only and not args.planilha:
        print("Informe o ID da planilha ou use --print-only", file=sys.stderr)
        return 2
    try:
        return executar(args)
    except KeyboardInterrupt:
        print("Apuração interrompida", file=sys.stderr)
        return 130
    except Exception as erro:  # noqa: BLE001 - fronteira da CLI: diagnóstico e código de saída
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
