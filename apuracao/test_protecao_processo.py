import ctypes
import errno
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apuracao import protecao_processo


@pytest.fixture
def libc(monkeypatch):
    biblioteca = SimpleNamespace(prctl=Mock(return_value=0))
    carregar = Mock(return_value=biblioteca)
    monkeypatch.setattr(protecao_processo.sys, "platform", "linux")
    monkeypatch.setattr(protecao_processo.ctypes, "CDLL", carregar)
    biblioteca.carregar = carregar
    return biblioteca


def test_configura_sigkill_sem_matar_filho_com_pai_vivo(monkeypatch, libc):
    monkeypatch.setattr(protecao_processo.os, "getppid", lambda: 1234)
    matar = Mock()
    monkeypatch.setattr(protecao_processo.os, "kill", matar)

    assert protecao_processo.proteger_filho(1234) is None

    libc.carregar.assert_called_once_with(None, use_errno=True)
    libc.prctl.assert_called_once_with(1, signal.SIGKILL, 0, 0, 0)
    assert libc.prctl.argtypes == [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    assert libc.prctl.restype is ctypes.c_int
    matar.assert_not_called()


def test_pai_morreu_antes_de_configurar_protecao(monkeypatch, libc):
    def consultar_pai():
        libc.prctl.assert_called_once_with(1, signal.SIGKILL, 0, 0, 0)
        return 1

    monkeypatch.setattr(protecao_processo.os, "getppid", consultar_pai)
    monkeypatch.setattr(protecao_processo.os, "getpid", lambda: 5678)
    matar = Mock()
    monkeypatch.setattr(protecao_processo.os, "kill", matar)

    protecao_processo.proteger_filho(1234)

    matar.assert_called_once_with(5678, signal.SIGKILL)


def test_erro_prctl_preserva_errno_e_contexto(monkeypatch, libc):
    libc.prctl.return_value = -1
    monkeypatch.setattr(protecao_processo.ctypes, "get_errno", lambda: errno.EPERM)
    consultar_pai = Mock()
    matar = Mock()
    monkeypatch.setattr(protecao_processo.os, "getppid", consultar_pai)
    monkeypatch.setattr(protecao_processo.os, "kill", matar)

    with pytest.raises(OSError, match="prctl.*PR_SET_PDEATHSIG") as erro:
        protecao_processo.proteger_filho(1234)

    assert erro.value.errno == errno.EPERM
    consultar_pai.assert_not_called()
    matar.assert_not_called()


def test_plataforma_nao_linux_falha_explicitamente(monkeypatch):
    monkeypatch.setattr(protecao_processo.sys, "platform", "darwin")
    carregar = Mock()
    monkeypatch.setattr(protecao_processo.ctypes, "CDLL", carregar)

    with pytest.raises(NotImplementedError, match="Linux"):
        protecao_processo.proteger_filho(1234)

    carregar.assert_not_called()


def processo_terminou(pid: int) -> bool:
    try:
        estado = Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0]
    except FileNotFoundError:
        return True
    return estado in {"Z", "X"}


@pytest.mark.skipif(sys.platform != "linux", reason="PR_SET_PDEATHSIG requer Linux")
def test_sigkill_no_pai_encerra_filho_real():
    codigo_filho = """
import os
import sys
import time
from apuracao.protecao_processo import proteger_filho

proteger_filho(int(sys.argv[1]))
print(f"PRONTO {os.getpid()}", flush=True)
time.sleep(60)
"""
    codigo_pai = f"""
import os
import subprocess
import sys

filho = subprocess.Popen([sys.executable, "-u", "-c", {codigo_filho!r}, str(os.getpid())])
print(f"FILHO {{filho.pid}}", flush=True)
filho.wait(timeout=60)
"""
    prazo = time.perf_counter() + 3
    pai = subprocess.Popen(
        [sys.executable, "-u", "-c", codigo_pai],
        cwd=Path(__file__).resolve().parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        mensagens = {}
        pendente = b""
        while len(mensagens) < 2:
            restante = prazo - time.perf_counter()
            assert restante > 0, "Pai e filho não sinalizaram prontidão no prazo"
            legiveis, _, _ = select.select([pai.stdout], [], [], restante)
            assert legiveis, "Pai e filho não sinalizaram prontidão no prazo"
            trecho = os.read(pai.stdout.fileno(), 4096)
            assert trecho, "Árvore de processos encerrou antes da prontidão"
            pendente += trecho
            while b"\n" in pendente:
                linha, pendente = pendente.split(b"\n", 1)
                origem, pid = linha.decode().split()
                mensagens[origem] = int(pid)
        assert mensagens["PRONTO"] == mensagens["FILHO"]
        pid_filho = mensagens["FILHO"]
        assert not processo_terminou(pid_filho)

        os.kill(pai.pid, signal.SIGKILL)
        pai.wait(timeout=max(0, prazo - time.perf_counter()))
        assert pai.returncode == -signal.SIGKILL
        while not processo_terminou(pid_filho):
            restante = prazo - time.perf_counter()
            assert restante > 0, "Filho sobreviveu ao SIGKILL do pai"
            time.sleep(min(0.01, restante))
    finally:
        try:
            os.killpg(pai.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        pai.wait(timeout=0.5)
        pai.stdout.close()
