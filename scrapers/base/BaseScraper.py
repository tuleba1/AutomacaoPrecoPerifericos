import logging
from urllib.parse import urljoin, urlparse

import requests

from config.settings import SCRAPER_USER_AGENT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class BaseScraper:
    loja = ""
    url = ""

    def __init__(self):
        self.session = requests.Session()
        self.paths: list[str] = ["/"]
        self.headers = {
            "User-Agent": SCRAPER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.session.headers.update(self.headers)
        self.logger = logging.getLogger(self.loja or self.__class__.__name__)

    def _resolver_url(self, caminho: str | None = None) -> str:
        if not caminho:
            return self.url
        if urlparse(caminho).scheme:
            return caminho
        return urljoin(self.url.rstrip("/") + "/", caminho.lstrip("/"))

    def acessar_pagina(self, url: str | None = None) -> requests.Response | None:
        pagina = self._resolver_url(url)
        try:
            self.logger.info("Acessando %s: %s", self.loja, pagina)
            response = self.session.get(pagina, timeout=20)

            if response.status_code == 200:
                self.logger.info("Página acessada com sucesso (%s)", self.loja)
                return response

            self.logger.error(
                "Erro ao acessar a página %s: status %s", pagina, response.status_code
            )
            return None
        except requests.RequestException as exc:
            self.logger.error("Erro ao acessar a página de %s: %s", self.loja, exc)
            return None

    def acessar_caminhos(self) -> list[requests.Response]:
        respostas: list[requests.Response] = []
        caminhos = self.paths or ["/"]
        for caminho in caminhos:
            resposta = self.acessar_pagina(caminho)
            if resposta is not None:
                respostas.append(resposta)
        return respostas
