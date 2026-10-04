import os
import signal
import subprocess
import sys
import time


def test_ctrl_c_encerra_mesmo_filhos_ignorando_sinais(tmp_path):
    codigo = """
import multiprocessing
import signal
import time
from apuracao.acompanhamento import cria_parser, gerenciar

def travado(*args):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print("FILHO_PRONTO", flush=True)
    time.sleep(60)

if __name__ == "__main__":
    import apuracao.acompanhamento as modulo
    modulo._trabalhar = travado
    args = cria_parser().parse_args(["2022", "1", "--data-path", __import__("sys").argv[1]])
    raise SystemExit(gerenciar(args, "teste", contexto=multiprocessing.get_context("fork")))
"""
    processo = subprocess.Popen(
        [sys.executable, "-u", "-c", codigo, str(tmp_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        import select

        limite = time.perf_counter() + 4
        prontos = 0
        while prontos < 2 and time.perf_counter() < limite:
            if select.select([processo.stdout], [], [], 0.2)[0] and b"FILHO_PRONTO" in processo.stdout.readline():
                prontos += 1
        assert prontos == 2
        inicio = time.perf_counter()
        os.kill(processo.pid, signal.SIGINT)
        stdout, stderr = processo.communicate(timeout=4)
        assert processo.returncode == 130, (stdout, stderr)
        assert time.perf_counter() - inicio < 4
    finally:
        if processo.poll() is None:
            os.killpg(processo.pid, signal.SIGKILL)
            processo.communicate(timeout=2)
