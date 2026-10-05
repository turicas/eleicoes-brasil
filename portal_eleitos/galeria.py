"""Galeria local de revisão dos retratos, sem upload nem alteração das fotos."""

import argparse
import html
import json
import sys
from pathlib import Path, PurePosixPath


def gerar_galeria(manifesto: Path, fotos: Path) -> Path:
    edicao = json.loads(manifesto.read_text())
    mapa = json.loads((fotos / "mapa-fotos.json").read_text())["fotos"]
    registros = {}
    estado = fotos / "estado-fotos.jsonl"
    if estado.exists():
        for linha in estado.read_text().splitlines():
            try:
                registro = json.loads(linha)
            except ValueError:
                continue
            if registro.get("etapa") == "sucesso":
                registros[registro["chave"]] = registro["resultado"].get("local", {})
    cards = []
    for uf, relativo in edicao["territorios"].items():
        arquivo = (manifesto.parent / relativo).resolve()
        if not arquivo.is_relative_to(manifesto.parent.resolve()):
            raise ValueError("Documento fora da publicação")
        documento = json.loads(arquivo.read_text())
        for cargo in documento.get("cargos", []):
            for eleito in cargo["eleitos"]:
                chave = f"{cargo['eleicao']}:{uf}:{eleito['sequencial_tse']}"
                foto = mapa.get(chave, {})
                metadados = registros.get(chave, {})
                fallback = metadados.get("fallback")
                nome = html.escape(eleito["nome_urna"])
                url = foto.get("url")
                imagem = "<p>Foto indisponível</p>"
                if foto.get("estado") == "disponivel" and isinstance(url, str):
                    caminho = PurePosixPath(url)
                    if caminho.is_absolute() or ".." in caminho.parts or caminho.parts[0] != "fotos":
                        raise ValueError("Caminho de foto inseguro")
                    imagem = f'<img src="{html.escape(url, quote=True)}" width="320" height="320" loading="lazy" alt="{nome}">'
                classe = "revisar" if fallback else ""
                cards.append(
                    (
                        bool(fallback),
                        uf,
                        nome,
                        (
                            f'<article class="{classe}">{imagem}<h2>{nome}</h2>'
                            f'<p>{html.escape(uf)} - {html.escape(cargo["cargo"]["nome"])}</p>'
                            f'<p>{html.escape(chave)}</p><p>{html.escape(str(fallback or metadados.get("metodo", "")))}</p></article>'
                        ),
                    )
                )
    cards.sort(key=lambda item: (not item[0], item[1], item[2]))
    conteudo = '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Revisão das fotos dos eleitos</title>'
    conteudo += "<style>body{font-family:sans-serif;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}article{border:1px solid #aaa;padding:8px}img{width:100%;height:auto}h2{font-size:18px}.revisar{border:4px solid #b45f06}</style>"
    conteudo += f"<h1>Revisão das fotos: {len(cards)} candidaturas</h1><p>Casos com fallback aparecem primeiro. Fotos não foram alteradas.</p><main>"
    conteudo += "".join(card[3] for card in cards) + "</main></html>"
    destino = fotos / "galeria.html"
    destino.write_text(conteudo, encoding="utf-8")
    return destino


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifesto", type=Path)
    parser.add_argument("fotos", type=Path)
    args = parser.parse_args(argv)
    try:
        print(gerar_galeria(args.manifesto, args.fotos))
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
