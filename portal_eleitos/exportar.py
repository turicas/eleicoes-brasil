"""Exporta revisões imutáveis de resultados, sem acessar Google Sheets ou MinIO."""

import argparse
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from .infra import ClienteTSE, salvar_json

CONFIGURACAO = "https://resultados.tse.jus.br/oficial/comum/config/ele-c.json"


def _carregar_anterior(publicacao: Path) -> dict[str, dict]:
    manifesto = publicacao / "manifesto.json"
    if not manifesto.exists():
        return {}
    dados = json.loads(manifesto.read_text())
    territorios = {}
    for codigo, relativo in dados["territorios"].items():
        arquivo = (publicacao / relativo).resolve()
        if not arquivo.is_relative_to(publicacao.resolve()):
            raise ValueError("Caminho inválido no manifesto anterior")
        territorios[codigo] = json.loads(arquivo.read_text())
    return territorios


def _aplicar_fotos(documentos: dict[str, dict], mapa: dict) -> None:
    if mapa.get("versao_schema") != 1 or not isinstance(mapa.get("fotos"), dict):
        raise ValueError("Mapa de fotos incompatível")
    for documento in documentos.values():
        for cargo in documento.get("cargos", []):
            for eleito in cargo["eleitos"]:
                chave = f"{cargo['eleicao']}:{cargo['abrangencia_disputa']['codigo']}:{eleito['sequencial_tse']}"
                foto = mapa["fotos"].get(chave)
                if foto is None:
                    continue
                permitidos = {
                    campo: foto.get(campo) for campo in ("estado", "url", "sha256", "largura", "altura", "formato")
                }
                if permitidos["estado"] == "disponivel":
                    hash_foto = permitidos["sha256"]
                    if (
                        not isinstance(hash_foto, str)
                        or len(hash_foto) != 64
                        or any(char not in "0123456789abcdef" for char in hash_foto)
                    ):
                        raise ValueError("Hash de foto inválido")
                    if permitidos["url"] != f"fotos/{hash_foto}.webp" or permitidos["formato"] != "webp":
                        raise ValueError("Caminho de foto inválido")
                    if not all(
                        isinstance(permitidos[campo], int) and permitidos[campo] > 0 for campo in ("largura", "altura")
                    ):
                        raise ValueError("Dimensões de foto inválidas")
                fonte = eleito["foto"].get("fonte_tse")
                eleito["foto"] = {**permitidos, "fonte_tse": fonte}


