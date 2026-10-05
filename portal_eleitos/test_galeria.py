import json

from portal_eleitos.exportar import exportar
from portal_eleitos.galeria import gerar_galeria
from portal_eleitos.test_exportar import bruto, fonte


def test_galeria_nome_escapado_e_referencia_local(tmp_path):
    manifesto = exportar(2026, tmp_path / "dados", fontes=[fonte()], coletar=lambda url: bruto())
    fotos = tmp_path / "fotos"
    (fotos / "fotos").mkdir(parents=True)
    hash_foto = "a" * 64
    (fotos / "fotos" / f"{hash_foto}.webp").write_bytes(b"foto")
    mapa = {"fotos": {"6259:AC:123": {"estado": "disponivel", "url": f"fotos/{hash_foto}.webp"}}}
    (fotos / "mapa-fotos.json").write_text(json.dumps(mapa))
    arquivo = gerar_galeria(manifesto, fotos)
    html = arquivo.read_text()
    assert "MARIA JOSÉ" in html
    assert f'src="fotos/{hash_foto}.webp"' in html
    assert "6259:AC:123" in html
    assert 'loading="lazy"' in html
