import json

import pytest

from apuracao.apuracao import first_sheet_rows, perc, read_data, second_sheet_rows


def test_totais_zerados_nao_inventam_percentual(dados_2022):
    for campo in ("sa", "s", "e", "ea", "tvn", "vb", "vv", "tv"):
        dados_2022[campo] = "0"
    dados_2022["cand"] = []
    assert perc(0, 0) == ""
    linhas = first_sheet_rows(read_data(dados_2022))
    assert linhas[0] == ["candidato", "vice", "numero", "votos_apurados", "perc", "dif. próx."]
    assert linhas[-1] == [0, "", 0, "", 0, "", 0]


@pytest.mark.parametrize("invalido_primeiro", [True, False])
def test_json_invalido_interrompe_sem_reutilizar_dados(dados_2022, tmp_path, invalido_primeiro):
    valido = tmp_path / "br-r-2022-10-02 18:30:00-03:00.json"
    valido.write_text(json.dumps(dados_2022))
    invalido = tmp_path / "br-r-2022-10-02 18:31:00-03:00.json"
    invalido.write_text("{")
    arquivos = [invalido] if invalido_primeiro else [valido, invalido]
    with pytest.raises(ValueError, match=invalido.name):
        second_sheet_rows(arquivos)
