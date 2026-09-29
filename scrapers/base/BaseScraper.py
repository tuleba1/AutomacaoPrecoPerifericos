import json
import logging
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

STATUS_REFRESH = {202, 403, 429}          # respostas que indicam sessão inválida/bloqueio
COOKIE_TTL = 30 * 60                      # 30 min; ajuste conforme observar
CACHE_DIR = Path(".cache_cookies")


class BaseScraper:
    loja = ""
    url = ""
    paths: list[str] = ["/"]
    headers: dict[str, str] = {}
    usar_browser: bool = False            # cada scraper decide se precisa do Playwright

    def __init__(self):
        self.paths = list(self.paths)
        self.headers = dict(self.headers)
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.logger = logging.getLogger(self.loja or self.__class__.__name__)
        self._cookies_obtidos_em = 0.0
        self._carregar_cache()

    # ---------- cookies dinâmicos ----------
    @property
    def _arquivo_cache(self) -> Path:
        return CACHE_DIR / f"{self.loja}.json"

    def _carregar_cache(self) -> None:
        if not self._arquivo_cache.exists():
            return
        dados = json.loads(self._arquivo_cache.read_text(encoding="utf-8"))
        if time.time() - dados["obtido_em"] > COOKIE_TTL:
            return
        for c in dados["cookies"]:
            self.session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c.get("path", "/"))
        self._cookies_obtidos_em = dados["obtido_em"]
        self.logger.info("Cookies carregados do cache")

    def _salvar_cache(self, cookies: list[dict]) -> None:
        CACHE_DIR.mkdir(exist_ok=True)
        self._arquivo_cache.write_text(
            json.dumps({"obtido_em": self._cookies_obtidos_em, "cookies": cookies}),
            encoding="utf-8",
        )

    def _cookies_via_browser(self) -> list[dict]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # se funcionar, teste headless=True
            ctx = browser.new_context(
                user_agent=self.headers.get("User-Agent"),
                locale="pt-BR",
            )
            page = ctx.new_page()
            page.goto(self.url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(3)  # dá tempo para o JS do anti-bot terminar de setar cookies
            cookies = ctx.cookies()
            browser.close()
        return cookies

    def _cookies_via_aquecimento(self) -> list[dict]:
        self.session.get(self.url, timeout=30)
        return [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in self.session.cookies
        ]

    def renovar_cookies(self) -> None:
        self.logger.info("Renovando cookies (%s)", "browser" if self.usar_browser else "aquecimento")
        self.session.cookies.clear()
        cookies = self._cookies_via_browser() if self.usar_browser else self._cookies_via_aquecimento()
        if self.usar_browser:
            for c in cookies:
                self.session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c.get("path", "/"))
        self._cookies_obtidos_em = time.time()
        self._salvar_cache(cookies)

    def _cookies_expirados(self) -> bool:
        return time.time() - self._cookies_obtidos_em > COOKIE_TTL

    # ---------- requisições ----------
    def _resolver_url(self, caminho: str | None = None) -> str:
        if not caminho:
            return self.url
        if urlparse(caminho).scheme:
            return caminho
        return urljoin(self.url.rstrip("/") + "/", caminho.lstrip("/"))

    def acessar_pagina(self, url: str | None = None, _tentativa: int = 1) -> requests.Response | None:
        pagina = self._resolver_url(url)

        if self._cookies_expirados():
            self.renovar_cookies()

        try:
            self.logger.info("Acessando %s: %s", self.loja, pagina)
            response = self.session.get(pagina, timeout=30, headers=self.headers)
        except requests.RequestException as exc:
            self.logger.error("Erro ao acessar a página de %s: %s", self.loja, exc)
            return None

        if response.status_code == 200: #Colocar validação de regex para confirmar a entrada no site
            self.logger.info("Página acessada com sucesso (%s) | HTTP 200", self.loja)
            return response

        if response.status_code in STATUS_REFRESH and _tentativa == 1:
            self.logger.warning("HTTP %s: renovando cookies e tentando de novo", response.status_code)
            self.renovar_cookies()
            return self.acessar_pagina(url, _tentativa=2)

        self.logger.error("Erro ao acessar %s | HTTP %s", pagina, response.status_code)
        return None

    def acessar_caminhos(self) -> list[requests.Response]:
        respostas = []
        for caminho in self.paths or ["/"]:
            r = self.acessar_pagina(caminho)
            if r is not None:
                respostas.append(r)
        return respostas