def exportar(
    ano: int,
    destino: Path,
    *,
    turno: int = 1,
    workers: int = 6,
    timeout: float = 10,
    fotos: Path | None = None,
    fontes: list[dict] | None = None,
    coletar=None,
) -> Path:
    from .dados import UFS_NOMES, descobrir_fontes, normalizar_resultado, url_foto

    destino = Path(destino)
    publicacao = destino / "publicacao"
    anteriores = _carregar_anterior(publicacao)
    documentos = deepcopy(anteriores)
    cliente = ClienteTSE(timeout) if coletar is None else None
    buscar = coletar or cliente
    inicio = time.perf_counter()
    agora = datetime.now(timezone.utc).isoformat()
    revisao = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    configuracao = None
    falhas = []
    try:
        if fontes is None:
            configuracao = buscar(CONFIGURACAO)
            fontes = descobrir_fontes(configuracao, ano, turno)
        if not fontes:
            raise ValueError("Nenhuma fonte disponível")
        for documento in documentos.values():
            if documento.get("edicao", {}).get("ano") != ano:
                raise ValueError("Diretório de saída pertence a outro ano")

        def processar(job):
            contexto = (job["eleicao"], job["cargo"], job["uf"])
            capturado = datetime.now(timezone.utc).isoformat()
            try:
                bruto = buscar(job["url"])
            except (OSError, ValueError) as erro:
                return job, None, str(erro)
            conteudo = json.dumps(
                bruto, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
            ).encode()
            hash_bruto = sha256(conteudo).hexdigest()
            salvar_json(
                destino / "brutos" / str(contexto[0]) / str(contexto[1]) / contexto[2] / f"{hash_bruto}.json", bruto
            )
            try:
                documento = normalizar_resultado(
                    bruto,
                    ano=ano,
                    eleicao=job["eleicao"],
                    turno=job["turno"],
                    cargo=job["cargo"],
                    uf=job["uf"],
                    url=job["url"],
                    capturado_em=capturado,
                    hash_bruto=hash_bruto,
                )
            except ValueError as erro:
                return job, None, str(erro)
            if configuracao:
                for eleito in documento["eleitos"]:
                    eleito["foto"]["fonte_tse"] = url_foto(
                        ano=ano,
                        eleicao=job["eleicao"],
                        uf=job["uf"],
                        sequencial_tse=eleito["sequencial_tse"],
                        config=configuracao,
                    )
            return job, documento, None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futuros = {executor.submit(processar, job): job for job in fontes}
            for concluidos, futuro in enumerate(as_completed(futuros), start=1):
                job, cargo, erro = futuro.result()
                codigo = job["uf"].upper()
                documento = documentos.setdefault(
                    codigo,
                    {
                        "territorio": {
                            "tipo": "br" if codigo == "BR" else "uf",
                            "codigo": codigo,
                            "nome": "Brasil" if codigo == "BR" else UFS_NOMES[codigo],
                            "uf": None if codigo == "BR" else codigo,
                        },
                        "cargos": [],
                    },
                )
                antigo = next((item for item in documento["cargos"] if item["cargo"]["codigo"] == job["cargo"]), None)
                if erro:
                    if antigo is None:
                        falhas.append(f"{codigo}/cargo {job['cargo']}: sem última versão válida ({erro})")
                    else:
                        antigo["fonte"]["estado_coleta"] = "ultima-versao-valida"
                        antigo["fonte"]["erro"] = erro
                else:
                    mesmo_turno = next(
                        (
                            item
                            for item in documento["cargos"]
                            if item["cargo"]["codigo"] == job["cargo"] and item["turno"] == job["turno"]
                        ),
                        None,
                    )
                    atrasado = (
                        mesmo_turno is not None and cargo["fonte"]["gerado_em"] < mesmo_turno["fonte"]["gerado_em"]
                    )
                    regrediu = mesmo_turno is not None and mesmo_turno["tf"] and not cargo["tf"]
                    if atrasado or regrediu:
                        mesmo_turno["fonte"]["estado_coleta"] = "ultima-versao-valida"
                        mesmo_turno["fonte"][
                            "erro"
                        ] = "Resposta anterior à versão ativa ou regressão de finalização; exige revisão"
                    else:
                        preservar_primeiro = job["turno"] == 2 and cargo["estado"] in ("pendente", "segundo-turno")
                        documento["cargos"] = [
                            item
                            for item in documento["cargos"]
                            if item["cargo"]["codigo"] != job["cargo"] or (preservar_primeiro and item["turno"] == 1)
                        ]
                        documento["cargos"].append(cargo)
                duracao = max(time.perf_counter() - inicio, 0.001)
                ritmo = concluidos / duracao
                print(
                    f"{concluidos}/{len(fontes)} ({100 * concluidos / len(fontes):.0f}%), {ritmo:.1f}/s ETA: {(len(fontes) - concluidos) / ritmo:.1f}s",
                    file=sys.stderr,
                )
        if falhas:
            raise ValueError("Não foi ativada revisão incompleta: " + "; ".join(falhas))
        if fotos:
            _aplicar_fotos(documentos, json.loads(Path(fotos).read_text()))
        edicao = {"id": f"geral-{ano}", "ano": ano, "tipo": "geral"}
        for documento in documentos.values():
            documento.update(versao_schema=1, revisao=revisao, edicao=edicao, coletado_em=agora)
            documento["cargos"].sort(key=lambda item: (item["cargo"]["codigo"], item["turno"]))
        indice = {
            "versao_schema": 1,
            "revisao": revisao,
            "edicao": edicao,
            "coletado_em": agora,
            "territorio": {"tipo": "br", "codigo": "BR", "nome": "Brasil", "uf": None},
            "cargos": documentos.get("BR", {}).get("cargos", []),
            "territorios": [],
        }
        caminhos = {"BR": f"revisoes/{revisao}/indice.json"}
        for codigo, documento in sorted(documentos.items()):
            if codigo == "BR":
                continue
            relativo = f"revisoes/{revisao}/ufs/{codigo}.json"
            salvar_json(publicacao / relativo, documento)
            caminhos[codigo] = relativo
            indice["territorios"].append(
                {
                    "territorio": documento["territorio"],
                    "cargos": [
                        {
                            "cargo": cargo["cargo"],
                            "turno": cargo["turno"],
                            "estado": cargo["estado"],
                            "quantidade_eleitos": len(cargo["eleitos"]),
                            "gerado_em": cargo["fonte"]["gerado_em"],
                        }
                        for cargo in documento["cargos"]
                    ],
                }
            )
        salvar_json(publicacao / caminhos["BR"], indice)
        manifesto = {
            "versao_schema": 1,
            "revisao": revisao,
            "edicao": edicao,
            "coletado_em": agora,
            "publicado_em": None,
            "territorios": caminhos,
        }
        salvar_json(publicacao / "manifesto.json", manifesto)
        return publicacao / "manifesto.json"
    finally:
        if cliente:
            cliente.close()


def atualizar_fotos(destino: Path, mapa: Path) -> Path:
    """Clona a revisão ativa com o mapa de fotos, sem refazer coleta nem sobrescrever snapshots."""
    publicacao = Path(destino) / "publicacao"
    manifesto = json.loads((publicacao / "manifesto.json").read_text())
    documentos = _carregar_anterior(publicacao)
    _aplicar_fotos(documentos, json.loads(Path(mapa).read_text()))
    revisao = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    caminhos = {}
    for codigo, documento in documentos.items():
        documento["revisao"] = revisao
        relativo = f"revisoes/{revisao}/indice.json" if codigo == "BR" else f"revisoes/{revisao}/ufs/{codigo}.json"
        salvar_json(publicacao / relativo, documento)
        caminhos[codigo] = relativo
    manifesto.update(revisao=revisao, publicado_em=None, territorios=caminhos)
    salvar_json(publicacao / "manifesto.json", manifesto)
    return publicacao / "manifesto.json"


def cria_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ano", type=int, choices=(2026,))
    parser.add_argument("destino", type=Path)
    parser.add_argument("--turno", type=int, choices=(1, 2), default=1)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument(
        "--fotos", type=Path, help="Mapa de variantes prontas; fotos devem ser publicadas antes do manifesto"
    )
    parser.add_argument("--somente-fotos", action="store_true", help="Clona revisão ativa com --fotos, sem HTTP")
    return parser


def main(argv=None):
    args = cria_parser().parse_args(argv)
    try:
        if args.workers < 1 or not 0 < args.timeout <= 60:
            raise ValueError("Workers e timeout inválidos")
        if args.somente_fotos:
            if args.fotos is None:
                raise ValueError("--somente-fotos exige --fotos")
            print(atualizar_fotos(args.destino, args.fotos))
            return 0
        arquivo = exportar(
            args.ano, args.destino, turno=args.turno, workers=args.workers, timeout=args.timeout, fotos=args.fotos
        )
        print(arquivo)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as erro:  # noqa: BLE001 - fronteira CLI com diagnóstico
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
