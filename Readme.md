# PC Price Monitor (MVP)

Monitoramento de precos de perifericos/pecas de PC em lojas como Kabum e Pichau,
com historico em PostgreSQL e API em FastAPI.

## Estrutura

Cada responsabilidade tem sua propria pasta — inclusive cada loja de scraper,
para que adicionar Amazon/Terabyte no futuro seja so criar uma pasta nova
sem mexer nas existentes.

```
pc-price-monitor/
├── config/
│   ├── settings.py           # variaveis de ambiente
│   └── sites.py              # catalogo e configuracao das lojas
├── database/
│   ├── connection.py         # engine/session SQLAlchemy + PostgreSQL
│   └── models.py             # tabela `precos` (produto, preco, loja, data_coleta)
├── app/
│   ├── domain/
│   └── scrapers/
│       ├── base/BaseScraper.py
│       ├── <loja>/            # scraper padrao por loja
│       ├── pichau/templates/  # fluxos especializados por categoria
│       ├── site_factory.py
│       └── run_scraper.py
├── api/
│   ├── main.py                # cria o app e registra os routers
│   ├── schemas.py
│   └── routers/
│       ├── produtos.py        # GET /produtos, GET /produtos/{produto}/mais-barato
│       └── historico.py       # GET /historico/{produto}
├── requirements.txt
├── main.py
└── .env.example
```

## Setup

1. Suba um Postgres local (ou use Docker):
   ```bash
   docker run --name pc-prices-db -e POSTGRES_USER=pc_user -e POSTGRES_PASSWORD=pc_pass \
     -e POSTGRES_DB=pc_prices -p 5432:5432 -d postgres:16
   ```

2. Instale as dependencias:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Copie `.env.example` para `.env` e configure apenas:
   - `SITES_ENABLED`
   - `PRODUCT_NAME`
   - `SCRAPER_HEADLESS`

4. Rode os scrapers:
   ```bash
   python main.py
   ```
   Cada loja executa acesso, pesquisa e extração nessa ordem; uma falha impede
   as etapas seguintes. Os resultados incluem o status e o motivo de cada etapa.

### Pesquisa por categoria

O fluxo seleciona o template automaticamente pelo `PRODUCT_NAME` e loja
habilitada. Exemplo:

```dotenv
SITES_ENABLED=pichau
PRODUCT_NAME=mouse
SCRAPER_HEADLESS=true
```

Para Pichau, a etapa `acessar_pagina` usa a URL padrão da loja
(`https://www.pichau.com.br`) e a etapa `pesquisar_produto` monta a rota de
listagem dinamicamente como `/perifericos/<produto>` (por exemplo:
`mouse` → `/perifericos/mouse`, `teclado` → `/perifericos/teclado`).

Se não houver template mapeado para o produto, o runner usa o scraper padrão da loja.

Para adicionar uma categoria:

1. Crie um template em `app/scrapers/<loja>/templates/` que herde do template
   comum da loja ou de `BaseScraper`. Sobrescreva acesso/validacao, pesquisa ou
   extracao somente quando a categoria exigir uma estrategia diferente.
2. Registre a categoria em `CATEGORY_TEMPLATE_CATALOG` em
   `app/scrapers/site_factory.py`, apontando para o caminho importavel da classe.
3. Acrescente testes para o roteamento e para o contrato de retorno do template.

Por exemplo, crie `app/scrapers/pichau/templates/headset.py`:

```python
from scrapers.pichau.pichau_scraper import PichauScraper
from .base import configurar_rota, validar_rota


class PichauHeadsetTemplate(PichauScraper):
    def __init__(self):
        super().__init__()
        configurar_rota(self, "PICHAU_HEADSET_URL", "/perifericos/headset")

    def validar_pagina(self, response):
        return validar_rota(self, response)
```

Depois, registre `"headset": "scrapers.pichau.templates.headset.PichauHeadsetTemplate"`
em `CATEGORY_TEMPLATE_CATALOG` e, se necessario, configure
`PICHAU_HEADSET_URL`. Nenhuma alteracao no fluxo global e necessaria.

5. Suba a API:
   ```bash
   uvicorn api.main:app --reload
   ```
   Docs interativas em http://localhost:8000/docs

## Endpoints

- `GET /produtos` — preco mais recente de cada produto por loja. Filtro opcional `?loja=kabum`.
- `GET /produtos/{produto}/mais-barato` — loja mais barata para um produto agora.
- `GET /historico/{produto}` — serie historica de precos (busca parcial no nome). Filtros opcionais `?loja=` e `?dias=`.

## Adicionando uma loja nova

1. Crie o scraper em `app/scrapers/<loja>/` herdando de `BaseScraper`.
2. Registre a loja em `SITE_CATALOGO`, em `config/sites.py`, informando o
   caminho da classe, URL e paths.
3. Para fluxos especializados, crie templates em
   `app/scrapers/<loja>/templates/` e adicione cada categoria a
   `CATEGORY_TEMPLATE_CATALOG` em `app/scrapers/site_factory.py`.

## Antes de rodar de verdade

Os seletores CSS em `scrapers/kabum/scraper.py` e `scrapers/pichau/scraper.py`
sao um ponto de partida e **precisam ser conferidos no DevTools do navegador**
contra o HTML atual dessas paginas, pois sites de e-commerce mudam o markup
com frequencia e nao houve acesso de rede a esses dominios neste ambiente
para validar.

A implementação base pesquisa usando um formulário HTML GET/POST e extrai
preços associados a produtos em JSON-LD. Lojas sem esse formulário ou markup
devem sobrescrever `pesquisar_produto` ou `extrair_preco` no scraper da loja.

## Proximos passos sugeridos

- Agendamento automatico (cron ou APScheduler) para rodar `scrapers.run_scrapers` periodicamente.
- Alertas de queda de preco (checar no `salvar()` se o novo preco < minimo historico e disparar Telegram/e-mail).
- Scrapers para Amazon e Terabyte seguindo o mesmo padrao de `BaseScraper`.
- Camada LangChain/LlamaIndex consultando o Postgres (ou um index vetorial sobre os nomes de produto) para perguntas em linguagem natural.
- Migrations com Alembic em vez de `create_all` direto.
