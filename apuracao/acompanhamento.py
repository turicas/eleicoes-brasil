"""Acompanhamento contínuo com presidente e UFs isolados em processos próprios."""

import argparse  # noqa: I001 - preserva largura do isort local
import fcntl
import json
import math
import multiprocessing
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .adaptador2022 import Apuracao2022
from .adaptador2026 import Apuracao2026
from .agregacao import somar_presidente
from .apresentacao import tabela_historico, tabela_resultado, titulo_resultado
from .coleta import Coletor
from .configuracao import codigo_eleicao, contextos_eleicao, url_municipios, url_resultado
from .cor_aba import cor_resultado
from .formatacao import UFS
from .modelo import Contexto
from .planilha import Planilha

URL_CONFIGURACAO = "https://resultados.tse.jus.br/oficial/comum/config/ele-c.json"
PLANILHAS = {
    (2026, 1): "1RGi20p_QECrdRo_KJgxhSDo7zO2wnIFuxRqKs2XrWa0",
    (2022, 1): "1Oy1mHo78313Ls1jSKayyVWW4KeqFyS94eg3LIIe1UXU",
    (2022, 2): "1r9UmthUo9IPSLqNN89r_fhrsXo-igSjzCMv2sViwNZo",
}


def identificador_planilha(ano: int, turno: int) -> str:
    try:
        return PLANILHAS[ano, turno]
    except KeyError as erro:
        raise ValueError(f"Não há planilha cadastrada para {ano}, turno {turno}") from erro


def credenciais(ano: int) -> Path:
    return Path(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or str(Path(__file__).parent / "credentials" / f"eleicoes-{ano}-brasil-io-sheets.json")
    )


def _intervalo(valor: str) -> float:
    try:
        intervalo = float(valor)
    except ValueError as erro:
        raise argparse.ArgumentTypeError("Intervalo deve ser numérico") from erro
    if not math.isfinite(intervalo) or intervalo <= 0:
        raise argparse.ArgumentTypeError("Intervalo deve ser finito e positivo")
    return intervalo


def _intervalo_presidente(valor: str) -> float:
    intervalo = _intervalo(valor)
    if intervalo > 30:
        raise argparse.ArgumentTypeError("Intervalo de presidente não pode exceder 30 segundos")
    return intervalo


def cria_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ano", type=int, choices=(2022, 2026))
    parser.add_argument("turno", type=int, choices=(1, 2))
    parser.add_argument("--intervalo-presidente", type=_intervalo_presidente, default=25)
    parser.add_argument("--intervalo-ufs", type=_intervalo, default=60)
    parser.add_argument(
        "--presidente-por-uf", action="store_true", help="Soma 27 UFs + exterior em vez do JSON nacional (2026)"
    )
    parser.add_argument("--data-path", type=Path, default=Path(__file__).parent / "data")
    return parser


def proximo_prazo(prazo: float, intervalo: float, agora: float) -> float:
    """Avança na grade original, descartando slots vencidos sem acumular execuções."""
    seguinte = prazo + intervalo
    if seguinte < agora:
        seguinte += math.ceil((agora - seguinte) / intervalo) * intervalo
    return seguinte


def executar_periodicamente(
    executar: Callable[[], None],
    intervalo: float,
    *,
    relogio: Callable[[], float] = time.perf_counter,
    espera: Callable[[float], object] = time.sleep,
    parar: Callable[[], bool] = lambda: False,
    max_iteracoes: int | None = None,
) -> None:
    """Executa sequencialmente; falhas de um ciclo não encerram a rotina."""
    if not math.isfinite(intervalo) or intervalo <= 0:
        raise ValueError("Intervalo deve ser finito e positivo")
    prazo = relogio()
    iteracoes = 0
    while not parar() and (max_iteracoes is None or iteracoes < max_iteracoes):
        restante = prazo - relogio()
        if restante > 0:
            espera(restante)
            if parar():
                break
            if relogio() < prazo:
                continue
        try:
            executar()
        except KeyboardInterrupt:
            raise
        except Exception as erro:  # noqa: BLE001 - fronteira de ciclo: preserva acompanhamento
            print(f"Falha no ciclo: {erro}", file=sys.stderr, flush=True)
        iteracoes += 1
        prazo = proximo_prazo(prazo, intervalo, relogio())


