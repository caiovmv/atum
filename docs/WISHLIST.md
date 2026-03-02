# Wishlist de features

Itens **já implementados** (para referência) e ideias para evolução futura.

---

## Implementado (referência)

- **Lista → dl-torrent (batch):** Comando `dl-torrent batch arquivo.txt` (ou `--stdin`) para processar uma linha por busca e baixar o melhor resultado. Ver [Comandos](docs/commands.md#batch) e [arquitetura](docs/arquitetura-netflix-self-hosted.md).
- **Pasta por artista/álbum:** Opção `--organize` (ou `ORGANIZE_BY_ARTIST_ALBUM=true`) no download direto; cria subpastas Artist/Album a partir do título.
- **Filtro por palavras-chave em feeds:** `--include` e `--exclude` no `feed poll` (e no `feed daemon`).
- **Feed daemon:** Comando `feed daemon --interval N` para poll em loop (alternativa ao cron).
- **Notificação ao novo item:** Webhook (POST JSON) e/ou notificação desktop (Windows: win10toast; Linux: notify-send) via `NOTIFY_ENABLED`, `NOTIFY_WEBHOOK_URL`, `NOTIFY_DESKTOP` no `.env`.

---

## Busca e descoberta (futuro)

- **Múltiplos indexadores:** RARBG, TorrentGalaxy e outros além de 1337x e TPB (TorrentGalaxy já suportado).
- **Busca por artista/álbum (Last.fm/Spotify):** Dado um nome, resolver "Artist - Album" ou lista de faixas para montar a query automaticamente.
- **Histórico de buscas:** Guardar últimas N buscas (SQLite ou JSON) e comando para repetir ou ajustar.
- **Favoritos / lista de desejos:** Salvar "artist - album" ou termos para depois rodar busca em lote (ou --dry-run para só listar).

---

## Qualidade e organização (futuro)

- **Verificação pós-download:** Opcionalmente rodar verificação de checksum (ex.: FLAC) ou listar arquivos baixados; comando para verificar pasta.
- **Subfiltro por tamanho:** --min-size e --max-size para descartar resultados fora do intervalo.

---

## Feeds (futuro)

- Melhorias adicionais em feeds (os filtros --include/--exclude, daemon e notificação já estão implementados; ver [Comandos](docs/commands.md#feed-add--list--poll--daemon)).

---

## Download e fila

- **Limite de concorrência:** No modo background, limitar quantos torrents baixam ao mesmo tempo (ex.: 2).
- **Prioridade na fila:** Comando para mover item para o topo ou definir prioridade.
- **Retry automático:** Para status failed, retentar N vezes com backoff antes de marcar como falha definitiva.
- **Progresso real na tabela:** Persistir e exibir % de progresso na listagem de downloads quando o backend expuser essa informação.

---

## Experiência e CLI

- **Saída JSON:** --json em search e download list para integrar com scripts.
- **Modo interativo contínuo:** Após uma busca, poder digitar "b" para nova busca, "l" para listar downloads, "q" para sair, em loop.
- **Tema / cores:** Opção no config ou --no-color para desabilitar cores.

---

## Configuração e manutenção

- **Profiles de config:** Vários "profiles" (ex.: default, work, lossless) com diferentes DOWNLOAD_DIR, CLIENT_TYPE, etc., e --profile.
- **Backup/restore do DB:** Exportar/importar ~/.dl-torrent/ (feeds + downloads) para mudar de máquina ou restaurar.
- **Health check:** Comando (ex.: `dl-torrent check`) que testa conexão com Transmission/uTorrent, 1337x e TPB acessíveis, libtorrent carregando, pastas existem.
