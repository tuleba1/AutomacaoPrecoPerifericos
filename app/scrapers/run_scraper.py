import logging
from config.settings import PRODUCT_NAME

try:
    from .site_factory import SiteFactory
except ImportError:
    from site_factory import SiteFactory

logger = logging.getLogger(__name__)


def run(site_name: str | None = None) -> list[dict]:
    if site_name:
        scrapers = [SiteFactory.criar_site(site_name)]
    else:
        scrapers = SiteFactory.criar_sites_habilitados()

    if not scrapers:
        logger.warning("Nenhum scraper habilitado para executar")
        return []

    resultados = []
    for scraper in scrapers:
        logger.info("Iniciando fluxo de %s", scraper.loja)
        resultado = scraper.executar_extracao(PRODUCT_NAME)
        resultados.append(resultado)
        if resultado["status"] == "OK":
            logger.info(
                "Fluxo de %s finalizado: produto=%s, preco=%s",
                scraper.loja,
                resultado["produto"],
                resultado["preco"],
            )
        else:
            logger.error(
                "Fluxo de %s interrompido: %s",
                scraper.loja,
                resultado["erro"],
            )
    return resultados


if __name__ == "__main__":
    run()
