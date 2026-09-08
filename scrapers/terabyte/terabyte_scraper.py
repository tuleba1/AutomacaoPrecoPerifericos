class TerabyteScraper(TemplateScraper):
    def __init__(self):
        super().__init__()
        self.loja = 'terabyte'
        self.url = 'https://www.terabyteshop.com.br/'
        self.headers = {
            'User-Agent': config.settings.SCRAPER_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }