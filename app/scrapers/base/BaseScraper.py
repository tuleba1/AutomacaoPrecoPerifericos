import json
import logging
import math
import re
import time
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests

from config.settings import PRODUCT_NAME
from app.domain.BasePesquisa import BasePesquisa

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

STATUS_REFRESH = {202, 403, 429}          # respostas que indicam sessão inválida/bloqueio
COOKIE_TTL = 30 * 60                      # 30 min; ajuste conforme observar
CACHE_DIR = Path(".cache_cookies")

class BaseScraper(BasePesquisa):
    def __init__(self):
        self.loja = getattr(self, "loja", "")
        self.url = getattr(self, "url", "")
        self.paths: list[str] = list(getattr(self, "paths", ["/"]))
        self.headers: dict[str, str] = dict(getattr(self, "headers", {}))
        self.usar_browser = getattr(self, "usar_browser", False)
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.logger = logging.getLogger(self.loja or self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self._cookies_obtidos_em = 0.0
        self._pagina_inicial: requests.Response | None = None
        self._resultado_busca: requests.Response | None = None
        self._carregar_cache()

    # Pegar cookies de forma dinâmicas
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
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        try:
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
        except PlaywrightError as exc:
            raise RuntimeError(f"Falha ao obter cookies pelo navegador: {exc}") from exc
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


    def _resolver_url(self, caminho: str | None = None) -> str:
        if not caminho:
            return self.url
        if urlparse(caminho).scheme:
            return caminho
        return urljoin(self.url.rstrip("/") + "/", caminho.lstrip("/"))

    def acessar_pagina(
        self, url: str, _tentativa: int = 0
    ) -> requests.Response | None:
        pagina = self._resolver_url(url)

        if self._cookies_expirados():
            self.renovar_cookies()

        try:
            self.logger.info("Acessando %s: %s", self.loja, pagina)
            response = self.session.get(pagina, timeout=30, headers=self.headers)
        except requests.RequestException as exc:
            self.logger.error("Erro ao acessar a página de %s: %s", self.loja, exc)
            return None

        if response.status_code == 200:
            self.logger.info("Página acessada com sucesso (%s) | HTTP 200", self.loja)
            return response

        if response.status_code in STATUS_REFRESH and _tentativa == 0:
            self.logger.warning("HTTP %s: renovando cookies e tentando de novo", response.status_code)
            self.renovar_cookies()
            return self.acessar_pagina(url, _tentativa=1)

        self.logger.error("Erro ao acessar %s | HTTP %s", pagina, response.status_code)
        return None

    def acessar_caminhos(self) -> list[requests.Response]:
        respostas = []
        for caminho in self.paths or ["/"]:
            r = self.acessar_pagina(caminho)
            if r is not None:
                respostas.append(r)
        return respostas

    @staticmethod
    def _parse_preco(valor: object, *, texto_localizado: bool = False) -> float:
        if isinstance(valor, bool) or valor is None:
            raise ValueError(f"Preço inválido: {valor!r}")

        texto = str(valor).strip()
        if texto_localizado:
            correspondencia = re.search(
                r"R\$\s*([\d][\d.,]*)(?!\s*x\b)", texto, re.IGNORECASE
            )
            if correspondencia:
                texto = correspondencia.group(1)
            else:
                correspondencia = re.search(r"\d[\d.,]*", texto)
                if correspondencia is None:
                    raise ValueError(f"Preço inválido: {valor!r}")
                texto = correspondencia.group()
            if "," in texto:
                texto = texto.replace(".", "").replace(",", ".")
            elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", texto):
                texto = texto.replace(".", "")

        try:
            preco = Decimal(texto)
        except InvalidOperation as exc:
            raise ValueError(f"Preço inválido: {valor!r}") from exc

        resultado = float(preco)
        if not preco.is_finite() or resultado <= 0 or not math.isfinite(resultado):
            raise ValueError(f"Preço deve ser um número finito maior que zero: {valor!r}")
        return resultado

    def pesquisar_produto(self, produto: str) -> requests.Response:
        if self._pagina_inicial is None:
            raise ValueError("A página inicial não foi acessada antes da pesquisa")

        soup = BeautifulSoup(self._pagina_inicial.text, "html.parser")
        for formulario in soup.find_all("form"):
            campos = formulario.find_all("input")
            campo_busca = next(
                (
                    campo
                    for campo in campos
                    if campo.get("name")
                    and (
                        campo.get("type", "text").lower() in {"search", "text"}
                    )
                ),
                None,
            )
            if campo_busca is None or not campo_busca.get("name"):
                continue

            metodo = formulario.get("method", "get").lower()
            if metodo not in {"get", "post"}:
                continue

            parametros = {}
            for campo in formulario.find_all("input", attrs={"type": "hidden"}):
                if campo.get("name"):
                    parametros[campo["name"]] = campo.get("value", "")
            parametros[campo_busca["name"]] = produto

            destino = urljoin(
                self._pagina_inicial.url,
                formulario.get("action") or self._pagina_inicial.url,
            )
            self.logger.debug(
                "Enviando pesquisa para %s pelo formulário %s",
                destino,
                metodo.upper(),
            )
            if metodo == "get":
                resposta = self.session.get(
                    destino, params=parametros, timeout=30, headers=self.headers
                )
            else:
                resposta = self.session.post(
                    destino, data=parametros, timeout=30, headers=self.headers
                )

            if resposta.status_code != 200:
                raise ValueError(
                    f"Pesquisa retornou HTTP {resposta.status_code} em {resposta.url}"
                )
            if not resposta.text.strip():
                raise ValueError("A pesquisa retornou uma página vazia")
            return resposta

        raise NotImplementedError(
            f"Não foi encontrado formulário de pesquisa compatível para {self.loja}"
        )

    @staticmethod
    def _percorrer_json(valor: object):
        if isinstance(valor, dict):
            yield valor
            for filho in valor.values():
                yield from BaseScraper._percorrer_json(filho)
        elif isinstance(valor, list):
            for filho in valor:
                yield from BaseScraper._percorrer_json(filho)

    @staticmethod
    def _tipo_produto(valor: object) -> bool:
        tipos = valor if isinstance(valor, list) else [valor]
        return any(
            isinstance(tipo, str)
            and tipo.rsplit("/", 1)[-1].lower() == "product"
            for tipo in tipos
        )

    def _precos_json_ld(self, soup: BeautifulSoup) -> list[tuple[float, str]]:
        candidatos = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                dados = json.loads(script.string or script.get_text())
            except json.JSONDecodeError:
                self.logger.debug("Bloco JSON-LD inválido ignorado durante extração")
                continue

            for item in self._percorrer_json(dados):
                if not self._tipo_produto(item.get("@type")):
                    continue
                nome = item.get("name")
                if not isinstance(nome, str):
                    continue

                ofertas = item.get("offers", [])
                if isinstance(ofertas, dict):
                    ofertas = [ofertas]
                if not isinstance(ofertas, list):
                    continue

                for oferta in ofertas:
                    if not isinstance(oferta, dict):
                        continue
                    valor = oferta.get("price", oferta.get("lowPrice"))
                    if valor is None:
                        continue
                    try:
                        preco = self._parse_preco(valor)
                    except ValueError:
                        continue
                    candidatos.append((preco, nome))
        return candidatos

    @staticmethod
    def _normalizar_texto(valor: str) -> str:
        sem_acentos = unicodedata.normalize("NFKD", valor)
        sem_acentos = sem_acentos.encode("ascii", "ignore").decode("ascii")
        return " ".join(re.findall(r"\w+", sem_acentos.casefold()))

    def extrair_preco(self, produto: str) -> float:
        if self._resultado_busca is None:
            raise ValueError("A pesquisa do produto não foi executada")

        soup = BeautifulSoup(self._resultado_busca.text, "html.parser")
        candidatos = self._precos_json_ld(soup)
        if not candidatos:
            raise ValueError(
                "Nenhum preço válido em dados estruturados de produto (JSON-LD) "
                "foi encontrado nos resultados"
            )

        termos = set(self._normalizar_texto(produto).split())
        pontuados = [
            (
                len(termos & set(self._normalizar_texto(nome).split())),
                preco,
                nome,
            )
            for preco, nome in candidatos
        ]
        maior_pontuacao = max(pontuacao for pontuacao, _, _ in pontuados)
        melhores = [
            (preco, nome)
            for pontuacao, preco, nome in pontuados
            if pontuacao == maior_pontuacao
        ]
        if maior_pontuacao == 0:
            raise ValueError(
                f"Nenhum produto nos resultados corresponde a {produto!r}"
            )
        if len(set(melhores)) > 1:
            raise ValueError(
                f"Resultados ambíguos para {produto!r}; não foi possível "
                "selecionar um preço com segurança"
            )

        preco = melhores[0][0]
        self.logger.debug("Preço validado para %s: %.2f", produto, preco)
        return preco

    @staticmethod
    def _resumo_retorno(retorno: object) -> object:
        if isinstance(retorno, requests.Response):
            return {
                "http_status": retorno.status_code,
                "url": retorno.url,
            }
        return retorno

    def executar_extracao(self, produto: str | None = None) -> dict:
        nome_produto = (produto or PRODUCT_NAME).strip()
        nomes_etapas = (
            "acessar_pagina",
            "pesquisar_produto",
            "extrair_preco",
        )
        etapas: dict[str, dict] = {}

        if not nome_produto:
            motivo = "PRODUCT_NAME não foi configurado no ambiente"
            self.logger.debug(
                "[%s] Entrada da etapa acessar_pagina: url=%s, produto ausente",
                self.loja,
                self.url,
            )
            self.logger.error("Fluxo interrompido: %s", motivo)
            etapas[nomes_etapas[0]] = {
                "status": "ERROR",
                "entrada": {"url": self.url, "produto": nome_produto},
                "erro": motivo,
            }
            for nome_etapa in nomes_etapas[1:]:
                self.logger.debug(
                    "[%s] Etapa %s não executada: etapa anterior falhou",
                    self.loja,
                    nome_etapa,
                )
                etapas[nome_etapa] = {
                    "status": "ERROR",
                    "executada": False,
                    "erro": "Não executada porque a etapa anterior falhou",
                }
            return {
                "status": "ERROR",
                "produto": nome_produto,
                "etapas": etapas,
                "erro": motivo,
            }

        entradas = (
            {"url": self.url},
            {"produto": nome_produto},
            {"produto": nome_produto},
        )
        acoes = (
            lambda: self.acessar_pagina(self.url),
            lambda: self.pesquisar_produto(nome_produto),
            lambda: self.extrair_preco(nome_produto),
        )

        for indice, (nome_etapa, entrada, acao) in enumerate(
            zip(nomes_etapas, entradas, acoes)
        ):
            self.logger.debug(
                "[%s] Entrada da etapa %s: %s", self.loja, nome_etapa, entrada
            )
            self.logger.debug("[%s] Executando etapa %s", self.loja, nome_etapa)
            try:
                retorno = acao()
                if nome_etapa == "acessar_pagina":
                    if (
                        retorno is None
                        or retorno.status_code != 200
                        or not retorno.text.strip()
                    ):
                        raise ValueError(
                            "A página inicial deve retornar HTTP 200 e conteúdo"
                        )
                    self._pagina_inicial = retorno
                elif nome_etapa == "pesquisar_produto":
                    if (
                        retorno is None
                        or retorno.status_code != 200
                        or not retorno.text.strip()
                    ):
                        raise ValueError(
                            "A pesquisa deve retornar HTTP 200 e conteúdo"
                        )
                    self._resultado_busca = retorno
                else:
                    retorno = self._parse_preco(
                        retorno,
                        texto_localizado=isinstance(retorno, str)
                        and ("R$" in retorno or "," in retorno),
                    )

                etapas[nome_etapa] = {
                    "status": "OK",
                    "entrada": entrada,
                    "retorno": self._resumo_retorno(retorno),
                }
                self.logger.debug(
                    "[%s] Retorno da etapa %s: status=OK, retorno=%s",
                    self.loja,
                    nome_etapa,
                    self._resumo_retorno(retorno),
                )
            except (
                requests.RequestException,
                ValueError,
                TypeError,
                AttributeError,
                OSError,
                RuntimeError,
                OverflowError,
            ) as exc:
                self.logger.exception(
                    "[%s] Erro na etapa %s: %s", self.loja, nome_etapa, exc
                )
                self.logger.debug(
                    "[%s] Retorno da etapa %s: status=ERROR, erro=%s",
                    self.loja,
                    nome_etapa,
                    exc,
                )
                etapas[nome_etapa] = {
                    "status": "ERROR",
                    "entrada": entrada,
                    "erro": str(exc),
                }
                for etapa_pendente in nomes_etapas[indice + 1 :]:
                    etapas[etapa_pendente] = {
                        "status": "ERROR",
                        "executada": False,
                        "erro": "Não executada porque a etapa anterior falhou",
                    }
                    self.logger.debug(
                        "[%s] Etapa %s não executada: etapa anterior falhou",
                        self.loja,
                        etapa_pendente,
                    )
                return {
                    "status": "ERROR",
                    "produto": nome_produto,
                    "etapas": etapas,
                    "erro": str(exc),
                }

        return {
            "status": "OK",
            "produto": nome_produto,
            "preco": etapas["extrair_preco"]["retorno"],
            "etapas": etapas,
        }