import socket
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import Mock

import pytest
import requests

import extractors


@contextmanager
def servidor_http(falhas=0, status=200, interrompe_corpo=False):
    """Servidor local sem esperas, com sockets e encerramento limitados."""
    chamadas = []

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(1)
            super().setup()

        def do_GET(self):
            chamadas.append(dict(self.headers))
            if len(chamadas) <= falhas:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            self.send_response(status)
            self.send_header("Content-Length", "10" if interrompe_corpo else "2")
            if status == 429:
                self.send_header("Retry-After", "1")
            self.end_headers()
            self.wfile.write(b"ok")
            self.wfile.flush()
            self.close_connection = True

        def log_message(self, *args):
            return

    servidor = HTTPServer(("127.0.0.1", 0), Handler)
    servidor.timeout = 0.1
    thread = Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{servidor.server_port}/arquivo", chamadas
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive(), "Servidor HTTP não encerrou"


def baixa(uri, filename, **kwargs):
    return extractors.download_file(uri, filename=filename, progress=False, timeout=0.5, **kwargs)


def test_recupera_conexao_fechada_antes_dos_headers(tmp_path):
    destino = tmp_path / "subdiretorio" / "arquivo.zip"
    with servidor_http(falhas=1) as (uri, chamadas):
        caminho = baixa(uri, destino)
    assert caminho == destino
    assert isinstance(caminho, Path)
    assert caminho.read_bytes() == b"ok"
    assert len(chamadas) == 2


def test_limita_tentativas_quando_servidor_sempre_fecha_conexao(tmp_path):
    destino = tmp_path / "arquivo.zip"
    with servidor_http(falhas=100) as (uri, chamadas), pytest.raises(requests.ConnectionError):
        baixa(uri, destino)
    assert len(chamadas) == 4
    assert not destino.exists()


@pytest.mark.parametrize("status", [404, 429, 503])
def test_erro_http_nao_repete_nem_cria_destino(tmp_path, status):
    destino = tmp_path / "inexistente" / "arquivo.zip"
    with servidor_http(status=status) as (uri, chamadas), pytest.raises(requests.HTTPError) as erro:
        baixa(uri, destino)
    assert erro.value.response.status_code == status
    assert len(chamadas) == 1
    assert not destino.parent.exists()


def test_stream_interrompido_nao_repete_download(tmp_path):
    with (
        servidor_http(interrompe_corpo=True) as (uri, chamadas),
        pytest.raises(requests.exceptions.ChunkedEncodingError),
    ):
        baixa(uri, tmp_path / "arquivo.zip")
    assert len(chamadas) == 1


def test_preserva_headers_e_precedencia_user_agent(tmp_path):
    headers = {"User-Agent": "customizado", "Accept": "application/zip", "X-Teste": "valor"}
    padrao = dict(extractors.DEFAULT_HEADERS)
    with servidor_http() as (uri, chamadas):
        baixa(uri, tmp_path / "arquivo.zip", headers=headers, user_agent="agente-prioritario")
    assert chamadas[0]["User-Agent"] == "agente-prioritario"
    assert chamadas[0]["Accept"] == "application/zip"
    assert chamadas[0]["X-Teste"] == "valor"
    assert chamadas[0]["Accept-Language"] == padrao["Accept-Language"]
    assert headers["User-Agent"] == "customizado"
    assert extractors.DEFAULT_HEADERS == padrao


def test_preserva_proxies_timeout_e_stream(tmp_path, monkeypatch):
    resposta = Mock(headers={})
    resposta.iter_content.return_value = iter([b"", b"ok"])
    requisicao = Mock(return_value=resposta)
    monkeypatch.setattr(requests.Session, "request", requisicao)
    proxies = {"http": "http://proxy.invalid:8080", "https": "http://proxy.invalid:8080"}
    destino = tmp_path / "arquivo.zip"
    caminho = extractors.download_file("http://example.invalid", destino, progress=False, proxies=proxies, timeout=0.25)
    assert caminho == destino
    assert caminho.read_bytes() == b"ok"
    assert requisicao.call_args.kwargs["proxies"] == proxies
    assert requisicao.call_args.kwargs["timeout"] == 0.25
    assert requisicao.call_args.kwargs["stream"] is True
    resposta.raise_for_status.assert_called_once_with()


def test_tentativas_de_conexao_limitadas_no_socket(tmp_path, monkeypatch):
    from urllib3.util import connection

    tentativas = []

    def falha_conexao(*args, **kwargs):
        tentativas.append(args)
        raise ConnectionRefusedError("Conexão recusada")

    with servidor_http() as (uri, chamadas):
        monkeypatch.setattr(connection, "create_connection", falha_conexao)
        with pytest.raises(requests.ConnectionError):
            baixa(uri, tmp_path / "arquivo.zip")
    assert len(tentativas) == 4
    assert not chamadas


