import logging

from scrapers.site_factory import SiteFactory

logger = logging.getLogger(__name__)


def run(site_name: str | None = None) -> None:
    if site_name:
        scrapers = [SiteFactory.create(site_name)]
    else:
        scrapers = SiteFactory.create_enabled()

    if not scrapers:
        logger.warning("Nenhum scraper habilitado para executar")
        return

    for scraper in scrapers:
        logger.info("Iniciando fluxo de %s", scraper.loja)
        scraper.acessar_caminhos()
        logger.info("Fluxo de %s finalizado", scraper.loja)


if __name__ == "__main__":
    run()
