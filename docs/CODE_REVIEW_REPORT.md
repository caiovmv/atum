# Code Review Report — dl-torrent

**Escopo:** Princípios SOLID, Clean Architecture, KISS, Design by Performance e Design Patterns.  
**Resultado:** Relatório **antes** (compliance + problemas) e **depois** (melhorias aplicadas + motivos).

---

## 1. Estado ANTES (compliance e problemas)

### 1.1 SOLID

| Princípio | Compliance antes | Problemas |
|-----------|------------------|-----------|
| **S — Single Responsibility** | Parcial | `main.py` com ~950 linhas: orquestra CLI, batch (_run_batch_lines), version, search, download, history, lastfm, spotify, wishlist, feed. Uma única “classe” (módulo) com muitas razões para mudar. `search.py` repetia o mesmo bloco (use_video, allowed) em três funções (1337x, TPB, TG). |
| **O — Open/Closed** | Parcial | Novos indexadores ou novos destinos exigem alterar `search_all` e `resolve_destination` (if/elif). Extensível via registro/factory em parte (client, destinations), mas não em toda a busca. |
| **L — Liskov Substitution** | Ok | Implementações de `MagnetDestination` e `TorrentClient` são substituíveis; não há quebra de contrato observada. |
| **I — Interface Segregation** | Parcial | `MagnetDestination` exige `run_after_if_sync` para todos; só `DirectDownloadDestination` usa. Demais implementações fazem no-op. Clientes de torrent têm interface enxuta (`add`). |
| **D — Dependency Inversion** | Fraco | `download_manager`, `search`, `feeds` importam `db` e `config` concretos. Não há abstrações (protocols/interfaces) para persistência ou configuração; testes dependem de mock de módulo (`patch("app.db.download_add")`). |

### 1.2 Clean Architecture

| Aspecto | Antes | Problemas |
|---------|--------|-----------|
| **Camadas** | Implícitas | Não há pastas domain/application/infrastructure. Domínio (quality, organize, domain/) existe mas é usado diretamente por search/feeds; não há camada de “use cases” isolada. |
| **Regra de dependência** | Violada | A “orquestração” (search, feeds, download_manager) importa infra (db, config, client). O núcleo não é independente de frameworks e de detalhes de I/O. |
| **Entidades** | Parciais | `DownloadStatus`, `SearchResult`, `QualityInfo` são entidades/valores; regras de qualidade e organização estão em módulos próprios (quality, organize) mas acoplados a typer em search/feeds. |
| **Casos de uso** | Misturados | `run_search`, `poll_feeds`, `run_pending_selection` são casos de uso mas vivem em módulos que também fazem I/O (typer.echo, feedparser, requests). |

### 1.3 KISS (Keep It Simple, Stupid)

| Aspecto | Antes | Problemas |
|---------|--------|-----------|
| **Duplicação** | Presente | O mesmo cálculo `use_video` e `allowed` (parse_format_filter vs parse_format_filter_video) repetido em `search_1337x`, `search_tpb` e `search_tg`. |
| **Complexidade local** | Aceitável | Lógica de cada função é compreensível; o problema é concentração em main.py e repetição em search. |

### 1.4 Design by Performance

| Aspecto | Antes | Observações |
|---------|--------|-------------|
| **DB** | Ok | SQLite com WAL e busy_timeout; uma conexão por operação (get_connection); context manager para poll. Nenhum pool explícito (SQLite tipicamente um writer). |
| **Concorrência** | Ok | Workers de download em threads; retry com backoff em restart_dead_workers para database locked. |
| **Rede** | Razoável | Busca paralela por indexador não implementada (search_all em sequência); poderia ser futura melhoria. |

### 1.5 Design Patterns