def test_timeout_de_leitura_dos_headers_nao_repete(tmp_path, monkeypatch):
    from urllib3.connectionpool import HTTPConnectionPool
    from urllib3.exceptions import ReadTimeoutError

    requisicao = Mock(side_effect=ReadTimeoutError(None, "/arquivo", "Tempo de leitura esgotado"))
    monkeypatch.setattr(HTTPConnectionPool, "_make_request", requisicao)
    with servidor_http() as (uri, chamadas), pytest.raises(requests.ConnectionError):
        baixa(uri, tmp_path / "arquivo.zip")
    assert requisicao.call_count == 1
    assert not chamadas


@pytest.mark.parametrize("falha", [None, "leitura", "escrita", "progresso", "interrupcao"])
@pytest.mark.parametrize("content_length", [None, "2"])
def test_fecha_progresso_em_sucesso_erro_e_interrupcao(tmp_path, monkeypatch, falha, content_length):
    resposta = Mock(headers={} if content_length is None else {"Content-Length": content_length})
    barra = Mock()
    cria_barra = Mock(return_value=barra)
    monkeypatch.setattr("tqdm.tqdm", cria_barra)
    monkeypatch.setattr(requests.Session, "request", Mock(return_value=resposta))
    erro = KeyboardInterrupt() if falha == "interrupcao" else OSError("Falha simulada")

    def chunks(chunk_size):
        yield b""
        yield b"ok"
        if falha in ("leitura", "interrupcao"):
            raise erro

    resposta.iter_content.side_effect = chunks
    if falha == "escrita":
        arquivo = Mock()
        arquivo.__enter__ = Mock(return_value=arquivo)
        arquivo.__exit__ = Mock(return_value=False)
        arquivo.write.side_effect = erro
        monkeypatch.setattr(Path, "open", Mock(return_value=arquivo))
    elif falha == "progresso":
        barra.update.side_effect = erro

    destino = tmp_path / "arquivo.zip"
    if falha is None:
        assert extractors.download_file("http://example.invalid", destino, title="Baixando", timeout=0.5) == destino
        assert destino.read_bytes() == b"ok"
    else:
        with pytest.raises(type(erro)) as capturada:
            extractors.download_file("http://example.invalid", destino, title="Baixando", timeout=0.5)
        assert capturada.value is erro
    cria_barra.assert_called_once_with(
        total=None if content_length is None else 2, unit="B", unit_scale=True, desc="Baixando"
    )
    barra.close.assert_called_once_with()
    if falha != "escrita":
        barra.update.assert_called_once_with(2)


def test_progresso_desabilitado_nao_cria_barra(tmp_path, monkeypatch):
    cria_barra = Mock()
    monkeypatch.setattr("tqdm.tqdm", cria_barra)
    with servidor_http() as (uri, _):
        assert baixa(uri, tmp_path / "arquivo.zip").read_bytes() == b"ok"
    cria_barra.assert_not_called()


def test_download_temporario_devolve_path(tmp_path, monkeypatch):
    monkeypatch.setattr(extractors.tempfile, "tempdir", str(tmp_path))
    with servidor_http() as (uri, _):
        caminho = baixa(uri, None)
    assert isinstance(caminho, Path)
    assert caminho.parent == tmp_path
    assert caminho.read_bytes() == b"ok"


@pytest.fixture
def resposta_http(monkeypatch):
    resposta = Mock(headers={})
    resposta.iter_content.return_value = iter([b"ok"])
    monkeypatch.setattr(requests.Session, "request", Mock(return_value=resposta))
    fecha_sessao = Mock()
    monkeypatch.setattr(requests.Session, "close", fecha_sessao)
    return resposta, fecha_sessao


@pytest.fixture
def temporarios_criados(tmp_path, monkeypatch):
    arquivos = []
    cria_temporario = extractors.tempfile.NamedTemporaryFile
    monkeypatch.setattr(extractors.tempfile, "tempdir", str(tmp_path))

    def cria_arquivo(*args, **kwargs):
        arquivo = cria_temporario(*args, **kwargs)
        arquivos.append(arquivo)
        return arquivo

    monkeypatch.setattr(extractors.tempfile, "NamedTemporaryFile", cria_arquivo)
    return arquivos


@pytest.mark.parametrize("falha", [None, "status", "leitura", "interrupcao"])
def test_fecha_resposta_e_sessao_em_sucesso_status_erro_e_interrupcao(tmp_path, resposta_http, falha):
    resposta, fecha_sessao = resposta_http
    erro = KeyboardInterrupt() if falha == "interrupcao" else requests.HTTPError("Falha simulada")
    if falha == "status":
        resposta.raise_for_status.side_effect = erro
    elif falha is not None:
        resposta.iter_content.side_effect = erro
    destino = tmp_path / "subdiretorio" / "arquivo.zip"

    if falha is None:
        assert baixa("http://example.invalid", destino) == destino
        assert destino.read_bytes() == b"ok"
    else:
        with pytest.raises(type(erro)) as capturada:
            baixa("http://example.invalid", destino)
        assert capturada.value is erro
        if falha == "status":
            assert not destino.parent.exists()

    resposta.close.assert_called_once_with()
    fecha_sessao.assert_called_once_with()


