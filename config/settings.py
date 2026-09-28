import os

from dotenv import load_dotenv

load_dotenv()


def csv_env(name: str, default: str, *, lowercase: bool = False) -> list[str]:
    raw = os.getenv(name, default)
    items = [item.strip() for item in raw.split(",") if item.strip()]
    if lowercase:
        return [item.lower() for item in items]
    return items


SCRAPER_USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
)
SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
SITES_ENABLED = csv_env(
    "SITES_ENABLED",
    "kabum,pichau,amazon,terabyte",
    lowercase=True,
)
