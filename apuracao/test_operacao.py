from dataclasses import replace

import requests

from apuracao.adaptador2022 import Apuracao2022
from apuracao.apresentacao import tabela_historico
from apuracao.cli import cria_parser, executar, main
from apuracao.modelo import Contexto
from apuracao.test_cli import ColetaSimulada


def test_falha_http_governador_nao_impede_outros(dados_2022, capsys):
    class ColetaComFalha(ColetaSimulada):
        def coletar(self, contexto, adaptador, url):
            if contexto.abrangencia == "ac":
                raise requests.HTTPError("503 temporário")
            return super().coletar(contexto, adaptador, url)

    args = cria_parser().parse_args(["2022", "1", "governador", "--print-only"])
    assert executar(args, coletor=ColetaComFalha(dados_2022)) == 1
    assert "AC" in capsys.readouterr().err


def test_main_erro_google_tem_diagnostico_sem_traceback(monkeypatch, capsys):
    class ErroGoogle(Exception):
        pass

    def falhar(args):
        raise ErroGoogle("Planilha não compartilhada")

    monkeypatch.setattr("apuracao.cli.executar", falhar)
    assert main(["2026", "1", "presidente", "identificador"]) == 1
    assert "compartilhada" in capsys.readouterr().err


def test_historico_colunas_nao_dependem_da_ordem_por_votos(dados_2022):
    resultado = Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)
    invertido = replace(resultado, candidatos=tuple(reversed(resultado.candidatos)))
    assert tabela_historico([resultado]).linhas[0] == tabela_historico([invertido]).linhas[0]
