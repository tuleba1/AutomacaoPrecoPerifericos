import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings

try:
    from .site_factory import SiteFactory
except ImportError:
    from site_factory import SiteFactory

from scrapers.base.BaseScraper import BaseScraper

logger = logging.getLogger(__name__)

PRODUCT_NAME = settings.PRODUCT_NAME
PRODUCTS_SEARCH = getattr(
    settings,
    "PRODUCTS_SEARCH",
    settings.csv_env("PRODUTOS_PESQUISA", "", lowercase=True),
)


def _executar_fluxo(scraper: BaseScraper, produto: str) -> dict:
    logger.info("Iniciando fluxo de %s para %s", settings.SITES_ENABLED, produto)
    resultado = scraper.executar_extracao(produto)
    for nome_etapa, etapa in resultado.get("etapas", {}).items():
        pendente = " (não executada)" if not etapa.get("executada", True) else ""
        logger.info(
            "[%s] Etapa %s: %s%s",
            "OK" if etapa["status"] == "OK" else "ERROR",
            nome_etapa,
            etapa["status"],
            pendente,
        )

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
    return resultado


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
        if not PRODUCTS_SEARCH:
            fluxo = SiteFactory.criar_template_produto(scraper.loja, PRODUCT_NAME)
            if fluxo is None:
                fluxo = scraper
            else:
                logger.info(
                    "[OK] Template selecionado: %s para o produto %s",
                    type(fluxo).__name__,
                    PRODUCT_NAME,
                )
            resultados.append(_executar_fluxo(fluxo, PRODUCT_NAME))
            continue

        scraper_disponivel = scraper
        for categoria in PRODUCTS_SEARCH:
            logger.info("[OK] Categoria identificada: %s", categoria)
            fluxo = SiteFactory.criar_template_categoria(scraper.loja, categoria)
            if fluxo is None:
                fluxo = SiteFactory.criar_template_produto(scraper.loja, categoria)
                produto_pesquisa = categoria
            else:
                produto_pesquisa = PRODUCT_NAME
            if fluxo is None:
                logger.info(
                    "Sem template para loja=%s e categoria=%s; usando fluxo padrão",
                    scraper.loja,
                    categoria,
                )
                fluxo = scraper_disponivel or SiteFactory.criar_site(scraper.loja)
                scraper_disponivel = None
            else:
                logger.info(
                    "[OK] Template selecionado: %s",
                    type(fluxo).__name__,
                )
            resultados.append(_executar_fluxo(fluxo, produto_pesquisa))
    return resultados


if __name__ == "__main__":
    run()
