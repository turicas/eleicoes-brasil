import sys
import threading
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from apuracao import acompanhamento
from apuracao.adaptador2022 import Apuracao2022
from apuracao.modelo import Contexto


class Relogio:
    def __init__(self):
        self.agora = 0.0
        self.esperas = []

    def __call__(self):
        return self.agora

    def esperar(self, segundos):
        assert segundos > 0
        self.esperas.append(segundos)
        self.agora += segundos


def test_agenda_inicio_a_inicio_pula_atrasos_e_continua_apos_falha():
    relogio = Relogio()
    inicios = []
    duracoes = iter([8, 31, 2, 0])
    ativo = False

    def executar():
        nonlocal ativo
        assert not ativo
        ativo = True
        inicios.append(relogio())
        relogio.agora += next(duracoes)
        ativo = False
        if len(inicios) == 2:
            raise ValueError("falha temporária")

    acompanhamento.executar_periodicamente(executar, 25, relogio=relogio, espera=relogio.esperar, max_iteracoes=4)
    assert inicios == [0, 25, 75, 100]
    assert relogio.esperas == [17, 19, 23]


def test_agenda_respeita_interrupcao_e_prazo_exato():
    assert acompanhamento.proximo_prazo(0, 25, 25) == 25
    with pytest.raises(KeyboardInterrupt):
        acompanhamento.executar_periodicamente(lambda: (_ for _ in ()).throw(KeyboardInterrupt()), 25, max_iteracoes=1)


@pytest.mark.parametrize("valor", ["0", "-1", "31", "nan", "inf"])
def test_intervalo_presidente_invalido(valor):
    with pytest.raises(SystemExit):
        acompanhamento.cria_parser().parse_args(["2026", "1", "--intervalo-presidente", valor])