@contextmanager
def travar_planilha(data_path: Path, identificador: str):
    """Mantém flock no pai até encerrar os filhos; o arquivo não é removido."""
    data_path.mkdir(parents=True, exist_ok=True)
    with (data_path / f"{identificador}.lock").open("a+", encoding="utf-8") as arquivo:
        try:
            fcntl.flock(arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as erro:
            raise RuntimeError("Já existe acompanhamento desta planilha neste diretório") from erro
        try:
            yield
        finally:
            fcntl.flock(arquivo, fcntl.LOCK_UN)


class LimiteConsultas:
    """Reserva inícios de consultas entre threads, mantendo folga abaixo do limite por IP do TSE."""

    def __init__(self, por_segundo: float = 20, *, relogio=time.perf_counter, espera=time.sleep):
        self._intervalo = 1 / por_segundo
        self._relogio = relogio
        self._espera = espera
        self._proximo = 0.0
        self._lock = threading.Lock()

    def aguardar(self):
        with self._lock:
            agora = self._relogio()
            inicio = max(agora, self._proximo)
            self._proximo = inicio + self._intervalo
        if inicio > agora:
            self._espera(inicio - agora)


class RotinaApuracao:
    """Reutiliza contexto, clientes, histórico e executor durante toda a vida do processo."""

    def __init__(
        self,
        ano: int,
        turno: int,
        tipo: str,
        sheet: str,
        data_path: Path,
        *,
        coletor=None,
        planilha=None,
        coletor_factory=None,
        presidente_por_uf=False,
    ):
        if tipo not in ("presidente", "governador"):
            raise ValueError("Tipo deve ser presidente ou governador")
        if presidente_por_uf and ano != 2026:
            raise ValueError("--presidente-por-uf exige 2026")
        self.presidente_por_uf = presidente_por_uf and tipo == "presidente"
        self.ano = ano
        self.turno = turno
        self.tipo = tipo
        self.sheet = sheet
        self.data_path = Path(data_path)
        self.coletor = coletor
        self.planilha = planilha
        self._coletor_factory = coletor_factory or self._novo_coletor
        self._local = threading.local()
        self._coletores = []
        self._executor = None
        self._contextos = None
        self._diretorios = None
        self._publicados = {}
        self._historico = None
        self._vistos = set()
        self._cor_publicada = None
        self._definicao_presidente = None
        self._definicao_publicada = None
        self._limite = LimiteConsultas()

    def _novo_coletor(self):
        return Coletor(self.data_path, timeout=8, tentativas=1)

    def configurar(self) -> None:
        """Consulta EA11 e EA12 apenas na inicialização bem-sucedida, fora dos ciclos seguintes."""
        if self.coletor is None:
            self.coletor = self._novo_coletor()
        if self._contextos is None:
            cargo = 1 if self.tipo == "presidente" else 3
            configuracao = self.coletor.buscar_json(URL_CONFIGURACAO) if self.ano == 2026 else {}
            diretorios = configuracao.get("arq") or None
            municipios = None
            if self.ano == 2026 and cargo == 3:
                codigo = codigo_eleicao(configuracao, self.ano, self.turno, cargo)
                municipios = self.coletor.buscar_json(url_municipios(self.ano, codigo, diretorios))
            contextos = contextos_eleicao(configuracao, self.ano, self.turno, cargo, municipios)
            if self.presidente_por_uf:
                codigo = codigo_eleicao(configuracao, self.ano, self.turno, 1)
                contextos = [
                    Contexto(self.ano, self.turno, codigo, 1, area)
                    for area in sorted([uf.lower() for uf in UFS] + ["zz"])
                ]
            self._contextos = contextos
            self._diretorios = diretorios
        if self.planilha is None:
            import gspread

            client = gspread.service_account(
                filename=str(credenciais(self.ano)), scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            self.planilha = Planilha(client, self.sheet, self.ano, self.turno, timeout=8, max_tentativas=1)
        if (self.tipo == "governador" or self.presidente_por_uf) and self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="apuracao-uf")

    @staticmethod
    def _chave(resultado):
        return resultado.contexto, resultado.geracao if resultado.geracao is not None else resultado.gerada_em

    def _coletar(self, contexto, *, paralelo=False):
        coletor = self.coletor
        if paralelo:
            if not hasattr(self._local, "coletor"):
                self._local.coletor = self._coletor_factory()
                self._coletores.append(self._local.coletor)
            coletor = self._local.coletor
        classe = Apuracao2022 if self.ano == 2022 else Apuracao2026
        self._limite.aguardar()
        resultado = coletor.coletar(contexto, classe(contexto), url_resultado(contexto, self._diretorios))
        return resultado

    def _registrar_historico(self, resultado):
        if self._historico is None:
            classe = Apuracao2022 if self.ano == 2022 else Apuracao2026
            anteriores = self.coletor.historico(resultado.contexto, classe(resultado.contexto))
            anteriores.extend(self._ler_historico_somas())
            anteriores.sort(key=lambda item: item.gerada_em)
            self._historico = []
            for anterior in anteriores:
                chave = self._chave(anterior)
                if chave not in self._vistos:
                    self._historico.append(anterior)
                    self._vistos.add(chave)
        chave = self._chave(resultado)
        if chave not in self._vistos:
            self._historico.append(resultado)
            self._vistos.add(chave)

    def _pasta_somas(self):
        return self.data_path / str(self.ano) / f"turno-{self.turno}" / "soma-presidente"

    def _salvar_fontes_soma(self, fontes, resultado):
        import tempfile
        from dataclasses import asdict

        pasta = self._pasta_somas()
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{resultado.geracao}.json"
        if destino.exists():
            return
        temporario = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=pasta, delete=False, suffix=".tmp"
            ) as arquivo:
                temporario = Path(arquivo.name)
                json.dump(
                    {"capturada_em": resultado.capturada_em, "fontes": [asdict(fonte) for fonte in fontes]},
                    arquivo,
                    default=str,
                    ensure_ascii=False,
                    indent=2,
                )
            temporario.replace(destino)
        finally:
            if temporario:
                temporario.unlink(missing_ok=True)

    def _ler_historico_somas(self):
        from .agregacao import fontes_salvas

        resultados = []
        for arquivo in self._pasta_somas().glob("*.json"):
            try:
                dados = json.loads(arquivo.read_text())
                if isinstance(dados, dict):
                    capturada = datetime.fromisoformat(dados["capturada_em"])
                    fontes = dados["fontes"]
                else:
                    capturada = datetime.fromtimestamp(arquivo.stat().st_mtime, timezone.utc).astimezone(
                        timezone(timedelta(hours=-3))
                    )
                    fontes = dados
                resultados.append(replace(somar_presidente(fontes_salvas(fontes)), capturada_em=capturada))
            except (ValueError, KeyError, TypeError) as erro:
                raise ValueError(f"Histórico agregado inválido: {arquivo}: {erro}") from erro
        return sorted(resultados, key=lambda resultado: resultado.gerada_em)

    def _consultar_cor_presidente(self, resultado):
        contexto = resultado.contexto
        dados = self.coletor.buscar_json(url_resultado(contexto, self._diretorios))
        self._definicao_presidente = Apuracao2026(contexto).ler(dados)
        return cor_resultado(self._definicao_presidente)

    def run(self) -> None:
        inicio = time.perf_counter()
        print(f"{self.tipo}: início", file=sys.stderr, flush=True)
        alterados = []
        concluidos = 0
        cor_presidente = None
        definicao_chave = None
        try:
            self.configurar()
            if self.tipo == "presidente":
                if self.presidente_por_uf:
                    futuros = {
                        self._executor.submit(self._coletar, contexto, paralelo=True): contexto
                        for contexto in self._contextos
                    }
                    fontes = []
                    falhas = []
                    for futuro in as_completed(futuros):
                        try:
                            fontes.append(futuro.result())
                        except Exception as erro:  # noqa: BLE001 - não publica soma parcial
                            falhas.append(f"{futuros[futuro].abrangencia}: {erro}")
                    if falhas:
                        raise ValueError("Fontes indisponíveis; soma não publicada: " + "; ".join(falhas))
                    resultado = replace(
                        somar_presidente(fontes),
                        capturada_em=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))),
                    )
                    self._salvar_fontes_soma(fontes, resultado)
                    try:
                        cor_presidente = self._consultar_cor_presidente(resultado)
                    except Exception as erro:  # noqa: BLE001 - falha de cor não interrompe votos; preserva cor anterior
                        print(f"Cor presidencial não atualizada: {erro}", file=sys.stderr, flush=True)
                else:
                    resultado = self._coletar(self._contextos[0])
                concluidos = 1
                self._registrar_historico(resultado)
                if self._definicao_presidente is not None:
                    nacional = self._definicao_presidente
                    definicao_chave = (nacional.geracao, nacional.matematicamente_definida, nacional.finalizada)
                if (
                    self._publicados.get(resultado.contexto) != self._chave(resultado)
                    or definicao_chave != self._definicao_publicada
                ) or (cor_presidente is not None and cor_presidente != self._cor_publicada):
                    alterados.append(resultado)
            else:
                futuros = {
                    self._executor.submit(self._coletar, contexto, paralelo=True): contexto
                    for contexto in self._contextos
                }
                for futuro in as_completed(futuros):
                    contexto = futuros[futuro]
                    concluidos += 1
                    try:
                        resultado = futuro.result()
                    except KeyboardInterrupt:
                        raise
                    except Exception as erro:  # noqa: BLE001 - mantém abas das UFs com falha
                        print(
                            f"UFs {concluidos}/{len(futuros)} {contexto.abrangencia.upper()}: {erro}",
                            file=sys.stderr,
                            flush=True,
                        )
                        continue
                    decorrido = max(time.perf_counter() - inicio, 0.001)
                    ritmo = concluidos / decorrido
                    eta = (len(futuros) - concluidos) / ritmo
                    print(
                        f"UFs {concluidos}/{len(futuros)} ({100 * concluidos / len(futuros):.0f}%), "
                        f"{ritmo:.1f}/s ETA: {eta:.1f}s | {contexto.abrangencia.upper()}: "
                        f"fonte={resultado.geracao} data={resultado.gerada_em}",
                        file=sys.stderr,
                        flush=True,
                    )
                    if self._publicados.get(resultado.contexto) != self._chave(resultado):
                        alterados.append(resultado)
                alterados.sort(key=lambda resultado: resultado.contexto.abrangencia)
            if alterados:
                tabelas = [
                    tabela_resultado(
                        resultado,
                        "Presidente" if self.tipo == "presidente" else resultado.contexto.abrangencia.upper(),
                        definicao_oficial=self._definicao_presidente if self.presidente_por_uf else None,
                    )
                    for resultado in alterados
                ]
                if self.presidente_por_uf:
                    tabelas[0].cor_aba = cor_presidente
                titulo = None
                if self.tipo == "presidente":
                    tabelas.append(tabela_historico(self._historico))
                    titulo = titulo_resultado(alterados[0])
                self.planilha.publicar(tabelas, titulo=titulo)
                self._definicao_publicada = definicao_chave
                if cor_presidente is not None:
                    self._cor_publicada = cor_presidente
                for resultado in alterados:
                    self._publicados[resultado.contexto] = self._chave(resultado)
            if self.tipo == "presidente" and concluidos:
                print(f"presidente: fonte={resultado.geracao} data={resultado.gerada_em}", file=sys.stderr, flush=True)
        finally:
            duracao = time.perf_counter() - inicio
            print(
                f"{self.tipo}: fim em {duracao:.2f}s; coletados={concluidos} alterados={len(alterados)}",
                file=sys.stderr,
                flush=True,
            )

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
        for coletor in [self.coletor, *self._coletores]:
            session = getattr(coletor, "session", None)
            if session is not None:
                session.close()
        client = getattr(self.planilha, "client", None)
        session = getattr(getattr(client, "http_client", None), "session", None)
        if session is not None:
            session.close()