@pytest.mark.parametrize("temporario", [False, True])
@pytest.mark.parametrize("falha", ["content_length", "barra", "interrupcao", "importacao"])
def test_fecha_arquivo_se_preparacao_do_progresso_falha(
    tmp_path, monkeypatch, resposta_http, temporarios_criados, temporario, falha
):
    resposta, fecha_sessao = resposta_http
    arquivos = temporarios_criados
    destino = None if temporario else tmp_path / "usuario.zip"
    if not temporario:
        abre_arquivo = Path.open

        def abre_destino(caminho, *args, **kwargs):
            arquivo = abre_arquivo(caminho, *args, **kwargs)
            arquivos.append(arquivo)
            return arquivo

        monkeypatch.setattr(Path, "open", abre_destino)

    erro = KeyboardInterrupt() if falha == "interrupcao" else OSError("Falha ao criar barra")
    if falha == "content_length":
        resposta.headers = {"Content-Length": "invalido"}
        tipo_erro = ValueError
    elif falha == "importacao":
        import sys

        monkeypatch.setitem(sys.modules, "tqdm", None)
        tipo_erro = ModuleNotFoundError
    else:
        monkeypatch.setattr("tqdm.tqdm", Mock(side_effect=erro))
        tipo_erro = type(erro)

    with pytest.raises(tipo_erro):
        extractors.download_file("http://example.invalid", destino, timeout=0.5)

    assert len(arquivos) == 1
    assert arquivos[0].closed
    caminho = Path(arquivos[0].name)
    assert caminho.exists() is (not temporario)
    resposta.close.assert_called_once_with()
    fecha_sessao.assert_called_once_with()


@pytest.mark.parametrize("falha", ["leitura", "escrita", "progresso", "interrupcao"])
def test_remove_so_temporario_proprio_em_erro_ou_interrupcao(
    tmp_path, monkeypatch, resposta_http, temporarios_criados, falha
):
    resposta, fecha_sessao = resposta_http
    usuario = tmp_path / "usuario.zip"
    usuario.write_bytes(b"dados do usuario")
    barra = Mock()
    monkeypatch.setattr("tqdm.tqdm", Mock(return_value=barra))
    erro = KeyboardInterrupt() if falha == "interrupcao" else OSError("Falha simulada")

    def chunks(chunk_size):
        if falha == "escrita":
            temporarios_criados[0].write = Mock(side_effect=erro)
        yield b"ok"
        if falha in ("leitura", "interrupcao"):
            raise erro

    resposta.iter_content.side_effect = chunks
    if falha == "progresso":
        barra.update.side_effect = erro

    with pytest.raises(type(erro)) as capturada:
        extractors.download_file("http://example.invalid", timeout=0.5)
    assert capturada.value is erro
    assert len(temporarios_criados) == 1
    assert temporarios_criados[0].closed
    assert not Path(temporarios_criados[0].name).exists()
    assert usuario.read_bytes() == b"dados do usuario"
    resposta.close.assert_called_once_with()
    fecha_sessao.assert_called_once_with()
    barra.close.assert_called_once_with()


@pytest.mark.parametrize("preexistente", [False, True])
@pytest.mark.parametrize("interrupcao", [False, True])
def test_preserva_destino_explicito_parcial_em_erro_ou_interrupcao(
    tmp_path, resposta_http, temporarios_criados, preexistente, interrupcao
):
    resposta, fecha_sessao = resposta_http
    destino = tmp_path / "usuario.zip"
    if preexistente:
        destino.write_bytes(b"conteudo anterior")
    erro = KeyboardInterrupt() if interrupcao else OSError("Leitura interrompida")

    def chunks(chunk_size):
        yield b"parcial"
        raise erro

    resposta.iter_content.side_effect = chunks
    with pytest.raises(type(erro)) as capturada:
        baixa("http://example.invalid", destino)
    assert capturada.value is erro
    assert destino.read_bytes() == b"parcial"
    assert not temporarios_criados
    resposta.close.assert_called_once_with()
    fecha_sessao.assert_called_once_with()


def test_status_invalido_nao_cria_temporario(resposta_http, temporarios_criados):
    resposta, fecha_sessao = resposta_http
    resposta.raise_for_status.side_effect = requests.HTTPError("Status inválido")
    with pytest.raises(requests.HTTPError):
        baixa("http://example.invalid", None)
    assert not temporarios_criados
    resposta.close.assert_called_once_with()
    fecha_sessao.assert_called_once_with()


def test_temporario_de_sucesso_permanece_fechado_e_devolvido(resposta_http, temporarios_criados):
    resposta, fecha_sessao = resposta_http
    caminho = baixa("http://example.invalid", None)
    assert len(temporarios_criados) == 1
    assert temporarios_criados[0].closed
    assert caminho == Path(temporarios_criados[0].name)
    assert caminho.read_bytes() == b"ok"
    resposta.close.assert_called_once_with()
    fecha_sessao.assert_called_once_with()
