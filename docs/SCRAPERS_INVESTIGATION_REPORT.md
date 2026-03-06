# Relatório final: investigação dos scrapers (TG, Torlock, SpeedTorrent, FitGirl, RuTracker, RARBG, EXT)

**Data:** Março 2025  
**Contexto:** Testes com 3 buscas (avatar, led zeppelin, fringe) apontaram 7 indexadores retornando 0 resultados. Este documento resume o diagnóstico e as alterações feitas.

> **Nota (removidos em definitivo):** Os 7 indexadores (tg, torlock, speedtorrent, fitgirl, rutracker, rarbg, ext) foram removidos do projeto por continuarem retornando 0 resultados. O documento permanece como histórico.

---

## 1. Resumo executivo

| Indexador      | Causa raiz                          | Correção aplicada                    | Status esperado                    |
|----------------|-------------------------------------|--------------------------------------|------------------------------------|
| **TG**         | FlareSolverr retorna 500            | Fallback para requisição direta      | Depende de FlareSolverr estável   |
| **Torlock**    | Links de detalhe em outro domínio   | Usar base + /torrent/ID/slug         | Deve retornar resultados           |
| **SpeedTorrent** | FlareSolverr 500 / site bloqueia  | Fallback no _common                  | Depende de FlareSolverr ou acesso  |
| **FitGirl**    | Magnet só na página do post         | Buscar links de posts e fetch       | Deve retornar se houver posts     |
| **RuTracker**  | Magnet no tópico; regex restritiva | Regex mais permissiva (viewtopic)   | Pode retornar se houver tópicos   |
| **RARBG**      | Proxy retorna 39 bytes (bloqueio)  | Nenhuma (proxy instável)             | Não mantido                        |
| **EXT**        | Detalhes em formato slug-mID       | Regex para slug-mID em ext.to       | Depende do HTML da busca           |

---

## 2. Diagnóstico detalhado

### 2.1 Ferramenta de diagnóstico

Foi usado o script `scripts/scraping/debug_failing.py`, que para cada indexador:

- Chama `get_url(URL_DE_BUSCA)` (com FLARESOLVERR_URL quando definido).
- Verifica: sucesso da requisição, tamanho do HTML, presença de `magnet:?xt=`, quantidade de links de detalhe quando aplicável.

### 2.2 Resultados do diagnóstico (ambiente com FlareSolverr em localhost:8191)

| Indexador   | Requisição   | Tamanho HTML | Tem magnet na listagem? | Observação                          |
|-------------|-------------|--------------|--------------------------|-------------------------------------|
| TG          | **500**     | —            | —                        | Erro no FlareSolverr (v1)            |
| Torlock     | OK (fallback) | 707k       | Não                      | 104 links /torrent/ID/slug; muitos para t0r.space |
| SpeedTorrent| **500**     | —            | —                        | Erro no FlareSolverr                 |
| FitGirl     | OK          | 115k         | Não                      | Magnet na página do post             |
| RuTracker   | OK          | 12k          | Não                      | Magnet na página do tópico           |
| RARBG       | OK          | **39 bytes** | Não                     | Resposta mínima (bloqueio do proxy)  |
| EXT         | OK          | 708k         | Não                      | Detalhes em formato slug-mID         |

---

## 3. Alterações realizadas

### 3.1 `scripts/scraping/_common.py`

- **Fallback quando FlareSolverr falha:**  
  Em `get_url()`, se a chamada ao FlareSolverr levantar exceção (por exemplo 5xx ou timeout), é feita **uma tentativa** de requisição direta (`_fetch_direct`), sem FlareSolverr.  
  Assim, sites que respondem à requisição direta (ex.: Torlock na listagem) passam a retornar HTML mesmo com FlareSolverr instável.

- **Nova função:** `_fetch_direct(url, timeout)` — faz GET direto (session + User-Agent) e aplica a mesma detecção de página bloqueada (`_is_blocked_page`).

### 3.2 `scripts/scraping/torlock/scrape.py`

- **Problema:** Na página de busca, os links de detalhe apontavam para outro host (ex.: `http://sqmw21h.t0r.space/torrent/...`). Ao seguir esses links, a resposta tinha ~62 bytes (inútil).
- **Solução:**  
  - Regex de detalhe passou a capturar **slug** (terceiro grupo): `.../torrent/(\d+)/([^"]*\.html)`.  
  - Para cada link **em outro host**, em vez de usar a URL do espelho, é construída a URL no domínio base: `base + "/torrent/" + tid + "/" + slug` (ex.: `https://www.torlock.com/torrent/741184/Avatar.8l9.html`).  
  - Assim, as páginas de detalhe são sempre buscadas no `TORLOCK_BASE_URL` configurado no `.env`.

### 3.3 `scripts/scraping/ext/scrape.py`

- **Problema:** ext.to usa URLs de detalhe no formato **slug-mID** (ex.: `https://ext.to/avatar-m142766/`), e não apenas `/torrent/ID` ou `/t/ID`.
- **Solução:** Inclusão de dois novos padrões para detalhe:  
  - `https?://[^"]*ext\.to/[^"]*-m(\d+)/?`  
  - `/([^"]*-m(\d+)/?)` (relativo).  
  Os IDs são desduplicados e as URLs de detalhe são buscadas para extrair o magnet. A listagem da busca continua sem magnet; o scraper depende de existirem esses links no HTML.

