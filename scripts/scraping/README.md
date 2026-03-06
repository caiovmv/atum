# Scripts de scraping por indexador

Scripts **isolados** para testar e afinar o scraping de cada indexador (magnet e/ou .torrent).  
Ainda **não estão integrados** ao app principal; servem para validar e ajustar os seletores antes de incorporar em `src/app/search.py`.

## Estrutura

- `_common.py` — helpers compartilhados (get_url, get_url_json, output_results, etc.). **Todos os scrapers usam apenas get_url() ou get_url_json()** para HTTP; quando `FLARESOLVERR_URL` está definido no `.env`, **todas** as requisições passam pelo FlareSolverr.
- `{indexer_name}/scrape.py` — script por indexador.

## Como rodar

Na raiz do projeto (onde está `src/` e `scripts/`):

```bash
# Exemplo: buscar "ubuntu" no 1337x
python -m scripts.scraping.1337x.scrape "ubuntu"

# Saída JSON (padrão)
python -m scripts.scraping.tpb.scrape "debian"

# Saída legível (sem JSON)
python -m scripts.scraping.tpb.scrape "debian" --no-json
```

Cada script aceita:

1. **Query** (obrigatório): termo de busca.
2. **--no-json** (opcional): imprime resultados em texto em vez de JSON.

Variáveis de ambiente para base URL de cada site: o `_common.py` carrega o `.env` da raiz do projeto (se existir e `python-dotenv` estiver instalado). Use as URLs que você validou no `.env`; veja o docstring no topo de cada `scrape.py`. Exemplo de variáveis: `X1337_BASE_URL`, `TPB_BASE_URL`, `TG_BASE_URL`, `YTS_BASE_URL`, `EZTV_BASE_URL`, `NYAA_BASE_URL`, `LIMETORRENTS_BASE_URL`, `TORLOCK_BASE_URL`, `FITGIRL_BASE_URL`, `RUTRACKER_BASE_URL`, `RARBG_BASE_URL`, `EXT_BASE_URL`.

## Dependências

- `requests` (para todos os que fazem HTTP).
- **Cloudflare, reCAPTCHA e outros captchas:** para sites protegidos (1337x, TorrentGalaxy, etc.), o `_common.py` tenta duas abordagens:
  1. **cloudscraper** — instale e use normalmente; é usado automaticamente quando disponível.
  ```bash
  pip install cloudscraper
  # ou
  pip install dl-torrent[scraping]
  ```
  Para desativar o bypass (usar só requests): `SCRAPING_BYPASS_CLOUDFLARE=0`.

  2. **FlareSolverr** — se mesmo com cloudscraper o site bloquear (proteção forte, reCAPTCHA, hCaptcha, Turnstile, etc.), use o [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr): adicione o serviço ao `docker-compose.yml`, suba com `docker compose up -d flaresolverr` e defina no `.env`: `FLARESOLVERR_URL=http://localhost:8191`. **Todos os scrapers** (1337x, tpb, tg, yts, eztv, nyaa, etc.) usam `get_url`/`get_url_json` do `_common.py`, que consulta `FLARESOLVERR_URL` primeiro; se estiver definido, a requisição é feita via FlareSolverr e o HTML/JSON retornado é usado. A detecção de página bloqueada considera Cloudflare, reCAPTCHA, hCaptcha, Turnstile; nesses casos, sem FlareSolverr configurado é lançado um erro sugerindo configurar `FLARESOLVERR_URL`.

Alguns indexadores usam bibliotecas extras no app (ex.: py1337x, tpblite); estes scripts usam apenas `requests` + regex/API para ficarem autocontidos e afináveis.

## Indexadores

| Pasta        | Site        | Magnet | .torrent |
|-------------|-------------|--------|----------|
| 1337x       | 1337x       | sim    | opcional |
| tpb         | The Pirate Bay | sim | opcional |
| yts         | YTS (API)   | sim    | —        |
| eztv        | EZTV        | sim    | —        |
| nyaa        | Nyaa        | sim    | —        |
| limetorrents| LimeTorrents| sim    | —        |
| iptorrents  | (stub)      | privado| —        |

### Status: você consegue magnet (ou .torrent)?

Todos os scrapers **só retornam magnet** por enquanto (nenhum preenche link .torrent). O que cada um faz:

