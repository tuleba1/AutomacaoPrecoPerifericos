from scrapers.base.BaseScraper import BaseScraper


class AmazonScraper(BaseScraper):
    def __init__(self):
        self.loja = "amazon"
        self.url = "https://www.amazon.com.br"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Chromium";v="154", "Brave";v="154", "Not A(Brand";v="99"',
            "Sec-Ch-Ua-Full-Version-List": (
                '"Chromium";v="154.0.0.0", "Brave";v="154.0.0.0", "Not A(Brand";v="99.0.0.0"'
            ),
            "Sec-Ch-Ua-Platform": "Android",
            "Sec-Ch-Ua-Platform-Version": "15",
            "Upgrade-Insecure-Requests": "1",
        }
    #AMAZON BLOQUEANDO PARA ACESSAR 