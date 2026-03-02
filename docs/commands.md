# Referência de comandos

Todos os comandos são executados como `dl-torrent <subcomando> [opções]`.

## Qualidade dos resultados

- **Música (padrão):** Só aparecem resultados com qualidade aceitável: FLAC, ALAC, MP3 320 ou MP3 até 198 kbps. O **`--format`** restringe a um subconjunto (ex.: `flac`, `alac`, `320`, `mp3_320`, `mp3`).
- **Filmes e séries (`--type movies` ou `--type tv`):** A qualidade é avaliada por resolução (720p, 1080p, 2160p/4K), codec (x264, x265) e fonte (BluRay, WEB-DL, HDTV). O **`--format`** aceita aliases como `1080p`, `720p`, `4k`, `x265`, `webdl`, `bluray`.

---

## search

Busca torrents por nome (música, filme ou série). Lista resultados para você escolher (setas + Espaço para marcar, Enter para confirmar) e envia os selecionados para o cliente configurado (ou para pasta / download direto, conforme as opções).

**Uso:** `dl-torrent search [QUERY] [OPÇÕES]`

| Opção | Descrição |
|-------|------------|
| `QUERY` | Termo de busca (nome da música/artista, filme ou série). Pode ser omitido se usar `--from-history N`. |
| `--type`, `-t` | Tipo de conteúdo: `music` (padrão), `movies`, `tv`. Define categoria no indexador e filtro de qualidade (áudio vs vídeo). |
| `--album`, `-a` | Nome do álbum (concatena à query; útil para música). |
| `--best`, `-b` | Baixar o melhor resultado automaticamente (alias de `--auto-download-best-result`). |
| `--auto-download-best-result` | Baixar apenas o melhor resultado, sem abrir a lista. |
| `--index`, `-i` | Número do resultado para baixar (1-based). Ex.: `--index 2` baixa o segundo. |
| `--limit`, `-n` | Máximo de resultados exibidos (padrão: 15). |
| `--format`, `-f` | Subfiltro: música (ex.: `flac,alac,320`) ou vídeo (ex.: `1080p,720p,4k,x265,webdl`) conforme `--type`. |
| `--no-quality-filter` | Mostrar todos os resultados, sem filtrar por qualidade. |
| `--verbose`, `-V` | Mostrar detalhes da busca (erros, quantidade por indexador). |
| `--all-categories` | Buscar em todas as categorias do 1337x (não só Music). |
| `--save-to-watch-folder` | Salvar magnets na pasta (WATCH_FOLDER ou `--watch-folder`), sem usar Transmission/uTorrent. |
| `--watch-folder` | Pasta onde salvar os magnets (com `--save-to-watch-folder`). |
| `--download-direct` | Baixar os arquivos diretamente com libtorrent (TorrentP), sem cliente externo. |
| `--download-dir` | Pasta de destino do download direto (com `--download-direct`). |
| `--listen-port` | Porta para download direto (use se houver conflito com outro processo). |
| `--background` | Com `--download-direct`: enfileirar na fila e baixar em background (use `download list` para acompanhar). |
| `--indexer` | Indexadores separados por vírgula: `1337x`, `tpb`, `tg` (padrão: `1337x,tpb`). |
| `--from-history` | Repetir a busca do histórico com o id indicado (veja `history list`). |
| `--organize` | Com download direto: criar subpastas conforme o tipo (Artist/Album, Movie (Year), Show/Season). |

**Exemplos:**

```bash
# Buscar e escolher na lista
dl-torrent search "Pink Floyd Wish You Were Here"

# Baixar só o melhor resultado
dl-torrent search "Artist Album" --best

# Com álbum
dl-torrent search "Wish You Were Here" --album "Pink Floyd"

# Baixar o resultado número 2
dl-torrent search "Artist Album" --index 2

# Salvar magnets em pasta (FrostWire / pasta monitorada)
dl-torrent search "Artist Album" --save-to-watch-folder --watch-folder ./downloads

# Download direto para uma pasta (com subpastas Artist/Album)
dl-torrent search "Artist Album" --download-direct --download-dir ./musica --organize

# Só FLAC e ALAC
dl-torrent search "Artist Album" -f flac,alac

# Filmes: 1080p ou melhor
dl-torrent search "Movie Name" --type movies -f 1080p,4k --download-direct --organize

# Séries: 720p ou 1080p
dl-torrent search "Show Name S01" --type tv -f 720p,1080p

# Usar só TPB
dl-torrent search "Artist Album" --indexer tpb

# Repetir busca do histórico (id 5)
dl-torrent search --from-history 5
```

