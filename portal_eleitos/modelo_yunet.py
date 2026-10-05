"""Baixa o detector local com checksum fixado; não é necessário no Brasil.IO."""

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

import requests

URL = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


def baixar(destino: Path) -> None:
    if destino.exists():
        if hashlib.sha256(destino.read_bytes()).hexdigest() != SHA256:
            raise ValueError("Modelo existente tem hash diferente; não será sobrescrito")
        return
    resposta = requests.get(URL, timeout=(5, 20))
    resposta.raise_for_status()
    if hashlib.sha256(resposta.content).hexdigest() != SHA256:
        raise ValueError("Checksum do modelo baixado difere da versão fixada")
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as stream:
            temporario = Path(stream.name)
            stream.write(resposta.content)
        temporario.replace(destino)
    finally:
        if temporario:
            temporario.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destino", type=Path)
    args = parser.parse_args(argv)
    try:
        baixar(args.destino)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
