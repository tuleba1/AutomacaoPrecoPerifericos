import os
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

from scrapers.base.BaseScraper import BaseScraper


class PichauScraper(BaseScraper):
    def __init__(self):
        self.loja = "pichau"
        self.url = os.getenv("PICHAU_URL", "https://www.pichau.com.br").rstrip("/")
        self.rgx_pagina_inicial =  (r'(?is)<title>\s*Pichau\s*-\s*'
        r'Os Melhores Preços do Brasil\s*</title>'
        )
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "pt-BR,pt;q=0.7",
            "Cache-Control": "max-age=0",
            "Priority": "u=0, i",
            "Referer": "https://www.google.com/",
            "Sec-Ch-Ua": '"Chromium";v="154", "Brave";v="154", "Not A(Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-Gpc": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
        }
        user_agent = os.getenv("PICHAU_USER_AGENT")
        if user_agent:
            self.headers["User-Agent"] = user_agent
        super().__init__()

    def pesquisar_produto(self, produto: str) -> requests.Response:
        if self._pagina_inicial is None:
            raise ValueError("A página da categoria não foi acessada antes da pesquisa")

        soup = BeautifulSoup(self._pagina_inicial.text, "html.parser")
        for formulario in soup.find_all("form"):
            campo_busca = next(
                (
                    campo
                    for campo in formulario.find_all("input")
                    if campo.get("name")
                    and campo.get("type", "text").lower() in {"search", "text"}
                ),
                None,
            )
            if campo_busca is None:
                continue

            metodo = formulario.get("method", "get").lower()
            if metodo not in {"get", "post"}:
                continue

            parametros = {
                campo["name"]: campo.get("value", "")
                for campo in formulario.find_all("input", attrs={"type": "hidden"})
                if campo.get("name")
            }
            parametros[campo_busca["name"]] = produto
            destino = urljoin(
                self._pagina_inicial.url,
                formulario.get("action") or self._pagina_inicial.url,
            )
            if metodo == "get":
                resposta = self.session.get(
                    destino,
                    params=parametros,
                    timeout=30,
                    headers=self.headers,
                )
            else:
                resposta = self.session.post(
                    destino,
                    data=parametros,
                    timeout=30,
                    headers=self.headers,
                )

            if resposta.status_code != 200 or not resposta.text.strip():
                raise ValueError(
                    f"Pesquisa retornou HTTP {resposta.status_code} em {resposta.url}"
                )
            return resposta

        raise NotImplementedError(
            "Não foi encontrado formulário de pesquisa compatível para pichau"
        )
