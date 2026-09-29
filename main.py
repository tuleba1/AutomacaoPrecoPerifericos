import argparse
import logging

from config.settings import SITES_ENABLED
from scrapers.run_scraper import run
from scrapers.site_factory import SiteFactory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("debug")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa o fluxo completo dos scrapers (debug)."
    )
    parser.add_argument(
        "--site",
        choices=SiteFactory.disponiveis(),
        help="Roda só um site do catálogo. Sem este argumento, usa SITES_ENABLED.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger.info("Iniciando fluxo de debug")
    if args.site:
        logger.info("Site selecionado via CLI: %s", args.site)
    else:
        logger.info("Sites habilitados via env: %s", ", ".join(SITES_ENABLED))
    run(site_name=args.site)
    logger.info("Fluxo de debug finalizado")


if __name__ == "__main__":
    main()
