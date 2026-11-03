from scrapers.pichau.pichau_scraper import PichauScraper

from .hardware import PichauHardwareTemplate
from .perifericos import PichauPerifericosTemplate

__all__ = [
    "PichauScraper",
    "PichauHardwareTemplate",
    "PichauPerifericosTemplate",
]
