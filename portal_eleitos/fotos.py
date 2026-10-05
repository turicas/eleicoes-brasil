"""Exporta fotos locais retomáveis; publicar as variantes antes de ativar o mapa no exportador."""

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path, PurePosixPath

MAX_BYTES = 10 * 1024 * 1024
CAMPOS_PUBLICOS = ("estado", "url", "sha256", "largura", "altura", "formato")


def _sha256(caminho: Path) -> str:
    with caminho.open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def _hash_json(valor) -> str:
    return hashlib.sha256(json.dumps(valor, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _caminho_seguro(base: Path, relativo: str) -> Path:
    if not isinstance(relativo, str) or not relativo or "\\" in relativo:
        raise ValueError("caminho relativo inválido")
    partes = PurePosixPath(relativo)
    if partes.is_absolute() or any(parte in {".", "..", ""} for parte in relativo.split("/")):
        raise ValueError(f"caminho inseguro: {relativo}")
    caminho = base / relativo
    if not caminho.resolve().is_relative_to(base.resolve()) or caminho.is_symlink():
        raise ValueError(f"caminho fora do diretório: {relativo}")
    return caminho


def _ler_json(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def _candidaturas(manifesto: Path) -> dict:
    dados = _ler_json(manifesto)
    if dados.get("versao_schema") != 1 or not isinstance(dados.get("territorios"), dict):
        raise ValueError("manifesto: esquema inválido")
    candidatos = {}
    for territorio, relativo in dados["territorios"].items():
        if not re.fullmatch(r"[A-Z]{2}", territorio):
            raise ValueError("território inválido")
        documento = _ler_json(_caminho_seguro(manifesto.parent, relativo))
        cargos = documento.get("cargos", [])
        if not isinstance(cargos, list):
            raise TypeError("cargos deve ser uma lista")
        for cargo in cargos:
            fonte = cargo.get("fonte", {})
            eleicao = str(fonte.get("eleicao", cargo.get("eleicao", "")))
            uf = fonte.get("abrangencia", territorio)
            if not re.fullmatch(r"[0-9]+", eleicao) or not re.fullmatch(r"[A-Z]{2}", uf):
                raise ValueError("contexto de eleição/UF inválido")
            for candidato in cargo.get("eleitos", []):
                sequencial = str(candidato["sequencial_tse"])
                if not re.fullmatch(r"[0-9]+", sequencial):
                    raise ValueError("sequencial_tse inválido")
                chave = f"{eleicao}:{uf}:{sequencial}"
                item = {
                    "chave": chave,
                    "eleicao": eleicao,
                    "uf": uf,
                    "sequencial": sequencial,
                    "url": candidato.get("foto", {}).get("fonte_tse"),
                }
                if chave in candidatos and candidatos[chave] != item:
                    raise ValueError(f"candidatura duplicada com fontes distintas: {chave}")
                candidatos[chave] = item
    return candidatos


def _validar_url(url: str, *, eleicao=None, uf=None, sequencial=None) -> None:
    if not isinstance(url, str):
        raise ValueError("fonte_tse ausente")  # noqa: TRY004 - contrato de foto inválida
    partes = urllib.parse.urlsplit(url)
    if partes.scheme != "https" or partes.netloc != "resultados.tse.jus.br" or partes.query or partes.fragment:
        raise ValueError("URL de foto fora da fonte oficial permitida")
    foto = re.fullmatch(r"/oficial/ele[0-9]{4}/([0-9]+)/fotos/([a-z]{2})/([0-9]+)\.(?:jpeg|jpg)", partes.path)
    if not foto or (eleicao is not None and foto.groups() != (eleicao, uf.lower(), sequencial)):
        raise ValueError("caminho de foto incompatível com a candidatura")


class _SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirecionamento de foto não permitido")


def baixar_foto(url: str, destino: Path, *, timeout: float = 10) -> None:
    """Transfere até 10 MiB, sem redirecionamentos e com orçamento de até oito segundos."""
    _validar_url(url)
    limite = min(timeout, 8.0)
    inicio = time.perf_counter()
    opener = urllib.request.build_opener(_SemRedirecionamento())
    requisicao = urllib.request.Request(url, headers={"User-Agent": "portal-eleitos/1"})
    with opener.open(requisicao, timeout=limite) as resposta, destino.open("wb") as arquivo:
        tamanho = resposta.headers.get("Content-Length")
        if tamanho is not None and int(tamanho) > MAX_BYTES:
            raise ValueError("foto excede 10 MiB")
        total = 0
        while True:
            if time.perf_counter() - inicio >= limite:
                raise TimeoutError("tempo total de download excedido")
            bloco = resposta.read1(min(64 * 1024, MAX_BYTES + 1 - total))
            if not bloco:
                break
            total += len(bloco)
            if total > MAX_BYTES:
                raise ValueError("foto excede 10 MiB")
            arquivo.write(bloco)
        if not total:
            raise ValueError("foto vazia")


def _temporario(pasta: Path, sufixo: str) -> Path:
    with tempfile.NamedTemporaryFile(prefix=".foto-", suffix=sufixo, dir=pasta, delete=False) as arquivo:
        return Path(arquivo.name)


def _gravar_json(caminho: Path, dados) -> None:
    temporario = _temporario(caminho.parent, ".json")
    try:
        temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        temporario.replace(caminho)
    finally:
        temporario.unlink(missing_ok=True)


def _estado(caminho: Path) -> tuple[dict, dict]:
    baixadas, sucessos = {}, {}
    if caminho.exists():
        with caminho.open(encoding="utf-8") as arquivo:
            for numero, linha in enumerate(arquivo, start=1):
                if not linha.strip():
                    continue
                try:
                    registro = json.loads(linha)
                except json.JSONDecodeError:
                    print(f"Estado: registro incompleto/inválido ignorado na linha {numero}.", file=sys.stderr)
                    continue
                if not isinstance(registro, dict):
                    raise ValueError(f"estado: registro inválido na linha {numero}")  # noqa: TRY004
                if registro.get("etapa") == "baixada":
                    baixadas[registro["chave"]] = registro
                elif registro.get("etapa") == "sucesso":
                    sucessos[registro["chave"]] = registro
    return baixadas, sucessos


def _variante_valida(resultado: dict, saida: Path) -> bool:
    try:
        sha = resultado["sha256"]
        if (
            resultado.get("estado") != "disponivel"
            or not isinstance(sha, str)
            or not re.fullmatch(r"[0-9a-f]{64}", sha)
            or resultado["url"] != f"fotos/{sha}.webp"
        ):
            return False
        caminho = _caminho_seguro(saida, resultado["url"])
        return caminho.is_file() and _sha256(caminho) == sha
    except (KeyError, TypeError, ValueError, OSError):
        return False


def _publica(resultado: dict, url: str) -> dict:
    return {**{campo: resultado.get(campo) for campo in CAMPOS_PUBLICOS}, "fonte_tse": url}


def _zip(saida: Path, mapa: dict, erros: dict) -> None:
    destino = _caminho_seguro(saida, "fotos.zip")
    temporario = _temporario(saida, ".zip")
    try:
        with zipfile.ZipFile(temporario, "w", compression=zipfile.ZIP_DEFLATED) as arquivo:
            arquivo.writestr("manifesto-fotos.json", json.dumps(mapa, ensure_ascii=False, indent=2))
            arquivo.writestr("erros-fotos.json", json.dumps(erros, ensure_ascii=False, indent=2))
            caminhos = {foto["url"] for foto in mapa["fotos"].values() if foto["estado"] == "disponivel"}
            for relativo in sorted(caminhos):
                arquivo.write(_caminho_seguro(saida, relativo), relativo)
        temporario.replace(destino)
    finally:
        temporario.unlink(missing_ok=True)


def executar_fotos(
    manifesto: Path,
    output: Path,
    modelo: Path,
    *,
    workers: int = 6,
    qualidade: int = 85,
    tamanho: int = 320,
    margem: float = 0.45,
    overrides: Path | None = None,
    timeout: float = 10,
    processador=None,
    baixador=None,
) -> dict:
    """Retorna mapa público; callbacks recebem os argumentos de processar_foto/baixar_foto.

    Processador injetado dispensa Pillow no preflight. O JSON de overrides associa
    eleição:UF:sequencial a um override. Estado local preserva a auditoria completa.
    """
    from .imagem import parametros_foto

    parametros = parametros_foto(tamanho, qualidade, margem)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise ValueError("workers deve ser inteiro positivo")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout deve ser positivo e finito")
    if not modelo.is_file():
        raise FileNotFoundError(f"modelo ONNX ausente: {modelo}")
    hash_modelo = _sha256(modelo)
    if processador is None:
        from PIL import features

        if not features.check("webp"):
            raise RuntimeError("Pillow não oferece suporte WebP")
        from .imagem import processar_foto

        processador = processar_foto
    limitar_http = baixador is None
    baixador = baixador or baixar_foto
    ajustes = _ler_json(overrides) if overrides is not None else {}
    if not isinstance(ajustes, dict) or any(not isinstance(valor, dict) for valor in ajustes.values()):
        raise ValueError("overrides deve associar chaves de candidaturas a objetos")
    candidatos = _candidaturas(manifesto)
    output.mkdir(parents=True, exist_ok=True)
    originais = _caminho_seguro(output, "originais")
    originais.mkdir(exist_ok=True)
    _caminho_seguro(output, "fotos").mkdir(exist_ok=True)
    estado = _caminho_seguro(output, "estado-fotos.jsonl")
    baixadas, sucessos = _estado(estado)
    if estado.exists() and estado.stat().st_size:
        with estado.open("rb") as arquivo:
            arquivo.seek(-1, 2)
            incompleto = arquivo.read(1) != b"\n"
        if incompleto:
            with estado.open("a", encoding="utf-8") as arquivo:
                arquivo.write("\n")
                arquivo.flush()
    lock = threading.Lock()
    cancelado = threading.Event()

    def registrar(registro):
        with lock, estado.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
            arquivo.flush()

    proximo_download = 0.0

    def limitar_download():
        nonlocal proximo_download
        with lock:
            agora = time.perf_counter()
            prazo = max(agora, proximo_download)
            proximo_download = prazo + 0.1
        if prazo > agora:
            time.sleep(prazo - agora)

    def trabalhar(item):
        chave, url = item["chave"], item["url"]
        identidade = {
            "chave": chave,
            "url": url,
            "modelo_sha256": hash_modelo,
            "parametros": parametros,
            "override_sha256": _hash_json(ajustes.get(chave)),
        }
        try:
            _validar_url(url, eleicao=item["eleicao"], uf=item["uf"], sequencial=item["sequencial"])
            anterior = sucessos.get(chave, {})
            local_anterior = anterior.get("resultado", {}).get("local", {})
            fallback_antigo = (
                local_anterior.get("fallback") == "multiplos_rostos"
                and local_anterior.get("versao_filtro_confianca", 1) < 2
            )
            if (
                not fallback_antigo
                and all(anterior.get(campo) == valor for campo, valor in identidade.items())
                and _variante_valida(anterior.get("resultado", {}), output)
            ):
                return chave, _publica(anterior["resultado"], url), True, None
            original = _caminho_seguro(output, f"originais/{chave.replace(':', '_')}.jpg")
            baixada = baixadas.get(chave, {})
            reutilizar = (
                baixada.get("url") == url and original.is_file() and _sha256(original) == baixada.get("original_sha256")
            )
            if not reutilizar:
                for tentativa in range(2):
                    if cancelado.is_set():
                        raise InterruptedError("processamento cancelado")
                    temporario = _temporario(originais, ".jpg")
                    try:
                        if limitar_http:
                            limitar_download()
                        baixador(url, temporario, timeout=timeout)
                        if not 0 < temporario.stat().st_size <= MAX_BYTES:
                            raise ValueError("foto vazia ou maior que 10 MiB")
                        hash_original = _sha256(temporario)
                        temporario.replace(original)
                        registrar({"etapa": "baixada", "chave": chave, "url": url, "original_sha256": hash_original})
                        break
                    except (TimeoutError, urllib.error.URLError, ConnectionError):
                        if tentativa == 1:
                            raise
                    finally:
                        temporario.unlink(missing_ok=True)
            if cancelado.is_set():
                raise InterruptedError("processamento cancelado")
            resultado = processador(
                original,
                output,
                modelo,
                tamanho=tamanho,
                qualidade=qualidade,
                margem=margem,
                override=ajustes.get(chave),
            )
            if not _variante_valida(resultado, output):
                raise ValueError("processador retornou variante ausente, insegura ou corrompida")
            registrar({**identidade, "etapa": "sucesso", "original_sha256": _sha256(original), "resultado": resultado})
            return chave, _publica(resultado, url), False, None
        except KeyboardInterrupt:
            cancelado.set()
            raise
        except Exception as erro:  # noqa: BLE001 - registra erro por item sem ocultar falha
            registrar({**identidade, "etapa": "erro", "erro": f"{type(erro).__name__}: {erro}"})
            foto = {"estado": "erro", "url": None, "sha256": None, "largura": None, "altura": None, "formato": "webp"}
            return chave, _publica(foto, url), False, type(erro).__name__

    inicio = time.perf_counter()
    mapa = {"versao_schema": 1, "fotos": {}}
    erros = {"versao_schema": 1, "erros": {}}
    total = len(candidatos)
    concluidas = ignoradas = falhas = 0
    executor = ThreadPoolExecutor(max_workers=workers)
    pendentes = set()
    itens = iter(candidatos.values())

    def agendar():
        item = next(itens, None)
        if item is not None:
            pendentes.add(executor.submit(trabalhar, item))

    try:
        for _ in range(min(workers, total)):
            agendar()
        while pendentes:
            prontas, _ = wait(pendentes, timeout=0.1, return_when=FIRST_COMPLETED)
            for futura in prontas:
                pendentes.remove(futura)
                chave, foto, ignorada, erro = futura.result()
                mapa["fotos"][chave] = foto
                ignoradas += ignorada
                if erro:
                    erros["erros"][chave] = {"estado": "erro", "tipo": erro}
                    falhas += 1
                concluidas += 1
                duracao = max(time.perf_counter() - inicio, 1e-9)
                taxa = concluidas / duracao
                print(
                    f"{concluidas}/{total} ({concluidas / total:.0%}), {taxa:.1f}/s "
                    f"ETA: {(total - concluidas) / taxa:.1f}s ignoradas={ignoradas} falhas={falhas}",
                    file=sys.stderr,
                )
                agendar()
    except BaseException:
        cancelado.set()
        for futura in pendentes:
            futura.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=True)
    mapa["fotos"] = dict(sorted(mapa["fotos"].items()))
    _gravar_json(_caminho_seguro(output, "mapa-fotos.json"), mapa)
    _zip(output, mapa, erros)
    if not total:
        print("0/0 (100%), 0.0/s ETA: 0.0s ignoradas=0 falhas=0", file=sys.stderr)
    return mapa


def cria_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifesto", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("modelo", type=Path)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--qualidade", type=int, default=85)
    parser.add_argument("--tamanho", type=int, default=320)
    parser.add_argument("--margem", type=float, default=0.45)
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--timeout", type=float, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = cria_parser().parse_args(argv)
    try:
        mapa = executar_fotos(**vars(argumentos))
    except KeyboardInterrupt:
        print("Processamento interrompido; o estado permite retomada.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, ImportError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return int(any(foto["estado"] == "erro" for foto in mapa["fotos"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
