import subprocess
import sys


def test_ajuda_nao_importa_http_google_ou_dataclasses():
    codigo = """
import sys
from apuracao.cli import main
try:
    main(['--help'])
except SystemExit as erro:
    assert erro.code == 0
assert not {'requests', 'gspread', 'json', 'pathlib'}.intersection(sys.modules)
"""
    subprocess.run([sys.executable, "-c", codigo], capture_output=True, check=True, timeout=3)
