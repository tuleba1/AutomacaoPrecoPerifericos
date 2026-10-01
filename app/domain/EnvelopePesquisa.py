from abc import ABC
from enum import Enum
from typing import Any


class StatusPesquisa(Enum):
    SUCESSO = "sucesso"
    ERRO = "erro"
    PESQUISANDO = "pesquisando"


class EnvelopePesquisa(ABC):

    def __init__(
        self,
        produto: str,
        preco: float | None = None,
        status: StatusPesquisa = StatusPesquisa.PESQUISANDO,
        mensagem: str = "",
        data: Any = None
    ):
        self.produto = produto
        self.preco = preco
        self.status = status
        self.mensagem = mensagem
        self.data = data

    @classmethod
    def sucesso(
        cls,
        produto: str,
        preco: float,
        mensagem: str = ""
    ):
        return cls(
            produto=produto,
            preco=preco,
            status=StatusPesquisa.SUCESSO,
            mensagem=mensagem
        )

    @classmethod
    def erro(
        cls,
        produto: str,
        mensagem: str
    ):
        return cls(
            produto=produto,
            status=StatusPesquisa.ERRO,
            mensagem=mensagem
        )

    @classmethod
    def pesquisando(
        cls,
        produto: str,
        mensagem: str = ""
    ):
        return cls(
            produto=produto,
            status=StatusPesquisa.PESQUISANDO,
            mensagem=mensagem
        )