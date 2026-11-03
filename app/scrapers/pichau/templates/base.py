import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests

if TYPE_CHECKING:
    from scrapers.pichau.pichau_scraper import PichauScraper


def configurar_rota(
    scraper: "PichauScraper",
    variavel_url: str,
    caminho_padrao: str,
    variaveis_alternativas: tuple[str, ...] = (),
) -> None:
    url_configurada = os.getenv(variavel_url)
    if not url_configurada:
        url_configurada = next(
            (
                os.getenv(variavel)
                for variavel in variaveis_alternativas
                if os.getenv(variavel)
            ),
            None,
        )
    scraper.url = url_configurada or (
        f"{scraper.url.rstrip('/')}/{caminho_padrao.lstrip('/')}"
    )


def validar_rota(scraper: "PichauScraper", response: requests.Response) -> bool:
    url_esperada = urlparse(scraper.url)
    url_recebida = urlparse(response.url)
    return (
        bool(url_esperada.netloc)
        and url_recebida.netloc.casefold() == url_esperada.netloc.casefold()
        and url_recebida.path.rstrip("/") == url_esperada.path.rstrip("/")
    )
