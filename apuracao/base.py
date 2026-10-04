from abc import ABC, abstractmethod
from datetime import datetime

from .modelo import Contexto, Resultado


class Apuracao(ABC):
    ano: int

    def __init__(self, contexto: Contexto):
        self.contexto = contexto
        if contexto.ano != self.ano:
            self._erro("ano", f"o formato exige {self.ano}")

    def _erro(self, campo: str, motivo: str):
        raise ValueError(
            f"{campo}: {motivo} (eleicao={self.contexto.eleicao}, abrangencia={self.contexto.abrangencia})"
        )

    def _campo(self, dados: dict, chave: str, caminho: str):
        if not isinstance(dados, dict) or chave not in dados:
            self._erro(caminho, "campo obrigatório ausente")
        return dados[chave]

    def _data(self, dados: dict, data: str, hora: str, opcional: bool = False) -> datetime | None:
        if opcional and not dados.get(data) and not dados.get(hora):
            return None
        valor_data = self._campo(dados, data, data)
        valor_hora = self._campo(dados, hora, hora)
        try:
            return datetime.strptime(f"{valor_data}T{valor_hora}-03:00", "%d/%m/%YT%H:%M:%S%z")
        except ValueError as erro:
            raise ValueError(
                f"{data}/{hora}: data ou hora inválida "
                f"(eleicao={self.contexto.eleicao}, abrangencia={self.contexto.abrangencia})"
            ) from erro

    @abstractmethod
    def ler(self, dados: dict) -> Resultado:
        """Converte um arquivo da fonte, preservando a semântica do seu formato."""
