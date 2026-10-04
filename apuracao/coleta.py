import json
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests

from .modelo import Contexto, Resultado


class Coletor:
    def __init__(self, raiz: Path, session=None, timeout=30, tentativas=3, sleep=time.sleep):
        if tentativas < 1:
            raise ValueError("tentativas deve ser positivo")
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session() if session is None else session
        self.timeout = timeout
        self.tentativas = tentativas
        self.sleep = sleep
        self._headers_padrao = session is None

    def _espera(self, resposta, tentativa: int) -> float:
        espera = min(2 ** min(tentativa, 6), 60)
        valor = resposta.headers.get("Retry-After") if resposta is not None else None
        if valor is not None:
            try:
                espera = float(valor)
            except ValueError:
                try:
                    data = parsedate_to_datetime(valor)
                    if data.tzinfo is None:
                        data = data.replace(tzinfo=timezone.utc)
                    espera = (data - datetime.now(timezone.utc)).total_seconds()
                except (ValueError, TypeError, OverflowError):
                    pass
        return max(0, min(espera, 60))

    def buscar_json(self, url: str) -> dict:
        url_consulta = url
        parametros = {"timeout": (self.timeout, self.timeout)}
        if self._headers_padrao:
            from extractors import DEFAULT_HEADERS

            parametros["headers"] = dict(DEFAULT_HEADERS)
        if urlsplit(url).hostname == "resultados.tse.jus.br":
            separador = "&" if "?" in url else "?"
            url_consulta = f"{url}{separador}_={time.time_ns()}"
            parametros.setdefault("headers", {}).update({"Cache-Control": "no-cache", "Pragma": "no-cache"})
        for tentativa in range(self.tentativas):
            resposta = None
            try:
                resposta = self.session.get(url_consulta, **parametros)
                resposta.raise_for_status()
            except (requests.Timeout, requests.ConnectionError):
                if tentativa + 1 == self.tentativas:
                    raise
                self.sleep(self._espera(resposta, tentativa))
                continue
            except requests.HTTPError:
                if resposta is None or not (resposta.status_code == 429 or 500 <= resposta.status_code < 600):
                    raise
                if tentativa + 1 == self.tentativas:
                    raise
                self.sleep(self._espera(resposta, tentativa))
                continue
            try:
                try:
                    dados = resposta.json(parse_float=Decimal)
                except TypeError:
                    dados = resposta.json()
            except ValueError as erro:
                raise ValueError(f"JSON inválido em {url}: {erro}") from erro
            if not isinstance(dados, dict):
                raise ValueError(f"JSON inválido em {url}: esperado objeto")  # noqa: TRY004
            return dados
        raise RuntimeError("Nenhuma tentativa executada")

    def _pasta(self, contexto: Contexto) -> Path:
        abrangencia = quote(contexto.abrangencia, safe="")
        if abrangencia in ("", ".", ".."):
            raise ValueError("abrangência inválida")
        return self.raiz / str(contexto.ano) / f"turno-{contexto.turno}" / f"cargo-{contexto.cargo}" / abrangencia

    def coletar(self, contexto: Contexto, adaptador, url: str) -> Resultado:
        dados = self.buscar_json(url)
        resultado = adaptador.ler(dados)
        if resultado.contexto != contexto:
            raise ValueError("Contexto do adaptador difere do contexto da coleta")
        pasta = self._pasta(contexto)
        pasta.mkdir(parents=True, exist_ok=True)
        fonte = quote(Path(urlsplit(url).path).stem or "fonte", safe="")
        timestamp = resultado.gerada_em.strftime("%Y%m%dT%H%M%S%f%z")
        geracao = dados.get("idg")
        sufixo = f"-{quote(str(geracao), safe='')}" if geracao is not None else ""
        destino = pasta / f"{fonte}-{timestamp}{sufixo}.json"
        conteudo = json.dumps(dados, default=str, ensure_ascii=False, indent=2)
        temporario = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=pasta, suffix=".tmp", delete=False
            ) as arquivo:
                temporario = Path(arquivo.name)
                arquivo.write(conteudo)
            temporario.replace(destino)
        finally:
            if temporario is not None:
                temporario.unlink(missing_ok=True)
        return resultado

    def historico(self, contexto: Contexto, adaptador) -> list[Resultado]:
        resultados = []
        for arquivo in sorted(self._pasta(contexto).glob("*.json")):
            if not arquivo.is_file():
                continue
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"), parse_float=Decimal)
                if not isinstance(dados, dict):
                    raise ValueError("esperado objeto")  # noqa: TRY004
                resultado = adaptador.ler(dados)
                if resultado.contexto != contexto:
                    raise ValueError("Contexto do adaptador difere do contexto do histórico")
            except (ValueError, KeyError, TypeError) as erro:
                raise ValueError(f"JSON inválido em {arquivo}: {erro}") from erro
            resultados.append(resultado)
        resultados.sort(key=lambda resultado: resultado.gerada_em)
        historico = []
        vistos = set()
        for resultado in resultados:
            chave = (resultado.contexto, resultado.geracao if resultado.geracao is not None else resultado.gerada_em)
            if chave not in vistos:
                vistos.add(chave)
                historico.append(resultado)
        return historico
