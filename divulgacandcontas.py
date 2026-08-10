"""Links de candidaturas no DivulgaCandContas do TSE.

Para montar a URL, usamos `numero_sequencial` como ID da candidatura e a unidade eleitoral do CSV normalizado.
O `codigo_eleicao` do CSV não é o ID de eleição do DivulgaCandContas.
"""

BASE_URL = "https://divulgacandcontas.tse.jus.br/divulga/#/candidato"

REGIAO_POR_UF = {
    "AC": "NORTE",
    "AL": "NORDESTE",
    "AM": "NORTE",
    "AP": "NORTE",
    "BA": "NORDESTE",
    "BR": "BRASIL",
    "CE": "NORDESTE",
    "DF": "CENTRO-OESTE",
    "ES": "SUDESTE",
    "GO": "CENTRO-OESTE",
    "MA": "NORDESTE",
    "MG": "SUDESTE",
    "MS": "CENTRO-OESTE",
    "MT": "CENTRO-OESTE",
    "PA": "NORTE",
    "PB": "NORDESTE",
    "PE": "NORDESTE",
    "PI": "NORDESTE",
    "PR": "SUL",
    "RJ": "SUDESTE",
    "RN": "NORDESTE",
    "RO": "NORTE",
    "RR": "NORTE",
    "RS": "SUL",
    "SC": "SUL",
    "SE": "NORDESTE",
    "SP": "SUDESTE",
    "TO": "NORTE",
}

# IDs retornados por `/divulga/rest/v1/eleicao/ordinaria/{ano}` do TSE. NÃO são os valores da coluna `codigo_eleicao`
# do CSV de candidaturas!
CODIGO_ELEICAO_ORDINARIA_POR_ANO = {
    "2004": "14431",
    "2006": "14423",
    "2008": "14422",
    "2010": "14417",
    "2012": "1699",
    "2014": "680",
    "2016": "2",
    "2018": "2022802018",
    "2020": "2030402020",
    "2022": "2040602022",
    "2024": "2045202024",
    "2026": "20322002026",
}

CAMPOS_OBRIGATORIOS = ("ano", "numero_sequencial", "sigla_unidade_federativa", "sigla_unidade_eleitoral")


def url_candidatura(candidatura: dict, codigo_eleicao_divulgacand=None):
    """Retorna a URL do DivulgaCandContas para uma linha de candidatura.

    Os valores são mantidos como texto, pois os códigos eleitorais municipais podem ter zero à esquerda.
    Para eleição suplementar, informe `codigo_eleicao_divulgacand`: o ID da URL não está no CSV e deve ser consultado
    no endpoint de eleições suplementares do TSE.
    """
    for campo in CAMPOS_OBRIGATORIOS:
        if not candidatura.get(campo):
            raise ValueError(f"Campo obrigatório ausente: {campo}")

    uf = str(candidatura["sigla_unidade_federativa"]).upper()
    try:
        regiao = REGIAO_POR_UF[uf]
    except KeyError as exc:
        raise ValueError(f"Sigla de unidade federativa desconhecida: {uf}") from exc

    ano = str(candidatura["ano"])
    if codigo_eleicao_divulgacand is None:
        if candidatura.get("tipo_eleicao") == "ELEICAO SUPLEMENTAR":
            raise ValueError("Informe codigo_eleicao_divulgacand para uma eleição suplementar")
        try:
            codigo_eleicao_divulgacand = CODIGO_ELEICAO_ORDINARIA_POR_ANO[ano]
        except KeyError as exc:
            raise ValueError(f"Ano sem ID conhecido no DivulgaCandContas: {ano}") from exc

    numero_sequencial = candidatura["numero_sequencial"]
    unidade_eleitoral = candidatura["sigla_unidade_eleitoral"]
    return f"{BASE_URL}/{regiao}/{uf}/{codigo_eleicao_divulgacand}/{numero_sequencial}/{ano}/{unidade_eleitoral}"