### 3.4 `scripts/scraping/fitgirl/scrape.py`

- **Problema:** Na página de busca (`/?s=...`) não há links magnet; o magnet está na página de cada **post**.
- **Solução:** Quando nenhum magnet é encontrado na listagem:  
  - Coleta de links para posts do mesmo domínio (regex que inclui o host do FitGirl e exclui `?s=`, `/feed`, `/page/`).  
  - Para cada URL de post (até `limit`), faz `get_url(post_url)` e procura `magnet_re` no HTML.  
  - Título continua vindo de `entry-title`, do magnet `dn` ou do link antes do magnet.

### 3.5 `scripts/scraping/rutracker/scrape.py`

- **Problema:** Magnet não está na página de busca; está na página do tópico (`viewtopic.php?t=ID`). O regex de links de tópico era restritivo (`href="[^"]*viewtopic\.php\?t=(\d+)..."`).
- **Solução:** Regex simplificada para `viewtopic\.php\?t=(\d+)`, sem exigir formato exato do `href`, para capturar IDs de tópico em qualquer contexto no HTML. As URLs de tópico são montadas como `base + "/forum/viewtopic.php?t=" + tid` e cada uma é buscada para extrair o magnet.

### 3.6 RARBG

- Nenhuma alteração de código. O proxy (rarbgproxy.to) retornou 39 bytes; o scraper já está documentado como **não mantido** (RARBG oficial encerrado em 2023). Comportamento esperado: lista vazia ou erro quando o proxy estiver bloqueado ou indisponível.

### 3.7 TG e SpeedTorrent

- Apenas o **fallback** do `_common` se aplica. Se o FlareSolverr retornar 5xx ou falhar, o scraper tenta requisição direta. Se o site bloquear a requisição direta (Cloudflare, etc.), o resultado continua sendo lista vazia até que:  
  - o FlareSolverr responda 200 para esse domínio, ou  
  - o ambiente (proxy, VPN, etc.) permita acesso direto.

---

## 4. Arquivos modificados (lista)

| Arquivo | Alteração |
|---------|-----------|
| `scripts/scraping/_common.py` | Fallback para requisição direta em falha do FlareSolverr; nova `_fetch_direct()`. |
| `scripts/scraping/torlock/scrape.py` | Regex de detalhe com slug; URLs de detalhe sempre no domínio base quando o link é de outro host. |
| `scripts/scraping/ext/scrape.py` | Regex para detalhes no formato slug-mID (ext.to). |
| `scripts/scraping/fitgirl/scrape.py` | Busca de links de posts na listagem e fetch de cada post para obter magnet. |
| `scripts/scraping/rutracker/scrape.py` | Regex mais permissiva para `viewtopic.php?t=ID`. |
| `scripts/scraping/debug_failing.py` | Script de diagnóstico (mantido para testes). |

---

## 5. Como testar

Na raiz do projeto, com `.env` carregado e `FLARESOLVERR_URL` definido (se desejar usar FlareSolverr):

```bash
# Um indexador, uma busca
python -m scripts.scraping.torlock.scrape avatar
python -m scripts.scraping.ext.scrape avatar
python -m scripts.scraping.fitgirl.scrape avatar
python -m scripts.scraping.rutracker.scrape avatar
python -m scripts.scraping.tg.scrape avatar
python -m scripts.scraping.speedtorrent.scrape avatar
python -m scripts.scraping.rarbg.scrape avatar
```

Ou o teste em lote (3 buscas: avatar, led zeppelin, fringe):

```bash
python -m scripts.scraping.run_all_tests
```

Critério de sucesso: pelo menos um item com `magnet` iniciando por `magnet:?xt=urn:btih:`.

---

## 6. Variáveis de ambiente relevantes

No `.env` (ou ambiente), para os scrapers usarem as URLs corretas:

- `FLARESOLVERR_URL` — opcional; quando definido, requisições passam pelo FlareSolverr (com fallback direto em falha).
- `TG_BASE_URL` — ex.: https://torrentgalaxy.one  
- `TORLOCK_BASE_URL` — ex.: https://www.torlock.com  
- `SPEEDTORRENT_BASE_URL` — ex.: https://www.speedtorrent.re  
- `FITGIRL_BASE_URL` — ex.: https://fitgirl-repacks.site  
- `RUTRACKER_BASE_URL` — ex.: https://rutracker.org  
- `RARBG_BASE_URL` — ex.: https://www.rarbgproxy.to  
- `EXT_BASE_URL` — ex.: https://ext.to  

---

## 7. Conclusão

- **Torlock, FitGirl, RuTracker e EXT** tiveram ajustes de lógica e regex; em ambiente com acesso às páginas (e, quando aplicável, FlareSolverr ou fallback funcionando), devem passar a retornar resultados quando houver conteúdo compatível.
- **TG e SpeedTorrent** dependem de FlareSolverr estável ou de acesso direto aos domínios; o fallback reduz falhas quando apenas o FlareSolverr estiver com 5xx.
- **RARBG** permanece como não mantido; comportamento atual (lista vazia ou erro com proxy bloqueado) é esperado.

Este relatório pode ser usado como referência para manutenção futura e para validar o comportamento dos scrapers em novos ambientes ou após mudanças nos sites.
