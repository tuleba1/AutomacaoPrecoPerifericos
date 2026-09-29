import os
from dataclasses import dataclass

from config.settings import SITES_ENABLED, csv_env


@dataclass(frozen=True)
class SiteConfig:
    nome_site: str
    exec_path: str
    url: str
    paths: tuple[str, ...]
    user_agent: str | None = None


def _site(
    nome_site: str,
    exec_path: str,
    default_url: str,
    default_paths: str = "/",
) -> SiteConfig:
    prefixo = nome_site.upper()
    url = os.getenv(f"{prefixo}_URL", default_url)
    paths = tuple(csv_env(f"{prefixo}_PATHS", default_paths))
    user_agent = os.getenv(f"{prefixo}_USER_AGENT") or None
    return SiteConfig(
        nome_site=nome_site,
        exec_path=exec_path,
        url=url,
        paths=paths,
        user_agent=user_agent,
    )


SITE_CATALOGO: dict[str, SiteConfig] = {
    "kabum": _site(
        "kabum",
        "scrapers.kabum.kabum_scraper.KabumScraper",
        "https://www.kabum.com.br",
    ),
    "pichau": _site(
        "pichau",
        "scrapers.pichau.pichau_scraper.PichauScraper",
        "https://www.pichau.com.br",
    ),
    "amazon": _site(
        "amazon",
        "scrapers.amazon.amazon_scraper.AmazonScraper",
        "https://www.amazon.com.br",
    ),
    "terabyte": _site(
        "terabyte",
        "scrapers.terabyte.terabyte_scraper.TerabyteScraper",
        "https://www.terabyteshop.com.br/",
    ),
}


def pegar_site(nome_site: str) -> SiteConfig:
    chave = nome_site.strip().lower()
    if chave not in SITE_CATALOGO:
        disponiveis = ", ".join(SITE_CATALOGO)
        raise KeyError(f"Site '{nome_site}' não está no catálogo. Disponíveis: {disponiveis}")
    return SITE_CATALOGO[chave]


def sites_habilitados() -> list[SiteConfig]:
    desconhecidos = [nome for nome in SITES_ENABLED if nome not in SITE_CATALOGO]
    if desconhecidos:
        disponiveis = ", ".join(SITE_CATALOGO)
        raise ValueError(
            f"SITES_ENABLED contém sites inválidos: {desconhecidos}. "
            f"Disponíveis: {disponiveis}"
        )
    return [SITE_CATALOGO[nome] for nome in SITES_ENABLED]