| Padrão | Uso antes | Observação |
|--------|-----------|------------|
| **Strategy** | Sim | `MagnetDestination` e implementações (WatchFolder, Client, BackgroundQueue, DirectDownload); `resolve_destination()` seleciona a estratégia. |
| **Factory** | Sim | `client/factory.py`: registry por client_type; `create_client_from_settings`. |
| **Repository** | Sim | `repositories/` encapsulam SQLite; re-export em `db.py`. |
| **Template Method** | Implícito | Fluxo de busca (obter resultados → filtrar qualidade → ordenar) repetido nos três indexadores com pequenas variações. |
| **Adapter** | Parcial | Clientes (Transmission, uTorrent, folder) adaptam APIs externas para `TorrentClient`. |

---

## 2. Melhorias EXECUTADAS e motivos

### 2.1 KISS / DRY — Helper de qualidade em `search.py`

**O que foi feito:**  
Criada a função `_quality_filter_for_content_type(content_type, format_filter, no_quality_filter)` que retorna `(use_video, allowed)`. As três funções `search_1337x`, `search_tpb` e `search_tg` passaram a usar esse helper em vez de repetir o mesmo bloco.

**Motivo:**  
- Reduz duplicação (DRY) e simplifica manutenção (KISS).  
- Uma única alteração na regra de “qualidade por tipo” (vídeo vs áudio) reflete nos três indexadores.  
- Menos chance de divergência entre 1337x, TPB e TG.

**Arquivo:** `src/app/search.py`

---

### 2.2 SRP — Módulo `batch.py`

**O que foi feito:**  
- Criado o módulo `src/app/batch.py` com responsabilidade única: **fluxo de batch** (ler linhas, chamar busca para cada uma).  
- `run_batch_lines(lines, **opts)` — lógica de “para cada linha, run_search com opções”.  
- `run_batch_cmd(file_path, stdin, ...)` — leitura de arquivo/stdin + validação + chamada a `run_batch_lines`.  
- `main.py` removeu a implementação de `_run_batch_lines` e do corpo do comando `batch`; passou a importar e chamar `run_batch_cmd` e `run_batch_lines` de `batch.py`.  
- Last.fm e Spotify `--batch` passaram a usar `batch.run_batch_lines`.

**Motivo:**  
- **Single Responsibility:** `main.py` deixa de ser dono da lógica de batch; apenas registra o comando e repassa parâmetros.  
- Redução de tamanho e responsabilidades em `main.py`.  
- Batch pode evoluir (retry, relatório, etc.) em um único módulo, sem poluir a CLI.

**Arquivos:** `src/app/batch.py` (novo), `src/app/main.py` (refatorado).

---

## 3. Estado DEPOIS (compliance)

### 3.1 SOLID — Depois

| Princípio | Compliance depois | Comentário |
|-----------|--------------------|------------|
| **S** | Melhorado | Responsabilidade de “batch” movida para `batch.py`; responsabilidade de “filtro de qualidade por tipo” centralizada em um helper em `search.py`. `main.py` continua grande mas com uma responsabilidade a menos. |
| **O** | Inalterado | Sem mudança estrutural para extensão (indexadores/destinos). |
| **L** | Ok | Sem alteração. |
| **I** | Inalterado | Interface `MagnetDestination` segue com `run_after_if_sync` para todos. |
| **D** | Melhorado | Persistência: `DownloadRepository` com Sqlite e Postgres; `get_repo()` escolhe por `DATABASE_URL`. Cache: `CoverCache` com in-memory e Redis; `get_cover_cache()` por `REDIS_URL`. |

### 3.2 Clean Architecture — Depois

| Aspecto | Depois | Comentário |
|---------|--------|------------|
| **Camadas** | Implícitas | Sem nova camada física; caso de uso “batch” está isolado em módulo próprio, o que é um passo em direção a separar orquestração. |
| **Regra de dependência** | Melhor | Repositório e cache via abstrações; implementação escolhida por config. |
| **Casos de uso** | Melhor | “Executar batch de buscas” está explícito em `batch.py`, sem estar misturado à CLI. |

### 3.3 KISS — Depois

