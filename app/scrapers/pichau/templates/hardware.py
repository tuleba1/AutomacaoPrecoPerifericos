import requests

from scrapers.pichau.pichau_scraper import PichauScraper
from .base import configurar_rota, validar_rota


class PichauHardwareTemplate(PichauScraper):
    def __init__(self):
        super().__init__()
        configurar_rota(
            self,
            "PICHAU_TECLADO_URL",
            "/perifericos/teclado",
        )

    def validar_pagina(self, response: requests.Response) -> bool:
        return validar_rota(self, response)