| Indexador   | Magnet funciona? | Se der errado: motivo / correção |
|-------------|------------------|----------------------------------|
| **1337x**   | ✅ Sim           | Busca + página de detalhe; FlareSolverr resolve. |
| **TPB**     | ✅ Sim           | Magnet na listagem; `html.unescape` no _common corrige `&amp;`. Título pode vir "Torrent" se o site não tiver `detLink`. |
| **YTS**     | ✅ Sim           | API JSON; hash convertido para magnet no script. Com FlareSolverr a resposta da API é usada igual. |
| **Nyaa**    | ✅ Sim           | Magnet na linha; título às vezes vinha como categoria — ajuste de parsing para preferir o nome do torrent. |
| **EZTV**    | ⚠️ Depende       | Magnet pode estar só na página do episódio (/ep/); na busca às vezes não há magnet direto. |
| **LimeTorrents** | ⚠️ Depende   | Sites/espelhos mudam HTML; se retornar `[]`, o layout da página não bate com os regex atuais — dá para corrigir ajustando os seletores no `scrape.py` do indexador. |
| **IPTorrents** | ❌ Stub        | Tracker privado; não implementado. |

---

## APIs e projetos prontos (recomendado)

Em vez de manter só scraping manual com regex, vale usar **bibliotecas ou APIs** já mantidas pela comunidade. O app já usa **py1337x** e **tpblite** em `src/app/search.py`; para os outros indexadores, estas opções ajudam:

### 1. Torrent-Api-py (Python) — **recomendado**

- **Repo:** [Ryuk-me/Torrent-Api-py](https://github.com/Ryuk-me/Torrent-Api-py) (~400 stars)
- **O que é:** API FastAPI que faz scraping em 1337x, PirateBay, Nyaasi, Torlock, Torrent Galaxy (tgx), YTS, Limetorrent, TorrentFunk, Glodls, TorrentProject, Kickass, Bitsearch, MagnetDL, Libgen, YourBittorrent.
- **Uso:** Rodar como serviço (`python main.py` → porta 8009) e chamar `GET /api/v1/search?site=1337x&query=...` (ou `site=tgx`, `piratebay`, `eztv` não listado mas há vários). Ou reutilizar os módulos em `torrents/` dentro do nosso código.
- **API pública (pode cair):** `https://torrent-api-py-nx0x.onrender.com/api/v1/search?site=1337x&query=avengers`
- **Obs:** Issues conhecidos: Cloudflare no 1337x, CAPTCHA no TorrentGalaxy; mesmo assim cobre mais sites e é mantido.

### 2. Torrent-Search-API (Node.js)

- **Repo:** [theriturajps/Torrent-Search-API](https://github.com/theriturajps/Torrent-Search-API)
- **O que é:** API HTTP que agrega 1337x, YTS, EZTV, TorrentGalaxy (tgx), Torlock, PirateBay, Nyaasi, Rarbg, Limetorrent, KickAss, Bitsearch, Glodls, TorrentFunk, TorrentProject (alguns domínios podem estar mortos).
- **Exemplo:** `GET https://itorrentsearch.vercel.app/api/1337x/avengers` ou `/api/eztv/...`, `/api/tgx/...`.
- **Uso no dl-torrent:** chamar essa API via `requests` como mais um backend de busca (sem depender de Node no nosso projeto).

### 3. Jackett / Prowlarr (serviço externo)

- **Jackett:** [Jackett/Jackett](https://github.com/Jackett/Jackett) — proxy que expõe vários indexadores em uma API única.
- **Prowlarr:** [Prowlarr/Prowlarr](https://github.com/Prowlarr/Prowlarr) — evolução/alternativa, integra com *arr (Radarr, Sonarr, etc.).
- **Uso:** Usuário instala Jackett ou Prowlarr, configura os indexadores que quiser; o dl-torrent chama a API do Jackett/Prowlarr (ex.: `/api/v2.0/indexers/all/results?apikey=...&Query=...`) e recebe resultados já normalizados (magnet, título, seeders, etc.). Um único backend cobre dezenas de sites.

### 4. Bibliotecas Python por site (já usadas ou úteis)

| Site   | Biblioteca / API        | Uso no projeto                          |
|--------|-------------------------|-----------------------------------------|
| 1337x  | **py1337x** (PyPI: `1337x`) | Já usado em `src/app/search.py`        |
| TPB    | **tpblite**             | Já usado em `src/app/search.py`        |
| YTS    | API JSON oficial        | Já usado (GET yts.mx/api/v2/list_movies.json) |

### Próximos passos sugeridos

1. **Curto prazo:** Testar a API do Torrent-Api-py (deploy público ou local) para 1337x, nyaasi, limetorrent, yts; se estável, usar como backend opcional em `search.py` (ex.: env `USE_TORRENT_API_PY_URL`).
2. **Médio prazo:** Suportar **Jackett/Prowlarr** como fonte opcional: se o usuário tiver configurado, o dl-torrent usa só essa API e dispensa scraping próprio para a maioria dos indexadores.
3. **Scripts nesta pasta:** Manter para debug e fallback; quando integrar uma API/biblioteca, marcar no README qual indexador está coberto por qual backend (py1337x, tpblite, Torrent-Api-py, Jackett, etc.).
