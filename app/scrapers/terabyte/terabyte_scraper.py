from scrapers.base.BaseScraper import BaseScraper


class TerabyteScraper(BaseScraper):
    def __init__(self): 
        self.loja = "terabyte"
        self.url = "https://www.terabyteshop.com.br/"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "pt-BR,pt;q=0.7",
            "Cache-Control": "max-age=0",
            "Priority": "u=0, i",
            "Referer": "https://www.kabum.com.br/",
            "Sec-Ch-Ua": '"Chromium";v="154", "Brave";v="154", "Not A(Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Sec-Gpc": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
        }