---

## history list

Lista as últimas buscas (cada `search` é salvo automaticamente).

| Opção | Descrição |
|-------|------------|
| `--limit`, `-n` | Máximo de entradas (padrão: 50). |

**Exemplo:** `dl-torrent history list --limit 20`

Para repetir uma busca: `dl-torrent search --from-history <id>`.

---

## batch

Para cada linha de um arquivo (ou do stdin), executa uma busca e baixa o **melhor resultado** na melhor qualidade. Útil para listas de música (Spotify, Last.fm) ou listas de filmes/séries.

**Uso:** `dl-torrent batch [ARQUIVO] [OPÇÕES]` ou `dl-torrent batch --stdin [OPÇÕES]`

| Opção | Descrição |
|-------|------------|
| `ARQUIVO` | Caminho do arquivo com uma linha por busca (Artist - Album, nome de filme ou série). |
| `--stdin` | Ler linhas do stdin em vez de arquivo. |
| `--type`, `-t` | Tipo de conteúdo: `music` (padrão), `movies`, `tv`. |
| `--format`, `-f` | Subfiltro de formato: música (ex.: `flac,alac,320`) ou vídeo (ex.: `1080p,720p`). |
| `--download-direct` | Baixar diretamente com libtorrent (sem cliente externo). |
| `--download-dir` | Pasta de destino (com --download-direct). |
| `--background` | Enfileirar e baixar em background (com --download-direct). |
| `--indexer` | Indexadores separados por vírgula (1337x, tpb, tg). |
| `--limit`, `-n` | Máximo de resultados por busca (padrão: 5; usa o melhor). |
| `--organize` | Criar subpastas conforme o tipo (Artist/Album, Movie (Year), Show/Season). |

**Exemplos:**

```bash
dl-torrent batch lista.txt --download-direct --download-dir ./musica
echo "Artist - Album" | dl-torrent batch --stdin --download-direct --organize
```

---

## wishlist add / list / remove / search

Lista de desejos: termos (ex.: "Artist - Album", nome de filme ou série) que você pode buscar em lote depois.

- **add** — Adiciona um termo. Ex.: `dl-torrent wishlist add "Pink Floyd - The Wall"`
- **list** — Lista todos os termos (com id).
- **remove** — Remove por id. Ex.: `dl-torrent wishlist remove 2`
- **search** — Executa uma busca para cada termo da wishlist. Com `--dry-run` só lista as buscas que seriam feitas, sem executar.

| Opção (em search) | Descrição |
|-------------------|------------|
| `--dry-run` | Só listar as buscas, não executar. |
| `--limit`, `-n` | Máximo de resultados por busca (padrão: 15). |
| `--type`, `-t` | Tipo de conteúdo: `music` (padrão), `movies`, `tv`. |

---

## resolve album

Lista sugestões "Artist - Album" para um nome de álbum usando o Last.fm. **Requer `LASTFM_API_KEY`** no `.env`.

**Uso:** `dl-torrent resolve album "NOME_DO_ÁLBUM" [--limit N]`

| Opção | Descrição |
|-------|------------|
| `--limit`, `-n` | Máximo de sugestões (padrão: 5). |

**Exemplo:** `dl-torrent resolve album "The Wall"`

---

## lastfm charts

Lista os **top tracks** do Last.fm no formato `Artist - Track` (uma linha por faixa). **Requer `LASTFM_API_KEY`** no `.env`. A saída pode ser usada com `batch` (pipe ou opção `--batch`).

**Uso:** `dl-torrent lastfm charts [--limit N] [--batch] [opções de batch]`

| Opção | Descrição |
|-------|------------|
| `--limit`, `-n` | Máximo de faixas (até 50; padrão: 50). |
| `--batch` | Em vez de só listar, rodar batch: buscar e baixar o melhor resultado por linha. |
| `--format`, `-f` | Subfiltro de formato (com `--batch`). |
| `--download-direct` | Baixar com libtorrent (com `--batch`). |
| `--download-dir` | Pasta de destino (com `--batch`). |
| `--background` | Enfileirar em background (com `--batch`). |
| `--indexer` | Indexadores para `--batch` (1337x, tpb, tg). |
| `--batch-limit` | Máximo de resultados por busca quando `--batch` (usa o melhor; padrão: 5). |
| `--organize` | Subpastas Artist/Album (com `--batch`). |

