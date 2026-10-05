import json
import tempfile
import threading
import time
from pathlib import Path

import requests


class ClienteTSE:
    """Sessões por thread e início de HTTP limitado, sem depender do coletor da planilha."""

    def __init__(self, timeout: float = 10, por_segundo: float = 10):
        self.timeout = timeout
        self._intervalo = 1 / por_segundo
        self._proximo = 0.0
        self._lock = threading.Lock()
        self._local = threading.local()
        self._sessoes = []

    def __call__(self, url: str) -> dict:
        with self._lock:
            agora = time.perf_counter()
            prazo = max(agora, self._proximo)
            self._proximo = prazo + self._intervalo
        if prazo > agora:
            time.sleep(prazo - agora)
        if not hasattr(self._local, "session"):
            self._local.session = requests.Session()
            self._sessoes.append(self._local.session)
        response = self._local.session.get(
            url,
            params={"_": time.time_ns()},
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            timeout=(self.timeout, self.timeout),
        )
        response.raise_for_status()
        dados = response.json()
        if not isinstance(dados, dict):
            raise ValueError(f"JSON não é objeto: {url}")  # noqa: TRY004
        return dados

    def close(self):
        for session in self._sessoes:
            session.close()


def salvar_json(destino: Path, dados) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destino.parent, delete=False, suffix=".tmp"
        ) as stream:
            temporario = Path(stream.name)
            stream.write(json.dumps(dados, ensure_ascii=False, indent=2, default=str) + "\n")
        temporario.replace(destino)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
