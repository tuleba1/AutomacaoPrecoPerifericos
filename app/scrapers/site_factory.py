import importlib
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "app"
for caminho in (str(ROOT), str(APP_ROOT)):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

from config.sites import SITE_CATALOGO, SiteConfig, pegar_site, sites_habilitados
from scrapers.base.BaseScraper import BaseScraper

logger = logging.getLogger(__name__)

CATEGORY_TEMPLATE_CATALOG: dict[str, dict[str, str]] = {
    "pichau": {
        "perifericos": "scrapers.pichau.templates.perifericos.PichauPerifericosTemplate",
        "teclado": "scrapers.pichau.templates.hardware.PichauHardwareTemplate",
    },
}

PRODUCT_TEMPLATE_CATALOG = {
    "pichau": {
        "mouse": "perifericos",
        "headset": "perifericos",
        "monitor": "perifericos",
        "teclado": "teclado",
    },
}


class SiteFactory:
    @staticmethod
    def _carregar_exec(exec_path: str) -> type[BaseScraper]:
        modulo_nome, class_name = exec_path.rsplit(".", 1)
        module = importlib.import_module(modulo_nome)
        scraper_cls = getattr(module, class_name)
        if not issubclass(scraper_cls, BaseScraper):
            raise TypeError(f"{exec_path} não herda de BaseScraper")
        return scraper_cls

    @classmethod
    def _build(cls, site: SiteConfig) -> BaseScraper:
        scraper_cls = cls._carregar_exec(site.exec_path)
        scraper = scraper_cls()
        scraper.url = site.url
        scraper.paths = list(site.paths)
        logger.info(
            "Fábrica montou %s | exec_path=%s | url=%s | paths=%s",
            site.nome_site,
            site.exec_path,
            site.url,
            site.paths,
        )
        return scraper

    @classmethod
    def criar_site(cls, nome_site: str) -> BaseScraper:
        return cls._build(pegar_site(nome_site))

    @classmethod
    def criar_template_categoria(
        cls, nome_site: str, categoria: str
    ) -> BaseScraper | None:
        caminho_template = CATEGORY_TEMPLATE_CATALOG.get(
            nome_site.strip().lower(), {}
        ).get(categoria.strip().lower())
        if caminho_template is None:
            return None

        scraper_cls = cls._carregar_exec(caminho_template)
        scraper = scraper_cls()
        logger.info(
            "Fábrica selecionou template %s | loja=%s | categoria=%s",
            scraper_cls.__name__,
            nome_site,
            categoria,
        )
        return scraper

    @classmethod
    def criar_template_produto(
        cls, nome_site: str, produto: str
    ) -> BaseScraper | None:
        loja = nome_site.strip().lower()
        termos = set(produto.casefold().split())
        categorias = PRODUCT_TEMPLATE_CATALOG.get(loja, {})
        categoria = next(
            (categorias[termo] for termo in termos if termo in categorias),
            None,
        )
        if categoria is None:
            return None
        return cls.criar_template_categoria(loja, categoria)

    @classmethod
    def criar_sites_habilitados(cls) -> list[BaseScraper]:
        return [cls._build(site) for site in sites_habilitados()]

    @classmethod
    def disponiveis(cls) -> list[str]:
        return list(SITE_CATALOGO)
