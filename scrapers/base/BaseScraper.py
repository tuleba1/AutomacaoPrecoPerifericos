import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List

import requests
from playwright.sync_api import Page, sync_playwright
 
from config.settings import SCRAPER_HEADLESS, SCRAPER_USER_AGENT
from database.connection import SessionLocal
from database.models import PrecoProduto

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

@dataclass

class itemColetado:
    produto: str
    preco: float
    url: str
    disponibilidade: bool = True

class BaseScraper(ABC):
    def init(self):
        self.loja = ''
        self.session = requests.Session()
        self.url = ''
        self.logger = logging.getLogger(self.loja)

    def acessar_pagina(self) -> bool:
        try:
            self.logger.info(f"Acessando a página {self.url}")
            response = self.session.get(self.url, headers=self.headers, timeout=20)

            if response.status_code == 200: 
                self.logger.info(f"Página acessada com sucesso")
                return True

            self.logger.error(f"Erro ao acessar a página {self.url}: {response.status_code}")
            return False

        except request.RequestException:
            self.logger.error(f"Erro ao acessar a página {self.loja}: {request.RequestException}")
            return False