**Exemplos:**

```bash
# Só listar (pipe para batch)
dl-torrent lastfm charts --limit 20 | dl-torrent batch --stdin --download-direct --organize

# Listar e rodar batch no mesmo comando
dl-torrent lastfm charts --limit 10 --batch --download-direct --download-dir ./musica
```

---

## spotify login / playlists / playlist

Integração com Spotify (OAuth) para obter listas de faixas das suas playlists (incl. Discover Weekly, Release Radar). **Requer app no [Dashboard Spotify](https://developer.spotify.com/dashboard)** e variáveis `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET` no `.env`. O redirect URI do app deve ser `http://localhost:8765/callback` (ou a porta em `SPOTIFY_REDIRECT_PORT`).

- **login** — Abre o navegador para autorizar; salva os tokens em `~/.dl-torrent/spotify_tokens.json`. Rode uma vez (ou quando expirar a sessão).
- **playlists** — Lista as playlists do usuário (id e nome) para usar em `spotify playlist <id>`.
- **playlist** — Lista as faixas da playlist no formato `Artist - Track` (ou `--batch` para buscar e baixar).

**Uso:**

- `dl-torrent spotify login`
- `dl-torrent spotify playlists [--limit N]`
- `dl-torrent spotify playlist <ID ou URL> [--batch] [opções de batch]`

| Opção (playlist) | Descrição |
|------------------|------------|
| `--batch` | Rodar batch com as faixas (buscar e baixar o melhor resultado por linha). |
| `--format`, `-f` | Subfiltro de formato (com `--batch`). |
| `--download-direct` | Baixar com libtorrent (com `--batch`). |
| `--download-dir` | Pasta de destino (com `--batch`). |
| `--background` | Enfileirar em background (com `--batch`). |
| `--indexer` | Indexadores para `--batch`. |
| `--batch-limit` | Máximo de resultados por busca quando `--batch`. |
| `--organize` | Subpastas Artist/Album (com `--batch`). |

**Exemplos:**

```bash
# Primeira vez: autorizar no navegador
dl-torrent spotify login

# Listar playlists e depois listar faixas de uma (por ID ou URL)
dl-torrent spotify playlists
dl-torrent spotify playlist 3cEYpjA9oz9GiPac4AsH4n
dl-torrent spotify playlist "https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n"

# Pipe para batch ou --batch
dl-torrent spotify playlist 3cEYpjA9oz9GiPac4AsH4n | dl-torrent batch --stdin --download-direct
dl-torrent spotify playlist 3cEYpjA9oz9GiPac4AsH4n --batch --download-direct --organize
```

---

## feed add / list / poll / daemon

Gerencia feeds RSS de torrents (música, filmes ou séries).

- **add** — Inscreve em um feed. Ex.: `dl-torrent feed add "https://exemplo.com/torrents.xml"` (opcional: `--type music|movies|tv`).
- **list** — Lista feeds inscritos (mostra o tipo de cada um).
- **poll** — Verifica os feeds e lista (ou baixa) novidades. Para feeds do tipo movies/tv, o filtro de qualidade usa resolução/codec (ex.: `--format 1080p,720p`).
- **daemon** — Fica em loop fazendo poll a cada N minutos (Ctrl+C para sair).

| Opção (em add) | Descrição |
|----------------|------------|
| `--type`, `-t` | Tipo do feed: `music` (padrão), `movies`, `tv`. Define qual filtro de qualidade usar no poll. |

| Opção (em poll e daemon) | Descrição |
|--------------------------|------------|
| `--auto-download` | Baixar automaticamente os itens com qualidade aceitável. |
| `--format`, `-f` | Subfiltro: música (ex.: `flac,320`) ou vídeo (ex.: `1080p,720p`) conforme o tipo do feed. |
| `--include` | Só itens cujo título contém alguma das palavras (separadas por vírgula). |
| `--exclude` | Descartar itens cujo título contém alguma das palavras (separadas por vírgula). |
| `--organize` | Criar subpastas por tipo (Artist/Album, Movie, Show/Season) ao baixar (poll/daemon). |

| Opção (em pending) | Descrição |
|---------------------|------------|
| `--organize` | Ao escolher itens para baixar, criar subpastas por tipo conforme o feed (music/movies/tv). |
| `--interval`, `-i` | Intervalo do watch em segundos após escolher itens (padrão: 5). |

| Opção (só em daemon) | Descrição |
|----------------------|------------|
| `--interval`, `-i` | Intervalo em minutos entre cada poll (padrão: 30). |

**Exemplos:**

```bash
dl-torrent feed add "https://exemplo.com/music.xml"
dl-torrent feed add "https://exemplo.com/movies.xml" --type movies
dl-torrent feed poll
dl-torrent feed poll --auto-download --format flac,320 --include "FLAC"
dl-torrent feed poll --format 1080p,720p   # para feeds tipo movies/tv
dl-torrent feed poll --exclude "soundtrack,mix"
dl-torrent feed daemon --interval 30 --auto-download
```

---

## runner

Inicia o **Download Runner**: processo HTTP (FastAPI) que expõe a fila de downloads. Usado pela API Web e pelo CLI em modo remoto quando `DOWNLOAD_RUNNER_URL` está definida.

**Uso:** `dl-torrent runner [OPÇÕES]`

| Opção | Descrição |
|-------|------------|
| `--port`, `-p` | Porta (padrão: 9092). |
| `--host`, `-h` | Host (padrão: 127.0.0.1). |

**Exemplo:** `dl-torrent runner` — depois defina `DOWNLOAD_RUNNER_URL=http://127.0.0.1:9092` para a API e o CLI.

Veja [Interface web (Atum)](web-interface.md) para subir Runner + API + console no navegador.

---

## serve

Inicia a **API Web** (busca + proxy para o Runner) e serve a console **Atum** (frontend React) em `/`. Requer `DOWNLOAD_RUNNER_URL` para as rotas de downloads.

**Uso:** `dl-torrent serve [OPÇÕES]`

| Opção | Descrição |
|-------|------------|
| `--port`, `-p` | Porta (padrão: 8000). |
| `--host`, `-h` | Host (padrão: 0.0.0.0). |

**Exemplo:** Com o Runner rodando, `set DOWNLOAD_RUNNER_URL=http://127.0.0.1:9092` e `dl-torrent serve`; abra http://localhost:8000.

---

## download add / list / start / stop / delete

Gerencia a fila de downloads em background (usada quando você usa `--download-direct --background` ou adiciona um magnet manualmente). Se `DOWNLOAD_RUNNER_URL` estiver definida e o Runner estiver acessível, os comandos delegam ao Runner (modo remoto).

- **add** — Adiciona um magnet (ou caminho para .torrent) à fila. Ex.: `dl-torrent download add "magnet:?xt=..." --download-dir ./musica`
- **list** — Lista downloads (status, tipo, progresso, se/le). Use `--watch` para atualizar a cada 2 segundos. A coluna **Tipo** mostra music/movies/tv quando o download foi adicionado com tipo (busca, batch, feed).
- **start** — Inicia ou retoma um download por id.
- **stop** — Para um download em andamento.
- **delete** — Remove da lista (e opcionalmente apaga arquivos com `--remove-files`).

| Opção (add) | Descrição |
|-------------|------------|
| `--download-dir`, `-d` | Pasta de destino (padrão: DOWNLOAD_DIR do .env ou ./downloads). |
| `--name`, `-n` | Nome amigável para exibir na lista. |
| `--start` / `--no-start` | Iniciar o download em background logo após adicionar (padrão: sim). |

| Opção (list) | Descrição |
|--------------|------------|
| `--status`, `-s` | Filtrar por status: `queued`, `downloading`, `paused`, `completed`, `failed`. |
| `--watch`, `-w` | Atualizar a lista a cada 2 segundos (Ctrl+C para sair). |

| Opção (delete) | Descrição |
|----------------|------------|
| `--remove-files` | Apagar também os arquivos baixados (pasta do torrent). |

**Exemplos:**

```bash
dl-torrent download list
dl-torrent download list --watch
dl-torrent download start 3
dl-torrent download stop 3
dl-torrent download delete 3 --remove-files
```