def _trabalhar(ano, turno, tipo, sheet, data_path, intervalo, encerramento, presidente_por_uf=False, pid_pai=None):
    if pid_pai is not None:
        from .protecao_processo import proteger_filho

        proteger_filho(pid_pai)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(130))
    rotina = RotinaApuracao(ano, turno, tipo, sheet, data_path, presidente_por_uf=presidente_por_uf)
    try:
        executar_periodicamente(rotina.run, intervalo, espera=encerramento.wait, parar=encerramento.is_set)
    except KeyboardInterrupt:
        encerramento.set()
    finally:
        rotina.close()


def gerenciar(args, sheet: str, *, contexto=None) -> int:
    """Pai possui lock e encerra filhos com prazo limitado, mesmo após sinais."""
    contexto = contexto or multiprocessing.get_context("spawn")
    encerramento = contexto.Event()
    processos = []
    anteriores = {}
    interrompido = False
    sinais = 0

    def interromper(sinal, frame):
        nonlocal interrompido, sinais
        interrompido = True
        sinais += 1
        if sinais == 1:
            print("Encerrando acompanhamento...", file=sys.stderr, flush=True)
        else:
            for processo in processos:
                if processo.is_alive():
                    processo.kill()

    with travar_planilha(args.data_path, sheet):
        print(
            "Pare o loop bash antigo antes de usar este acompanhamento; ele não é encerrado automaticamente.",
            file=sys.stderr,
            flush=True,
        )
        for sinal in (signal.SIGINT, signal.SIGTERM):
            anteriores[sinal] = signal.signal(sinal, interromper)
        try:
            for tipo, intervalo in (("presidente", args.intervalo_presidente), ("governador", args.intervalo_ufs)):
                processo = contexto.Process(
                    target=_trabalhar,
                    args=(
                        args.ano,
                        args.turno,
                        tipo,
                        sheet,
                        args.data_path,
                        intervalo,
                        encerramento,
                        args.presidente_por_uf,
                        os.getpid(),
                    ),
                    name=f"apuracao-{tipo}",
                )
                processo.start()
                processos.append(processo)
            while not interrompido and not encerramento.wait(0.2):
                if any(not processo.is_alive() for processo in processos):
                    print("Processo de apuração encerrado inesperadamente", file=sys.stderr, flush=True)
                    return 1
            return 130 if interrompido else 0
        except KeyboardInterrupt:
            return 130
        finally:
            encerramento.set()
            prazo = time.perf_counter() + 0.5
            for processo in processos:
                processo.join(timeout=max(0, prazo - time.perf_counter()))
            for processo in processos:
                if processo.is_alive():
                    processo.terminate()
            prazo = time.perf_counter() + 0.5
            for processo in processos:
                processo.join(timeout=max(0, prazo - time.perf_counter()))
                if processo.is_alive():
                    processo.kill()
                    processo.join(timeout=1)
            for sinal, anterior in anteriores.items():
                signal.signal(sinal, anterior)


def main(argv: list[str] | None = None) -> int:
    args = cria_parser().parse_args(argv)
    try:
        if args.presidente_por_uf and args.ano != 2026:
            raise ValueError("--presidente-por-uf exige 2026")
        sheet = identificador_planilha(args.ano, args.turno)
        return gerenciar(args, sheet)
    except KeyboardInterrupt:
        return 130
    except Exception as erro:  # noqa: BLE001 - diagnóstico da CLI
        print(f"Erro: {erro}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