| Aspecto | Depois | Comentário |
|---------|--------|------------|
| **Duplicação** | Reduzida | Cálculo de qualidade por content_type em um único lugar em `search.py`. |
| **Complexidade** | Reduzida | Menos linhas repetidas; leitura das funções de busca mais direta. |

### 3.4 Design by Performance — Depois

DB: SQLite ou PostgreSQL por `DATABASE_URL`. Cache de capas (in-memory ou Redis) com TTL. Rede: inalterado.

### 3.5 Design Patterns — Depois

Repository com Sqlite e Postgres; Protocol `CoverCache` (in-memory vs Redis). Strategy/Factory preservados.

### 3.6 Open/Closed — Strategy e Factory (documentação)

**Strategy (destinos de magnet):**  
- Interface: `MagnetDestination` (em `domain/` ou client) com `run_after_if_sync`, etc.  
- Implementações: WatchFolder, Client (Transmission/uTorrent), BackgroundQueue, DirectDownload.  
- Ponto de seleção: `resolve_destination()` (ou equivalente) escolhe a estratégia conforme `client_type` e opções.  
- **Extensão:** para novo destino, criar nova classe que implementa a interface e registrá-la no ponto de seleção (evitar if/elif longo).

**Factory (clientes de torrent):**  
- Módulo: `client/factory.py` — `create_client_from_settings(settings)` retorna o cliente (Transmission, uTorrent, folder).  
- Registry por `client_type` (transmission, utorrent, folder).  
- **Extensão:** adicionar novo tipo em `Settings` e novo caso no factory; o restante do código depende da interface `TorrentClient` (ex.: `add`).

**Repository (persistência):**  
- Porta: `DownloadRepository`; implementações Sqlite e Postgres escolhidas por `DATABASE_URL`.  
- Feed, wishlist e search_history seguem o mesmo padrão (funções que delegam a implementação SQLite ou Postgres conforme config).

### 3.7 Abstrações e ponto único de composição

| Abstração | Implementações | Onde obter |
|-----------|----------------|------------|
| `DownloadRepository` | SqliteDownloadRepository, PostgresDownloadRepository | `deps.get_repo()` |
| `CoverCache` | InMemoryCoverCache, RedisCoverCache | `deps.get_cover_cache()` |
| Configuração | Settings (env/.env) + override para testes | `deps.get_settings()` ou `config.get_settings()` |
| Feed / wishlist / search_history | SQLite ou Postgres (por `DATABASE_URL`) | `feed_repository.*`, `wishlist_repository.*`, `search_history_repository.*` |

**Ponto único de composição:** `app.deps` expõe `get_settings()`, `get_repo()`, `get_cover_cache()` e `set_overrides(...)` para testes. A aplicação (API, runner, cover_service, download_manager) usa `deps`; repositórios de baixo nível continuam usando `config.get_settings()` para evitar import circular.

---

## 4. Resumo

- **Antes:** Violações em SRP (main.py e search.py), DIP (dependências concretas), regra de dependência da Clean Architecture; duplicação em search; boa aderência a LSP e uso de Strategy/Factory/Repository.  
- **Melhorias feitas:** (1) Helper de qualidade (KISS/DRY); (2) Módulo batch (SRP); (3) DownloadRepository + feed/wishlist/search_history com SQLite e PostgreSQL; (4) CoverCache in-memory/Redis; (5) API routers; (6) Docker (frontend, API, Runner, Postgres 18, Redis); (7) Configuração injetável (`SettingsProvider`, `set_settings_override`); (8) Ponto único de composição (`deps`: get_settings, get_repo, get_cover_cache, set_overrides); (9) Documentação Strategy/Factory (Open/Closed).  
- **Depois:** SRP, DIP e KISS melhorados; padrões Repository, Protocol e ponto único de composição aplicados.

Recomendações futuras: segregar interface de destino sync/async; camada de use cases explícita; busca paralela por indexador.
