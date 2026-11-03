import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
import requests

from scrapers.pichau.pichau_scraper import PichauScraper

from .base import validar_rota


class PichauPerifericosTemplate(PichauScraper):
    def __init__(self):
        super().__init__()
        self.max_paginas = 3
        self.tamanho_pagina = 200
        self._paginas_pesquisa: list[requests.Response] = []
        self._html_paginas_pesquisa: list[str] = []
        self.status_bloqueio =  {403, 429, 503}

    def validar_pagina(self, response: requests.Response) -> bool:
        return validar_rota(self, response)

    @staticmethod
    def _normalizar_slug(valor: str) -> str:
        sem_acento = unicodedata.normalize("NFKD", valor)
        sem_acento = sem_acento.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento.casefold()).strip("-")
        return slug

    def _montar_url_produto(self, produto: str) -> str:
        slug = self._normalizar_slug(produto)
        if not slug:
            raise ValueError("Produto informado é vazio após normalização")

        url_base = urlparse(self.url)
        caminho = url_base.path or "/"
        if "/perifericos" in caminho:
            prefixo = caminho.split("/perifericos", maxsplit=1)[0]
            caminho_base = f"{prefixo}/perifericos"
        else:
            caminho_base = caminho.rstrip("/")

        if not caminho_base:
            caminho_base = "/perifericos"

        caminho_produto = f"{caminho_base.rstrip('/')}/{slug}"
        return urlunparse(
            (
                url_base.scheme,
                url_base.netloc,
                caminho_produto,
                "",
                "",
                "",
            )
        )

    @staticmethod
    def _url_com_pagina(url: str, pagina: int, tamanho_pagina: int) -> str:
        parsed = urlparse(url)
        parametros = dict(parse_qsl(parsed.query, keep_blank_values=True))
        parametros["pageSize"] = str(tamanho_pagina)
        if pagina > 1:
            parametros["page"] = str(pagina)
        else:
            parametros.pop("page", None)
        query = urlencode(parametros)
        return urlunparse(parsed._replace(query=query))

    @staticmethod
    def _resposta_bloqueada(response: requests.Response) -> bool:
        texto = response.text.casefold()
        return any(
            marcador in texto
            for marcador in ["access denied"]
        )

    @staticmethod
    def _tem_produtos(response: requests.Response) -> bool:
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.select_one("a[href*='/produto/']"):
            return True
        if soup.select_one("h2[class*='product_info_title']"):
            return True

        total_count = re.search(r'"total_count"\s*:\s*(\d+)', response.text)
        if total_count is not None:
            return int(total_count.group(1)) > 0

        texto = soup.get_text(" ", strip=True).casefold()
        return not (
            "nenhum produto" in texto
            or "nenhum resultado" in texto
            or "sem resultado" in texto
        )

    @staticmethod
    def _obter_proxima_pagina(response: requests.Response, pagina_atual: int) -> str | None:
        soup = BeautifulSoup(response.text, "html.parser")

        for ancora in soup.find_all("a", href=True):
            aria_label = (ancora.get("aria-label") or "").casefold()
            rel = " ".join(ancora.get("rel", [])).casefold()
            if "next" in rel or "next page" in aria_label or "próxima" in aria_label:
                return urljoin(response.url, ancora["href"])

        pagina_seguinte = pagina_atual + 1
        for ancora in soup.find_all("a", href=True):
            href = ancora["href"]
            if f"page={pagina_seguinte}" in href:
                return urljoin(response.url, href)
        return None

    def _coletar_paginas_resultado(self, produto: str) -> list[requests.Response]:
        if self._pagina_inicial is None:
            raise ValueError("A página da categoria não foi acessada antes da pesquisa")

        if self._cookies_expirados():
            self.renovar_cookies()

        url_base_produto = self._montar_url_produto(produto)
        paginas: list[requests.Response] = []

        self.logger.info(
            "Iniciando pesquisa em %s | produto=%s | limite=%s páginas | tamanho=%s",
            url_base_produto,
            produto,
            self.max_paginas,
            self.tamanho_pagina,
        )

        for pagina in range(1, self.max_paginas + 1):
            url_pagina = self._url_com_pagina(url_base_produto, pagina, self.tamanho_pagina)
            try:
                resposta = self.session.get(
                    url_pagina,
                    timeout=30,
                    headers=self.headers,
                )
            except requests.Timeout as exc:
                self.logger.error(
                    "Página %s timeout em %s: %s",
                    pagina,
                    url_pagina,
                    exc,
                )
                raise ValueError(f"Timeout ao acessar a página {pagina}: {url_pagina}") from exc
            except requests.RequestException as exc:
                self.logger.error(
                    "Página %s erro de requisição em %s: %s",
                    pagina,
                    url_pagina,
                    exc,
                )
                raise ValueError(
                    f"Erro de requisição ao acessar a página {pagina}: {url_pagina}"
                ) from exc

            if resposta.status_code in self.status_bloqueio:
                self.logger.error(
                    "Página %s bloqueada (%s) em %s",
                    pagina,
                    resposta.status_code,
                    resposta.url,
                )
                raise ValueError(
                    f"Bloqueio detectado na página {pagina} (HTTP {resposta.status_code})"
                )

            if resposta.status_code != 200:
                self.logger.error(
                    "Página %s retornou HTTP %s em %s",
                    pagina,
                    resposta.status_code,
                    resposta.url,
                )
                raise ValueError(
                    f"Resposta inesperada na página {pagina}: HTTP {resposta.status_code}"
                )

            if not resposta.text.strip():
                self.logger.warning("Página %s vazia em %s", pagina, resposta.url)
                break

            if self._resposta_bloqueada(resposta):
                self.logger.error(
                    "Página %s possui indicadores de bloqueio em %s",
                    pagina,
                    resposta.url,
                )
                raise ValueError(f"Bloqueio detectado na página {pagina}: {resposta.url}")

            if not self._tem_produtos(resposta):
                self.logger.warning(
                    "Página %s sem produtos; encerrando paginação em %s",
                    pagina,
                    resposta.url,
                )
                break

            paginas.append(resposta)
            self.logger.info(
                "Página %s coletada com sucesso | url=%s",
                pagina,
                resposta.url,
            )

            proxima = self._obter_proxima_pagina(resposta, pagina)
            if not proxima:
                self.logger.info(
                    "Paginação encerrada na página %s (sem link de próxima)",
                    pagina,
                )
                break

        return paginas

    @staticmethod
    def _consolidar_paginas_em_resposta(paginas: list[requests.Response]) -> requests.Response:
        if len(paginas) == 1:
            return paginas[0]

        resposta_base = paginas[0]
        encoding = resposta_base.encoding or "utf-8"
        html_consolidado = "\n".join(pagina.text for pagina in paginas)
        resposta_base._content = html_consolidado.encode(encoding, errors="ignore")
        resposta_base.encoding = encoding
        return resposta_base

    def obter_html_paginas(self) -> list[str]:
        return list(self._html_paginas_pesquisa)

    def pesquisar_produto(self, produto: str) -> requests.Response:
        paginas = self._coletar_paginas_resultado(produto)
        if not paginas:
            raise ValueError("A pesquisa não retornou páginas com produtos")

        self._paginas_pesquisa = paginas
        self._html_paginas_pesquisa = [pagina.text for pagina in paginas]
        resposta_consolidada = self._consolidar_paginas_em_resposta(paginas)
        self.logger.info(
            "Pesquisa consolidada em aba Ãºnica | pÃ¡ginas=%s | url_base=%s",
            len(paginas),
            resposta_consolidada.url,
        )
        return resposta_consolidada
