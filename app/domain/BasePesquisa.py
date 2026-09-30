from abc import ABC, abstractmethod


class BasePesquisa(ABC):
    def __init__(self):
        self.url = None

    @abstractmethod
    def acessar_pagina(self):
        raise NotImplementedError

    @abstractmethod
    def pesquisar_produto(self, produto):
        raise NotImplementedError
    
    @abstractmethod
    def extrair_preco(self,produto):
        raise NotImplementedError

    def executar_extracao(self,produto):
        raise NotImplementedError
    #Momentaneamente com esses metodos