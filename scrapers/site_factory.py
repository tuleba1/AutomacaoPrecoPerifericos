import importlib
import logging

from config.sites import SITE_CATALOG, SiteConfig, enabled_sites, get_site
from scrapers.base.BaseScraper import BaseScraper

logger = logging.getLogger(__name__)


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
    def criar_site(cls, site_name: str) -> BaseScraper:
        return cls._build(get_site(site_name))

        @classmethod
        def criar_sites_habilitados(cls) -> list[BaseScraper]:
        return [cls._build(site) for site in enabled_sites()]

    @classmethod
    def disponiveis(cls) -> list[str]:
        return list(SITE_CATALOG)
