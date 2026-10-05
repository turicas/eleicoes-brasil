import unittest

import pytest

from divulgacandcontas import url_candidatura
from extractors import CandidaturaExtractor


class DivulgaCandContasTestCase(unittest.TestCase):
    def test_gera_url_de_candidatura_municipal(self):
        candidatura = {
            "ano": "2024",
            "codigo_eleicao": "619",
            "numero_sequencial": "160001990123",
            "sigla_unidade_federativa": "PR",
            "sigla_unidade_eleitoral": "75353",
        }

        self.assertEqual(
            url_candidatura(candidatura),
            "https://divulgacandcontas.tse.jus.br/divulga/#/candidato/SUL/PR/2045202024/160001990123/2024/75353",
        )

    def test_gera_url_de_candidatura_estadual_e_federal(self):
        estadual = {
            "ano": "2022",
            "codigo_eleicao": "546",
            "numero_sequencial": "260001693738",
            "sigla_unidade_federativa": "SE",
            "sigla_unidade_eleitoral": "SE",
        }
        federal = {
            "ano": "2022",
            "codigo_eleicao": "545",
            "numero_sequencial": "280001618036",
            "sigla_unidade_federativa": "BR",
            "sigla_unidade_eleitoral": "BR",
        }

        self.assertEqual(url_candidatura(estadual).split("/")[6], "NORDESTE")
        self.assertIn("/2040602022/", url_candidatura(estadual))
        self.assertEqual(url_candidatura(federal).split("/")[6], "BRASIL")
        self.assertIn("/2040602022/", url_candidatura(federal))

    def test_exige_id_do_divulgacand_em_eleicao_suplementar(self):
        candidatura = {
            "ano": "2014",
            "tipo_eleicao": "ELEICAO SUPLEMENTAR",
            "numero_sequencial": "270000010435",
            "sigla_unidade_federativa": "TO",
            "sigla_unidade_eleitoral": "TO",
        }

        with self.assertRaisesRegex(ValueError, "codigo_eleicao_divulgacand"):
            url_candidatura(candidatura)
        self.assertIn("/91575/", url_candidatura(candidatura, codigo_eleicao_divulgacand="91575"))

    def test_rejeita_campos_ausentes_e_unidade_federativa_desconhecida(self):
        with self.assertRaisesRegex(ValueError, "numero_sequencial"):
            url_candidatura(
                {
                    "ano": "2024",
                    "codigo_eleicao": "1",
                    "sigla_unidade_federativa": "PR",
                    "sigla_unidade_eleitoral": "3",
                }
            )
        with self.assertRaisesRegex(ValueError, "unidade federativa"):
            url_candidatura(
                {
                    "ano": "2024",
                    "codigo_eleicao": "1",
                    "numero_sequencial": "2",
                    "sigla_unidade_federativa": "XX",
                    "sigla_unidade_eleitoral": "3",
                }
            )


@pytest.fixture
def candidatura_suplementar():
    return {
        "ano": "2024",
        "numero_sequencial": "123",
        "codigo_cargo": "6",
        "cargo": "DEPUTADO FEDERAL",
        "cpf": "12345678901",
        "nome": "JOÃO D´ÁVILA",
        "nome_urna": "JOÃO",
        "data_eleicao": "06/10/2024",
        "data_aceite": "",
        "data_nascimento": "",
        "sigla_unidade_federativa": "SP",
        "sigla_unidade_federativa_nascimento": "SP",
        "titulo_eleitoral": "",
        "candidatura_inserida_urna": "SIM",
        "etnia": "",
        "estado_civil": "",
        "genero": "",
        "grau_instrucao": "",
        "unidade_eleitoral": "SÃO PAULO",
        "tipo_abrangencia_eleicao": "FEDERAL",
        "tipo_eleicao": "ELEIÇÃO ORDINÁRIA",
        "tipo_agremiacao": "PARTIDO ISOLADO",
        "ocupacao": "",
    }


def converte_candidatura_suplementar(candidatura_suplementar):
    campos = list(candidatura_suplementar)
    return CandidaturaExtractor().convert_row(campos, campos)(list(candidatura_suplementar.values()))


@pytest.mark.parametrize(
    "tipo_eleicao",
    ["ELEICAO SUPLEMENTAR", "ELEIÇÃO SUPLEMENTAR", "Eleição suplementar", " eleição SUPLEMENTAR "],
)
def test_suplementar_exige_identificador_especifico(candidatura_suplementar, tipo_eleicao):
    from divulgacandcontas import url_candidatura

    candidatura_suplementar.update(tipo_eleicao=tipo_eleicao, sigla_unidade_eleitoral="SP")
    with pytest.raises(ValueError, match="codigo_eleicao_divulgacand"):
        url_candidatura(candidatura_suplementar)
    assert "/987/" in url_candidatura(candidatura_suplementar, codigo_eleicao_divulgacand="987")


def test_suplementar_convertida_exige_identificador_especifico(candidatura_suplementar):
    from divulgacandcontas import url_candidatura

    candidatura_suplementar.update(tipo_eleicao="ELEIÇÃO SUPLEMENTAR", sigla_unidade_eleitoral="SP")
    with pytest.raises(ValueError, match="codigo_eleicao_divulgacand"):
        url_candidatura(converte_candidatura_suplementar(candidatura_suplementar))
