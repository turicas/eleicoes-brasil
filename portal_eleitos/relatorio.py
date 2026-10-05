"""Auditoria de completude por cargo, sem inferir eleitos quando a fonte não os informa."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .infra import salvar_json


def avaliar(cargo: dict) -> dict:
    vagas = cargo.get("vagas")
    quantidade = len(cargo["eleitos"])
    if cargo["fonte"]["estado_coleta"] != "sucesso":
        situacao, motivo = "atualizacao-falhou", cargo["fonte"].get("erro", "Usando última versão válida")
    elif cargo["estado"] == "pendente":
        situacao, motivo = "aguardando-tse", "TSE ainda não finalizou este resultado"
    elif cargo["estado"] == "segundo-turno":
        situacao, motivo = (
            "aguardando-segundo-turno",
            "Disputa terá segundo turno; não retentar primeiro turno para descobrir eleito",
        )
    elif cargo["estado"] == "sem-eleitos":
        situacao, motivo = "sem-atribuicao", "TSE finalizou sem atribuir eleitos; requer acompanhamento específico"
    elif not cargo.get("tf"):
        situacao, motivo = "revisar", "Estado finalizado sem tf=true"
    elif vagas is None:
        situacao, motivo = "revisar", "Quantidade de vagas não disponível para conferir completude"
    elif quantidade != vagas:
        situacao, motivo = "revisar", f"Lista tem {quantidade} eleitos para {vagas} vagas; não preencher por ranking"
    else:
        situacao, motivo = "concluido", "Finalizado pelo TSE e quantidade de eleitos compatível com as vagas"
    return {
        "cargo": cargo["cargo"],
        "turno": cargo["turno"],
        "situacao": situacao,
        "motivo": motivo,
        "quantidade_eleitos": quantidade,
        "vagas": vagas,
        "gerado_em": cargo["fonte"]["gerado_em"],
    }


def resumir(documentos: dict[str, dict]) -> dict:
    resultados = [
        {"uf": uf, **avaliar(cargo)}
        for uf, documento in sorted(documentos.items())
        for cargo in documento.get("cargos", [])
    ]
    contagens = dict(Counter(item["situacao"] for item in resultados))
    bloqueios = {"aguardando-tse", "atualizacao-falhou", "revisar"}
    return {
        "versao_schema": 1,
        "resultados": resultados,
        "contagens": contagens,
        "pode_encerrar_primeiro_turno": bool(resultados)
        and not any(item["situacao"] in bloqueios for item in resultados),
    }


def gravar_relatorio(destino: Path, documentos: dict[str, dict], *, emitir: bool = True) -> dict:
    relatorio = resumir(documentos)
    salvar_json(destino / "relatorio-conclusao.json", relatorio)
    linhas = [
        "# Conclusão da exportação",
        "",
        "| UF | Cargo | Turno | Situação | Eleitos / vagas | Fonte |",
        "| - | - | - | - | - | - |",
    ]
    for item in relatorio["resultados"]:
        linhas.append(
            f"| {item['uf']} | {item['cargo']['nome']} | {item['turno']} | {item['situacao']} | {item['quantidade_eleitos']} / {item['vagas']} | {item['gerado_em']} |"
        )
        if emitir:
            print(
                f"{item['uf']} | {item['cargo']['nome']} | {item['situacao']} | {item['quantidade_eleitos']}/{item['vagas']} | {item['motivo']}",
                file=sys.stderr,
            )
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "relatorio-conclusao.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    if emitir:
        print(
            "Resumo: " + ", ".join(f"{status}={quantidade}" for status, quantidade in relatorio["contagens"].items()),
            file=sys.stderr,
        )
        print(
            "Primeiro turno: "
            + (
                "sem resultados pendentes de atualização; segundo turno/exceções continuam separados"
                if relatorio["pode_encerrar_primeiro_turno"]
                else "ainda há resultados pendentes, falhas ou inconsistências; consulte o relatório"
            ),
            file=sys.stderr,
        )
    return relatorio


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifesto", type=Path)
    args = parser.parse_args(argv)
    try:
        manifesto = json.loads(args.manifesto.read_text())
        documentos = {}
        for uf, relativo in manifesto["territorios"].items():
            arquivo = (args.manifesto.parent / relativo).resolve()
            if not arquivo.is_relative_to(args.manifesto.parent.resolve()):
                raise ValueError("Caminho fora da publicação")
            documentos[uf] = json.loads(arquivo.read_text())
        gravar_relatorio(args.manifesto.parent.parent, documentos)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
