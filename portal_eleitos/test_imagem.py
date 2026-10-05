"""Retratos sintéticos: enquadramento, segurança e identidade da variante."""

import hashlib
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw, features

from portal_eleitos.imagem import parametros_foto, processar_foto


@pytest.fixture
def entrada(tmp_path):
    original = tmp_path / "grade.png"
    imagem = Image.new("RGB", (120, 80), "red")
    desenho = ImageDraw.Draw(imagem)
    desenho.rectangle((60, 0, 119, 39), fill="green")
    desenho.rectangle((0, 40, 59, 79), fill="blue")
    desenho.rectangle((60, 40, 119, 79), fill="yellow")
    imagem.save(original)
    modelo = tmp_path / "face_detection_yunet_2023mar.onnx"
    modelo.write_bytes(b"modelo sintetico, nao executavel")
    return original, tmp_path / "saida", modelo


def executar(entrada, **opcoes):
    return processar_foto(*entrada, detector=lambda imagem, modelo: [], **opcoes)


def abrir_saida(entrada, resultado):
    return Image.open(entrada[1] / resultado["url"])


def test_parametros_e_importacao_sem_dependencias_visuais():
    assert parametros_foto()["tamanho"] == 320
    assert parametros_foto()["qualidade"] == 85
    assert parametros_foto()["margem"] == 0.45
    codigo = (
        "import sys; import portal_eleitos.imagem; assert 'cv2' not in sys.modules; assert 'PIL' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", codigo], capture_output=True, check=True, timeout=5)


@pytest.mark.parametrize(
    "opcoes",
    [
        {"tamanho": 0},
        {"tamanho": 5000},
        {"qualidade": 101},
        {"margem": -1},
        {"margem": float("nan")},
        {"tamanho": True},
    ],
)
def test_parametros_invalidos(opcoes):
    with pytest.raises(ValueError):
        parametros_foto(**opcoes)


def test_webp_hash_preserva_original_e_reprise(entrada):
    antes = entrada[0].read_bytes()
    resultado = executar(entrada)
    caminho = entrada[1] / resultado["url"]
    assert resultado["sha256"] == hashlib.sha256(caminho.read_bytes()).hexdigest()
    assert resultado["url"] == f"fotos/{resultado['sha256']}.webp"
    assert resultado["estado"] == "disponivel"
    assert resultado["formato"] == "webp"
    assert (resultado["largura"], resultado["altura"]) == (320, 320)
    with abrir_saida(entrada, resultado) as imagem:
        assert imagem.format == "WEBP"
        assert imagem.mode == "RGB"
        assert imagem.size == (320, 320)
        assert not imagem.getexif()
        assert min(imagem.getpixel((0, 0))) > 245
    assert entrada[0].read_bytes() == antes
    assert resultado == executar(entrada)
    assert len(list(caminho.parent.iterdir())) == 1
    assert resultado["local"]["sha256_original"] == hashlib.sha256(antes).hexdigest()
    assert resultado["local"]["modelo"]["sha256"] == hashlib.sha256(entrada[2].read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "rostos,motivo",
    [
        ([], "sem_rosto"),
        ([{"x": 20, "y": 10, "largura": 40, "altura": 40, "confianca": 0.89}], "baixa_confianca"),
        (
            [
                {"x": 20, "y": 10, "largura": 40, "altura": 40, "confianca": 0.95},
                {"x": 60, "y": 10, "largura": 40, "altura": 40, "confianca": 0.96},
            ],
            "multiplos_rostos",
        ),
    ],
)
def test_fallback_conservador(entrada, rostos, motivo):
    resultado = processar_foto(*entrada, detector=lambda imagem, modelo: rostos)
    local = resultado["local"]
    assert local["metodo"] == "contain"
    assert local["revisao"] is True
    assert local["fallback"] == motivo
    assert local["rosto"] is None
    assert local["padding"]["superior"] > local["padding"]["esquerdo"] > 0


def test_rosto_unico_tem_margem_e_coordenadas_orientadas(entrada):
    rosto = {"x": 40, "y": 20, "largura": 30, "altura": 40, "confianca": 0.95}
    resultado = processar_foto(*entrada, detector=lambda imagem, modelo: [rosto])
    local = resultado["local"]
    assert local["metodo"] == "yunet"
    assert local["revisao"] is False
    assert local["score"] == 0.95
    assert local["recorte"]["largura"] == pytest.approx(76)
    assert local["recorte"]["altura"] == pytest.approx(76)
    assert local["imagem_orientada"] == {"largura": 120, "altura": 80}


def test_override_fora_da_borda_e_round_trip(entrada):
    override = {"x": -20, "y": -10, "largura": 80, "altura": 80}

    def proibido(imagem, modelo):
        raise AssertionError("Override deve dispensar detecção")

    resultado = processar_foto(*entrada, detector=proibido, override=override, tamanho=160)
    local = resultado["local"]
    assert local["metodo"] == "manual"
    assert local["revisao"] is False
    assert local["recorte"] == override
    assert local["padding"] == {"superior": 20, "direito": 0, "inferior": 0, "esquerdo": 40, "unidade": "pixels_saida"}
    assert local["padding"]["esquerdo"] * override["largura"] / 160 == -override["x"]
    with abrir_saida(entrada, resultado) as imagem:
        assert min(imagem.getpixel((10, 10))) > 245
        vermelho, verde, azul = imagem.getpixel((60, 40))
        assert vermelho > 200 and verde < 40 and azul < 40


