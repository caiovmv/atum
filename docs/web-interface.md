# Interface web (Atum)

A interface web **Atum** permite buscar torrents e gerenciar a fila de downloads pelo navegador. Ela usa uma API que fala com o **Download Runner** (processo que mantém a fila e as threads de download).

## Arquitetura

- **Download Runner** (`dl-torrent runner`): processo FastAPI na porta 9092 que expõe a fila (GET/POST /downloads, start, stop, delete). Use a variável de ambiente `DOWNLOAD_RUNNER_URL` para que a API e o CLI apontem para ele.
- **API Web** (`dl-torrent serve`): processo FastAPI na porta 8000 que oferece busca (GET /api/search), adicionar a partir da busca (POST /api/add-from-search) e proxy de todas as rotas de downloads para o Runner. Serve também o frontend Atum em `/`.
- **Console Atum**: SPA em React (sidebar + área principal, tema escuro). Build em `frontend/dist`; a API Web serve esses arquivos quando o diretório existe.

## Como subir

1. **Terminal 1 – Runner** (fila de downloads):
   ```bash
   dl-torrent runner
   ```
   Por padrão escuta em `http://127.0.0.1:9092`.

2. **Terminal 2 – API Web + Atum**:
   ```bash
   set DOWNLOAD_RUNNER_URL=http://127.0.0.1:9092
   dl-torrent serve
   ```
   Por padrão escuta em `http://0.0.0.0:8000`. Abra no navegador: **http://localhost:8000**

3. **Build do frontend** (só precisa uma vez, ou após mudanças no React):
   ```bash
   cd frontend && npm install && npm run build && cd ..
   ```
   Se `frontend/dist` não existir, a API Web não monta a SPA; você ainda pode usar a API em `/api/*`.

## Variáveis de ambiente

| Variável | Uso |
|----------|-----|
| `DOWNLOAD_RUNNER_URL` | URL do Runner (ex.: `http://127.0.0.1:9092`). Usada pela API Web para proxy de downloads e pelo CLI em modo remoto. |

## CLI em modo remoto

Com o Runner em execução e `DOWNLOAD_RUNNER_URL` definida e acessível, os comandos `download add`, `download list`, `download start`, `download stop` e `download delete` delegam ao Runner. Assim, você pode usar o CLI em uma máquina e a fila rodar em outra (ou no mesmo processo do Runner).

Exemplo (em outro terminal, com Runner e API já rodando):
```bash
set DOWNLOAD_RUNNER_URL=http://127.0.0.1:9092
dl-torrent download list
dl-torrent download add "magnet:?xt=..."
```

## Rotas da API

- `GET /api/search?q=...&limit=200&sort_by=seeders|size&content_type=music|movies|tv` — busca; retorna lista de resultados serializados.
- `POST /api/add-from-search` — body: `query`, `indices[]`, `content_type`, `save_path?`, etc.; reexecuta a busca, resolve magnets e envia ao Runner.
- `GET /api/downloads?status=` — lista downloads (proxy Runner).
- `POST /api/downloads` — adiciona download (proxy Runner).
- `POST /api/downloads/{id}/start` — inicia (proxy Runner).
- `POST /api/downloads/{id}/stop` — para (proxy Runner).
- `DELETE /api/downloads/{id}?remove_files=false` — remove (proxy Runner).
