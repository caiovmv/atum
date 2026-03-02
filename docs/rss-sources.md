# Fontes de RSS para música, filmes e séries

Este documento lista onde existem feeds RSS úteis para música (e opcionalmente filmes/séries) e como usá-los com o dl-torrent. Quando o site não oferece RSS nativo, indicamos ferramentas que geram feeds a partir de buscas.

Para **filmes e séries**, use `dl-torrent feed add "URL" --type movies` ou `--type tv`. No poll, o filtro de qualidade será por resolução/codec (ex.: `--format 1080p,720p`). Muitos indexadores genéricos (Torlock, Zooqle, etc.) têm feeds mais voltados a vídeo; Jackett/Prowlarr também geram feeds de busca para filmes e séries.

---

## The Pirate Bay (TPB)

- **RSS:** Disponível por categoria e por mirror. Exemplo de feed geral: `https://tpb.party/rss` (ou caminhos por categoria Audio, dependendo do mirror).
- **Observação:** O domínio do TPB varia (tpb.party, espelhos diversos). Não há RSS "pessoal" oficial; use o feed público de novidades da categoria desejada.
- **No dl-torrent:** Adicione a URL do RSS com `dl-torrent feed add "URL"` e use `feed poll --auto-download --format flac,320` (veja [Feeds e agendamento](feeds-and-scheduling.md)).

---

## 1337x

- **RSS:** Não oferece RSS nativo.
- **Alternativas:** Usar **Jackett** ou **Prowlarr** para gerar um feed a partir de uma busca no 1337x (ex.: "FLAC", "artist name"). A URL gerada pode ser adicionada ao dl-torrent. Se não usar essas ferramentas, reste a busca manual no dl-torrent.

---

## Outros indexadores (resumo)

| Site      | RSS nativo | Relevante para música |
|-----------|------------|------------------------|
| Torlock   | Sim        | Parcial (muitos filmes/séries) |
| Zooqle    | Sim        | Parcial |
| RuTracker | Sim        | Sim (grande catálogo de áudio) |

A maioria dos indexadores genéricos é mais voltada a filmes e séries; para música, TPB (Audio), RuTracker e feeds gerados por Jackett/Prowlarr a partir de 1337x costumam ser os mais úteis.

---

## Ferramentas que geram RSS

- **Jackett:** Proxy que traduz pedidos de vários indexadores (1337x, TPB, etc.) em RSS. Você configura um indexador e uma busca (ex.: "FLAC"); o Jackett devolve uma URL de feed que pode ser colada em `dl-torrent feed add`.
- **Prowlarr:** Gerenciador de indexadores que se integra com Jackett e com apps como Sonarr/Radarr; também gera feeds de busca que podem ser usados pelo dl-torrent.
- **Feed43 / YarrrRSS:** Serviços que transformam páginas web em RSS (scraping). Úteis quando um site não tem RSS; você define a página e o padrão de extração e obtém uma URL de feed.

Para usar com dl-torrent: obtenha a URL do feed (ex.: Jackett → Indexer 1337x → RSS de busca "FLAC") e use `dl-torrent feed add <url>`; depois agende o poll com cron ou Task Scheduler (veja [Feeds e agendamento](feeds-and-scheduling.md)).

---

## Uso no dl-torrent

- **Adicionar feed:** `dl-torrent feed add "URL"` (opcional: `--type music|movies|tv` para definir o filtro de qualidade no poll).
- **Listar feeds:** `dl-torrent feed list`
- **Verificar e baixar:** `dl-torrent feed poll --auto-download --format flac,320` (música) ou `--format 1080p,720p` (feeds tipo movies/tv).
- **Filtrar por palavras:** `--include "FLAC"` e `--exclude "bootleg,mix"` no `feed poll`
- **Poll em loop:** `dl-torrent feed daemon --interval 30 --auto-download` (alternativa ao cron)

O poll pode ser agendado (cron no Linux/macOS, Agendador de Tarefas no Windows) ou feito em loop com `feed daemon`. Detalhes em [Feeds e agendamento](feeds-and-scheduling.md).
