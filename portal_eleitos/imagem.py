"""Prepara retratos em CPU; enquadramento e evidências ficam no campo local."""

import hashlib
import math
import tempfile
import warnings
from pathlib import Path

MAX_PIXELS = 20_000_000
VERSAO_PARAMETROS = 1


def _numero(valor, nome: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ValueError(f"{nome} deve ser um número finito")
    return float(valor)


def parametros_foto(tamanho: int = 320, qualidade: int = 85, margem: float = 0.45) -> dict:
    """Valida parâmetros e identifica a versão do enquadramento para retomada."""
    if isinstance(tamanho, bool) or not isinstance(tamanho, int) or not 1 <= tamanho <= 4096:
        raise ValueError("tamanho deve ser inteiro entre 1 e 4096")
    if isinstance(qualidade, bool) or not isinstance(qualidade, int) or not 1 <= qualidade <= 100:
        raise ValueError("qualidade deve ser inteira entre 1 e 100")
    margem = _numero(margem, "margem")
    if not 0 <= margem <= 10:
        raise ValueError("margem deve estar entre 0 e 10")
    return {"tamanho": tamanho, "qualidade": qualidade, "margem": margem, "versao": VERSAO_PARAMETROS}


def _sha256(caminho: Path) -> str:
    with caminho.open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def _abrir_imagem(original: Path):
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(original) as imagem:
                if imagem.width * imagem.height > MAX_PIXELS:
                    raise ValueError("imagem excede o limite de 20 milhões de pixels")
                imagem.verify()
            with Image.open(original) as imagem:
                orientada = ImageOps.exif_transpose(imagem)
                if "A" in orientada.getbands() or "transparency" in orientada.info:
                    transparente = orientada.convert("RGBA")
                    fundo = Image.new("RGBA", orientada.size, "white")
                    orientada = Image.alpha_composite(fundo, transparente)
                return orientada.convert("RGB")
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as erro:
        raise ValueError("imagem excede o limite de 20 milhões de pixels") from erro
    except (UnidentifiedImageError, OSError, SyntaxError) as erro:
        raise ValueError(f"imagem inválida: {erro}") from erro


def detectar_rosto(imagem, modelo: Path) -> list[dict]:
    """YuNet 2023/OpenCV 4 em CPU; recebe PIL RGB orientada, retorna caixas originais.

    Reduz o maior lado para até 640 pixels e não retorna pontos faciais ou embeddings.
    O limiar baixo permite distinguir baixa confiança de ausência de rosto.
    """
    import cv2

    cv2.setNumThreads(1)
    import numpy as np
    from PIL import Image

    if cv2.__version__.split(".")[0] != "4":
        raise RuntimeError("YuNet 2023 requer OpenCV 4.x")
    escala = min(1.0, 640 / max(imagem.size))
    largura = max(1, round(imagem.width * escala))
    altura = max(1, round(imagem.height * escala))
    reduzida = imagem.resize((largura, altura), Image.Resampling.LANCZOS)
    detector = cv2.FaceDetectorYN.create(
        str(modelo), "", (largura, altura), 0.3, 0.3, 5000, cv2.dnn.DNN_BACKEND_OPENCV, cv2.dnn.DNN_TARGET_CPU
    )
    _, rostos = detector.detect(cv2.cvtColor(np.asarray(reduzida), cv2.COLOR_RGB2BGR))
    if rostos is None:
        return []
    escala_horizontal = imagem.width / largura
    escala_vertical = imagem.height / altura
    return [
        {
            "x": float(rosto[0]) * escala_horizontal,
            "y": float(rosto[1]) * escala_vertical,
            "largura": float(rosto[2]) * escala_horizontal,
            "altura": float(rosto[3]) * escala_vertical,
            "confianca": float(rosto[14]),
        }
        for rosto in rostos
    ]


def _retangulo(dados: dict, dimensoes: tuple[int, int], *, quadrado: bool) -> dict:
    try:
        retangulo = {campo: _numero(dados[campo], campo) for campo in ("x", "y", "largura", "altura")}
    except (KeyError, TypeError) as erro:
        raise ValueError("recorte exige x, y, largura e altura numéricos") from erro
    largura, altura = dimensoes
    if not 0 < retangulo["largura"] <= 4 * max(dimensoes) or not 0 < retangulo["altura"] <= 4 * max(dimensoes):
        raise ValueError("dimensões do recorte fora dos limites seguros")
    if quadrado and retangulo["largura"] != retangulo["altura"]:
        raise ValueError("recorte manual deve ser quadrado")
    if (
        retangulo["x"] >= largura
        or retangulo["y"] >= altura
        or retangulo["x"] + retangulo["largura"] <= 0
        or retangulo["y"] + retangulo["altura"] <= 0
    ):
        raise ValueError("recorte deve intersectar a imagem")
    return retangulo


def _padding(recorte: dict, dimensoes: tuple[int, int], tamanho: int) -> dict:
    largura, altura = dimensoes
    escala = tamanho / recorte["largura"]
    return {
        "superior": max(0.0, -recorte["y"]) * escala,
        "direito": max(0.0, recorte["x"] + recorte["largura"] - largura) * escala,
        "inferior": max(0.0, recorte["y"] + recorte["altura"] - altura) * escala,
        "esquerdo": max(0.0, -recorte["x"]) * escala,
        "unidade": "pixels_saida",
    }


def processar_foto(
    original: Path,
    destino_dir: Path,
    modelo: Path,
    *,
    tamanho=320,
    qualidade=85,
    margem=0.45,
    override: dict | None = None,
    detector=None,
) -> dict:
    """Grava fotos/<hash>.webp atomicamente sem alterar o original.

    Detector injetável: callable(imagem PIL RGB orientada, modelo Path) -> lista
    de dicts x/y/largura/altura/confianca. Override usa coordenadas orientadas.
    Consumidores públicos devem remover o campo local, que contém auditoria.
    Falhas de inferência geram contain com revisão; KeyboardInterrupt propaga.
    """
    from PIL import Image, features

    parametros = parametros_foto(tamanho, qualidade, margem)
    margem = parametros["margem"]
    if not features.check("webp"):
        raise RuntimeError("Pillow não oferece suporte WebP")
    imagem = _abrir_imagem(original)
    hash_original = _sha256(original)
    hash_modelo = _sha256(modelo) if modelo.is_file() else None
    rosto = None
    score = None
    fallback = None
    erro_detector = None
    metodo = "contain"
    if override is not None:
        recorte = _retangulo(override, imagem.size, quadrado=True)
        metodo = "manual"
    else:
        try:
            deteccoes = (detector or detectar_rosto)(imagem, modelo)
            rostos = []
            for deteccao in deteccoes:
                confianca = _numero(deteccao["confianca"], "confianca")
                if not 0 <= confianca <= 1:
                    raise ValueError("confiança fora do intervalo 0 a 1")
                if confianca >= 0.9:
                    rostos.append(deteccao)
            if len(rostos) == 0:
                fallback = "baixa_confianca" if deteccoes else "sem_rosto"
            elif len(rostos) > 1:
                fallback = "multiplos_rostos"
            else:
                score = _numero(rostos[0]["confianca"], "confianca")
                if not 0 <= score <= 1:
                    raise ValueError("confiança fora do intervalo 0 a 1")
                if score < 0.9:
                    fallback = "baixa_confianca"
                else:
                    rosto = _retangulo(rostos[0], imagem.size, quadrado=False) | {"confianca": score}
                    metodo = "yunet"
        except KeyboardInterrupt:
            raise
        except Exception as erro:  # noqa: BLE001 - inferência externa não impede publicar a imagem inteira
            fallback = "erro_detector"
            erro_detector = f"{type(erro).__name__}: {erro}"
            rosto = None
        if metodo == "yunet":
            lado = max(rosto["largura"], rosto["altura"]) * (1 + 2 * margem)
            recorte = {
                "x": rosto["x"] + rosto["largura"] / 2 - lado / 2,
                "y": rosto["y"] + rosto["altura"] / 2 - lado / 2 - 0.05 * rosto["altura"],
                "largura": lado,
                "altura": lado,
            }
        else:
            lado = max(imagem.size) * (1 + 2 * margem)
            recorte = {
                "x": (imagem.width - lado) / 2,
                "y": (imagem.height - lado) / 2,
                "largura": lado,
                "altura": lado,
            }
    # Amostra diretamente na saída: janela externa nunca aloca um canvas gigantesco.
    escala = recorte["largura"] / tamanho
    variante = imagem.transform(
        (tamanho, tamanho),
        Image.Transform.AFFINE,
        (escala, 0, recorte["x"], 0, escala, recorte["y"]),
        resample=Image.Resampling.BICUBIC,
        fillcolor="white",
    )
    variante.info.clear()
    pasta = destino_dir / "fotos"
    pasta.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".foto-", suffix=".webp", dir=pasta, delete=False) as arquivo:
            temporario = Path(arquivo.name)
        variante.save(temporario, format="WEBP", quality=qualidade, method=6)
        hash_variante = _sha256(temporario)
        temporario.replace(pasta / f"{hash_variante}.webp")
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
    return {
        "url": f"fotos/{hash_variante}.webp",
        "sha256": hash_variante,
        "largura": tamanho,
        "altura": tamanho,
        "formato": "webp",
        "estado": "disponivel",
        "local": {
            "versao_filtro_confianca": 2,
            "imagem_orientada": {"largura": imagem.width, "altura": imagem.height},
            "rosto": rosto,
            "recorte": recorte,
            "padding": _padding(recorte, imagem.size, tamanho),
            "modelo": {"arquivo": modelo.name, "versao": "yunet-2023mar-opencv4", "sha256": hash_modelo},
            "sha256_original": hash_original,
            "parametros": parametros,
            "margem_rosto": margem if metodo == "yunet" else None,
            "metodo": metodo,
            "score": score,
            "revisao": metodo == "contain",
            "fallback": fallback,
            "erro_detector": erro_detector,
            "override": dict(override) if override is not None else None,
        },
    }
