# Configuração

A configuração do dl-torrent é feita por variáveis de ambiente. O jeito mais simples é usar um arquivo `.env` na raiz do projeto (ou no diretório de trabalho).

## Criar o arquivo .env

Copie o arquivo de exemplo e edite:

```bash
cp .env.example .env
```

Edite `.env` com um editor de texto e preencha pelo menos o tipo de cliente e as variáveis do cliente escolhido.

## Variáveis por tema

### Cliente de torrent

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `CLIENT_TYPE` | Cliente usado para receber os magnets: `transmission`, `utorrent` ou `folder` | `transmission` |

**Transmission** (quando `CLIENT_TYPE=transmission`):

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `TRANSMISSION_HOST` | Host do daemon Transmission | `localhost` |
| `TRANSMISSION_PORT` | Porta RPC | `9091` |
| `TRANSMISSION_USER` | Usuário (deixe vazio se não usar) | — |
| `TRANSMISSION_PASSWORD` | Senha | — |

**uTorrent** (quando `CLIENT_TYPE=utorrent`):

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `UTORRENT_URL` | URL da Web UI (ex.: `http://localhost:8080`) | `http://localhost:8080` |
| `UTORRENT_USER` | Usuário | `admin` |
| `UTORRENT_PASSWORD` | Senha | — |

**Folder** (quando `CLIENT_TYPE=folder` — FrostWire ou pasta monitorada):

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `WATCH_FOLDER` | Pasta onde o app grava os magnet links em `magnets.txt`; você pode colar no FrostWire ou usar uma pasta monitorada pelo cliente | `./torrents` |

### Pastas

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `DOWNLOAD_DIR` | Pasta de destino dos downloads (usada pelo Transmission/uTorrent ou por `--download-direct`) | — (usa `./downloads` ou a opção `--download-dir` quando aplicável) |
| `WATCH_FOLDER` | Ver acima (modo folder) | `./torrents` |

### Interface web e Runner

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `DOWNLOAD_RUNNER_URL` | URL do Download Runner (ex.: `http://127.0.0.1:9092`). Quando definida e acessível, a API Web faz proxy das rotas de downloads para o Runner e o CLI (`download add/list/start/stop/delete`) delega ao Runner. Veja [Interface web (Atum)](web-interface.md). | — |

### Indexadores de busca

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `X1337_BASE_URL` | URL base do 1337x (espelho). Ex.: `https://www.1337x.to` ou `https://www.1377x.to` | `https://www.1377x.to` |
| `TPB_BASE_URL` | URL base do The Pirate Bay; o domínio varia por região (ex.: `https://tpb.party`, `https://thepiratebay.org`) | `https://tpb.party` |
| `TG_BASE_URL` | URL base do TorrentGalaxy | `https://torrentgalaxy.to` |

### Last.fm (opcional)

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `LASTFM_API_KEY` | API key do Last.fm para resolver nome de álbum/artista (obtenha em [last.fm/api](https://www.last.fm/api/account)). Com ela, `dl-torrent search --album "The Wall"` pode virar "Pink Floyd - The Wall", o comando `resolve album` e `lastfm charts` funcionam | — |

### Spotify (opcional, para playlists)

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `SPOTIFY_CLIENT_ID` | Client ID do app no [Dashboard Spotify](https://developer.spotify.com/dashboard). Necessário para `spotify login`, `playlists` e `playlist`. | — |
| `SPOTIFY_CLIENT_SECRET` | Client Secret do app. | — |
| `SPOTIFY_REDIRECT_PORT` | Porta do callback OAuth em localhost (ex.: 8765). O redirect URI do app no Dashboard deve ser `http://localhost:<porta>/callback`. | `8765` |

Após `dl-torrent spotify login`, os tokens ficam em **`~/.dl-torrent/spotify_tokens.json`** (não commitar esse arquivo).

### Tipo de conteúdo (search, batch, feeds)

O tipo de conteúdo (`music`, `movies`, `tv`) é definido por comando: `search --type movies`, `batch --type tv`, `wishlist search --type tv`, `feed add "URL" --type movies`. Não há variável de ambiente para isso; o padrão é sempre `music`. Para filmes e séries, o filtro de qualidade usa resolução/codec (1080p, 720p, x265, etc.) em vez de FLAC/MP3.

### Organização e notificação (opcional)

| Variável | Descrição | Padrão |
|----------|------------|--------|
| `ORGANIZE_BY_ARTIST_ALBUM` | Com download direto, criar subpastas Artist/Album (extraído do título do torrent). Pode ser ativado também com `--organize` no comando. | `false` |
| `NOTIFY_ENABLED` | Ativar notificação ao detectar novo item no feed (poll). | `false` |
| `NOTIFY_WEBHOOK_URL` | URL para POST JSON ao detectar novo item (`{"title","message","text"}`). Requer `NOTIFY_ENABLED=true`. | — |
| `NOTIFY_DESKTOP` | Mostrar notificação na área de trabalho (Windows: instale `win10toast`; Linux: usa `notify-send`). Requer `NOTIFY_ENABLED=true`. | `false` |

## Onde ficam os dados

O dl-torrent guarda estado em:

- **`~/.dl-torrent/`** (pasta do usuário):
  - `feeds.db` — feeds inscritos, itens já processados dos feeds, histórico de buscas, wishlist e fila de downloads
  - `spotify_tokens.json` — tokens OAuth do Spotify (após `spotify login`)

Nenhuma configuração é armazenada ali; apenas dados de uso (feeds, histórico, wishlist, downloads, tokens Spotify).