def test_cli_planilhas_e_credenciais(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    args = acompanhamento.cria_parser().parse_args(["2026", "1", "--data-path", "brutos"])
    assert args.intervalo_presidente == 25
    assert args.intervalo_ufs == 60
    assert args.data_path == Path("brutos")
    assert (
        acompanhamento.credenciais(2026)
        == Path(acompanhamento.__file__).parent / "credentials" / "eleicoes-2026-brasil-io-sheets.json"
    )
    assert acompanhamento.identificador_planilha(2026, 1) == "1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0"
    assert acompanhamento.identificador_planilha(2022, 1) == "1Oy1mHo78313Ls1jSKayyVWW4KeqFyS94eg3LIIe1UXU"
    assert acompanhamento.identificador_planilha(2022, 2) == "1r9UmthUo9IPSLqNN89r_fhrsXo-igSjzCMv2sViwNZo"
    with pytest.raises(ValueError, match="planilha"):
        acompanhamento.identificador_planilha(2026, 2)


def test_nao_inicia_processos_para_planilha_desconhecida(tmp_path, monkeypatch):
    def proibido(*args, **kwargs):
        pytest.fail("não deve iniciar o gerenciador")

    monkeypatch.setattr(acompanhamento, "gerenciar", proibido)
    assert acompanhamento.main(["2026", "2", "--data-path", str(tmp_path)]) == 1
    assert not list(tmp_path.iterdir())


def test_lock_exclusivo_permanece_no_disco(tmp_path):
    with (
        acompanhamento.travar_planilha(tmp_path, "sheet"),
        pytest.raises(RuntimeError, match="acompanhamento"),
        acompanhamento.travar_planilha(tmp_path, "sheet"),
    ):
        pytest.fail("lock duplicado")
    assert (tmp_path / "sheet.lock").exists()
    with acompanhamento.travar_planilha(tmp_path, "sheet"):
        pass


class Publicador:
    def __init__(self):
        self.lotes = []
        self.falhar = False

    def publicar(self, tabelas, **kwargs):
        if self.falhar:
            raise OSError("Google indisponível")
        self.lotes.append(tabelas)


class ColetaFalsa:
    def __init__(self, resultado):
        self.resultado = resultado
        self.leituras_historico = 0
        self.falhas = set()
        self.threads = set()

    def coletar(self, contexto, adaptador, url):
        self.threads.add(threading.get_ident())
        if contexto.abrangencia in self.falhas:
            raise OSError("UF indisponível")
        return replace(self.resultado, contexto=contexto)

    def historico(self, contexto, adaptador):
        self.leituras_historico += 1
        return [self.resultado, self.resultado]


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(acompanhamento.LimiteConsultas, "aguardar", lambda self: None)


@pytest.fixture
def resultado(dados_2022):
    return Apuracao2022(Contexto(2022, 1, 544, 1, "br")).ler(dados_2022)


def test_presidente_reusa_historico_e_so_confirma_publicacao_sucesso(tmp_path, resultado):
    coletor = ColetaFalsa(resultado)
    publicador = Publicador()
    rotina = acompanhamento.RotinaApuracao(
        2022, 1, "presidente", "sheet", tmp_path, coletor=coletor, planilha=publicador
    )
    publicador.falhar = True
    with pytest.raises(OSError):
        rotina.run()
    publicador.falhar = False
    rotina.run()
    rotina.run()
    assert len(publicador.lotes) == 1
    assert coletor.leituras_historico == 1
    assert [tabela.nome for tabela in publicador.lotes[0]] == ["Presidente", "LinhaDoTempo"]
    assert len(publicador.lotes[0][1].linhas) == 2
    coletor.resultado = replace(resultado, geracao="nova")
    rotina.run()
    assert len(publicador.lotes) == 2
    assert len(publicador.lotes[1][1].linhas) == 3
    rotina.close()


def test_governadores_publicam_um_lote_parcial_e_retentam_uf(tmp_path, resultado):
    coletor = ColetaFalsa(resultado)
    coletor.falhas = {"ac"}
    publicador = Publicador()
    rotina = acompanhamento.RotinaApuracao(
        2022, 1, "governador", "sheet", tmp_path, coletor=coletor, coletor_factory=lambda: coletor, planilha=publicador
    )
    try:
        rotina.run()
        assert len(publicador.lotes) == 1
        assert len(publicador.lotes[0]) == 26
        assert "AC" not in {tabela.nome for tabela in publicador.lotes[0]}
        assert threading.get_ident() not in coletor.threads
        coletor.falhas.clear()
        rotina.run()
        assert len(publicador.lotes) == 2
        assert [tabela.nome for tabela in publicador.lotes[1]] == ["AC"]
    finally:
        rotina.close()


def test_worker_autenticacao_uma_vez_timeout_curto(tmp_path, resultado, monkeypatch):
    autenticacoes = []
    construcoes = []
    cliente = object()

    def autenticar(**kwargs):
        autenticacoes.append(kwargs)
        return cliente

    def construir(client, sheet, ano, turno, **kwargs):
        construcoes.append((client, kwargs))
        return Publicador()

    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.setitem(sys.modules, "gspread", SimpleNamespace(service_account=autenticar))
    monkeypatch.setattr(acompanhamento, "Planilha", construir)
    rotina = acompanhamento.RotinaApuracao(2022, 1, "presidente", "sheet", tmp_path, coletor=ColetaFalsa(resultado))
    rotina.run()
    rotina.run()
    assert autenticacoes == [
        {
            "filename": str(
                Path(acompanhamento.__file__).parent / "credentials" / "eleicoes-2022-brasil-io-sheets.json"
            ),
            "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
        }
    ]
    assert construcoes == [(cliente, {"timeout": 8, "max_tentativas": 1})]
    coletor = rotina._novo_coletor()
    try:
        assert coletor.timeout == 8
        assert coletor.tentativas == 1
    finally:
        coletor.session.close()
        rotina.close()


def test_manager_encerra_filhos_com_join_limitado(tmp_path):
    class Evento:
        def __init__(self):
            self.acionado = False

        def set(self):
            self.acionado = True

        def wait(self, timeout):
            assert timeout == 0.2
            return True

    class Processo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.ativo = False
            self.joins = []
            self.terminado = False
            self.morto = False

        def start(self):
            self.ativo = True

        def is_alive(self):
            return self.ativo

        def join(self, timeout):
            assert 0 <= timeout <= 10
            self.joins.append(timeout)

        def terminate(self):
            self.terminado = True

        def kill(self):
            self.morto = True
            self.ativo = False

    evento = Evento()
    processos = []

    def criar_processo(**kwargs):
        processo = Processo(**kwargs)
        processos.append(processo)
        return processo

    contexto = SimpleNamespace(Event=lambda: evento, Process=criar_processo)
    args = acompanhamento.cria_parser().parse_args(["2022", "1", "--data-path", str(tmp_path)])
    assert acompanhamento.gerenciar(args, "sheet", contexto=contexto) == 0
    assert evento.acionado
    assert len(processos) == 2
    assert [processo.kwargs["args"][2] for processo in processos] == ["presidente", "governador"]
    assert [processo.kwargs["args"][5] for processo in processos] == [25, 60]
    assert all(processo.terminado and processo.morto and len(processo.joins) == 3 for processo in processos)
