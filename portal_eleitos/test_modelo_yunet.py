import pytest

from portal_eleitos.modelo_yunet import baixar


def test_modelo_existente_invalido_nao_e_sobrescrito(tmp_path):
    arquivo = tmp_path / "modelo.onnx"
    arquivo.write_bytes(b"modelo diferente")
    with pytest.raises(ValueError, match="não será sobrescrito"):
        baixar(arquivo)
    assert arquivo.read_bytes() == b"modelo diferente"


def test_checksum_download_invalido_nao_salva(tmp_path, monkeypatch):
    class Resposta:
        content = b"modelo errado"

        def raise_for_status(self):
            return None

    monkeypatch.setattr("portal_eleitos.modelo_yunet.requests.get", lambda url, timeout: Resposta())
    with pytest.raises(ValueError, match="Checksum"):
        baixar(tmp_path / "modelo.onnx")
    assert not (tmp_path / "modelo.onnx").exists()
