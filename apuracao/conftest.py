import pytest


@pytest.fixture
def dados_2022():
    return {
        "dg": "02/10/2022",
        "hg": "18:30:00",
        "sa": "50",
        "s": "100",
        "e": "200",
        "ea": "100",
        "tvn": "5",
        "vb": "5",
        "vv": "90",
        "tv": "100",
        "cand": [
            {"nm": "LULA", "nv": "VICE A", "n": "13", "vap": "54", "pvap": "60,00"},
            {"nm": "JAIR BOLSONARO", "nv": "VICE B &amp; C", "n": "22", "vap": "36", "pvap": "40,00"},
        ],
    }
