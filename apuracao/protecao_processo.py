import ctypes
import os
import signal
import sys

PR_SET_PDEATHSIG = 1


def proteger_filho(pid_pai: int) -> None:
    """Encerra o filho com SIGKILL se o pai morrer, inclusive durante a configuração. Requer Linux."""
    if sys.platform != "linux":
        raise NotImplementedError("A proteção de processos com PR_SET_PDEATHSIG requer Linux")

    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0) != 0:
        numero_erro = ctypes.get_errno()
        raise OSError(numero_erro, f"prctl(PR_SET_PDEATHSIG, SIGKILL): {os.strerror(numero_erro)}")

    if os.getppid() != pid_pai:
        os.kill(os.getpid(), signal.SIGKILL)
