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
│   └── settings.py           # todas as variaveis de ambiente centralizadas
├── database/
│   ├── connection.py         # engine/session SQLAlchemy + PostgreSQL
│   └── models.py             # tabela `precos` (produto, preco, loja, data_coleta)
├── scrapers/
│   ├── base/
│   │   └── scraper_base.py   # classe base (Playwright + salvar no banco)
│   ├── kabum/
│   │   └── scraper.py
│   ├── pichau/
│   │   └── scraper.py
│   └── run_scrapers.py       # roda todos os scrapers de uma vez
├── api/
│   ├── main.py                # cria o app e registra os routers
│   ├── schemas.py
│   └── routers/
│       ├── produtos.py        # GET /produtos, GET /produtos/{produto}/mais-barato
│       └── historico.py       # GET /historico/{produto}
├── requirements.txt
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

3. Copie `.env.example` para `.env` e ajuste `DATABASE_URL` se necessario.

4. Rode os scrapers (cria as tabelas automaticamente na primeira execucao):
   ```bash
   python -m scrapers.run_scrapers
   ```

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

1. Crie `scrapers/<loja>/scraper.py` com uma classe que herda de `BaseScraper`
   (veja `scrapers/kabum/scraper.py` como referencia).
2. Adicione a classe na lista `SCRAPERS` em `scrapers/run_scrapers.py`.

## Antes de rodar de verdade

Os seletores CSS em `scrapers/kabum/scraper.py` e `scrapers/pichau/scraper.py`
sao um ponto de partida e **precisam ser conferidos no DevTools do navegador**
contra o HTML atual dessas paginas, pois sites de e-commerce mudam o markup
com frequencia e nao houve acesso de rede a esses dominios neste ambiente
para validar.

## Proximos passos sugeridos

- Agendamento automatico (cron ou APScheduler) para rodar `scrapers.run_scrapers` periodicamente.
- Alertas de queda de preco (checar no `salvar()` se o novo preco < minimo historico e disparar Telegram/e-mail).
- Scrapers para Amazon e Terabyte seguindo o mesmo padrao de `BaseScraper`.
- Camada LangChain/LlamaIndex consultando o Postgres (ou um index vetorial sobre os nomes de produto) para perguntas em linguagem natural.
- Migrations com Alembic em vez de `create_all` direto.