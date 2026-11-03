import requests

from scrapers.pichau.pichau_scraper import PichauScraper

from .base import configurar_rota, validar_rota


class PichauPerifericosTemplate(PichauScraper):
    def __init__(self):
        super().__init__()
        configurar_rota(
            self,
            "PICHAU_PERIFERICOS_URL",
            "/perifericos",
            variaveis_alternativas=("PICHAU_MOUSE_URL",),
        )

    def validar_pagina(self, response: requests.Response) -> bool:
        return validar_rota(self, response)

    def pesquisar_produto(self, produto: str) -> requests.Response:
        if self._pagina_inicial is None:
            raise ValueError("A página da categoria não foi acessada antes da pesquisa")