@pytest.mark.parametrize(
    "override",
    [
        {"x": 0, "y": 0, "largura": 20, "altura": 10},
        {"x": 0, "y": 0, "largura": 1e12, "altura": 1e12},
        {"x": float("inf"), "y": 0, "largura": 10, "altura": 10},
        {"x": 500, "y": 0, "largura": 10, "altura": 10},
        {"x": 0, "y": 0, "largura": -10, "altura": -10},
        {"x": "0", "y": 0, "largura": 10, "altura": 10},
    ],
)
def test_override_invalido_nao_publica(entrada, override):
    with pytest.raises(ValueError):
        executar(entrada, override=override)
    assert not entrada[1].exists()


def test_orientacao_exif_antes_do_detector(entrada):
    original, _, _ = entrada
    with Image.open(original) as imagem:
        exif = Image.Exif()
        exif[274] = 6
        imagem.save(original, format="JPEG", exif=exif)

    def detector(imagem, modelo):
        assert imagem.size == (80, 120)
        assert imagem.mode == "RGB"
        vermelho, verde, azul = imagem.getpixel((20, 20))
        assert azul > vermelho and azul > verde
        return []

    resultado = processar_foto(*entrada, detector=detector)
    assert resultado["local"]["imagem_orientada"] == {"largura": 80, "altura": 120}


def test_imagem_corrompida_nao_publica(entrada):
    entrada[0].write_bytes(b"nao e imagem")
    with pytest.raises(ValueError, match="imagem"):
        executar(entrada)
    assert not entrada[1].exists()


def test_limite_20_milhoes_antes_de_decodificar(entrada):
    imagem = Image.new("1", (5001, 4000))
    imagem.save(entrada[0])
    with pytest.raises(ValueError, match="20"):
        executar(entrada)
    assert not entrada[1].exists()


def test_webp_indisponivel_falha_antes_de_abrir(entrada, monkeypatch):
    monkeypatch.setattr(features, "check", lambda recurso: False)
    entrada[0].write_bytes(b"invalido")
    with pytest.raises(RuntimeError, match="WebP"):
        executar(entrada)
    assert not entrada[1].exists()


def test_falha_detector_revisao_e_interrupcao(entrada):
    def falha(imagem, modelo):
        raise RuntimeError("inferência indisponível")

    resultado = processar_foto(*entrada, detector=falha)
    assert resultado["local"]["fallback"] == "erro_detector"
    assert "inferência indisponível" in resultado["local"]["erro_detector"]

    def interrompe(imagem, modelo):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        processar_foto(*entrada, detector=interrompe)


def test_yunet_reduz_640_cpu_e_restaura_coordenadas(monkeypatch, tmp_path):
    from types import SimpleNamespace

    import numpy as np

    from portal_eleitos.imagem import detectar_rosto

    chamadas = {}

    class Detector:
        def detect(self, matriz):
            assert matriz.shape == (320, 640, 3)
            assert tuple(matriz[0, 0]) == (0, 0, 255)
            caixa = np.zeros((1, 15))
            caixa[0, :4] = (64, 32, 128, 64)
            caixa[0, 14] = 0.97
            return None, caixa

    def criar(*argumentos):
        chamadas["argumentos"] = argumentos
        return Detector()

    modulo = SimpleNamespace(
        __version__="4.14.0",
        setNumThreads=lambda threads: None,
        FaceDetectorYN=SimpleNamespace(create=criar),
        dnn=SimpleNamespace(DNN_BACKEND_OPENCV=3, DNN_TARGET_CPU=0),
        COLOR_RGB2BGR=4,
        cvtColor=lambda matriz, codigo: matriz[:, :, ::-1],
    )
    monkeypatch.setitem(sys.modules, "cv2", modulo)
    imagem = Image.new("RGB", (1280, 641), "red")
    modelo = tmp_path / "face_detection_yunet_2023mar.onnx"
    rostos = detectar_rosto(imagem, modelo)
    assert chamadas["argumentos"][2] == (640, 320)
    assert chamadas["argumentos"][-2:] == (3, 0)
    assert rostos[0] == pytest.approx({"x": 128, "y": 64.1, "largura": 256, "altura": 128.2, "confianca": 0.97})


def test_falha_gravacao_remove_apenas_temporario_proprio(entrada, monkeypatch):
    pasta = entrada[1] / "fotos"
    pasta.mkdir(parents=True)
    arquivo_usuario = pasta / "anotacoes.txt"
    arquivo_usuario.write_text("preservar", encoding="utf-8")

    def falha(*argumentos, **opcoes):
        raise OSError("disco indisponível")

    monkeypatch.setattr(Image.Image, "save", falha)
    with pytest.raises(OSError, match="disco"):
        executar(entrada)
    assert list(pasta.iterdir()) == [arquivo_usuario]
    assert arquivo_usuario.read_text(encoding="utf-8") == "preservar"


def test_falso_positivo_fraco_nao_invalida_rosto_confiavel(entrada):
    rostos = [
        {"x": 40, "y": 20, "largura": 30, "altura": 40, "confianca": 0.94},
        {"x": 80, "y": 60, "largura": 10, "altura": 10, "confianca": 0.53},
    ]
    resultado = processar_foto(*entrada, detector=lambda imagem, modelo: rostos)
    assert resultado["local"]["metodo"] == "yunet"
    assert resultado["local"]["rosto"]["confianca"] == 0.94
    assert resultado["local"]["fallback"] is None
