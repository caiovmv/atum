# Changelog

## [0.2.0] — Cache, eviction, sync e melhorias UX (Busca e Downloads)

### Backend

- **Cache apenas Redis:** Removido cache in-memory para capas; sem `REDIS_URL` usa no-op (não cacheia). Prefixos `dl-torrent:cover:` e `dl-torrent:search:`.
- **Eviction:** API de eviction por `download_id`; chamada em `delete` e no sync. TTL 7 dias para capas de download (failsafe); TTL 1 dia para pesquisa.
- **Sync inteligente:** `reconcile_downloads_with_filesystem` evict capa no Redis e apaga arquivos quando conteúdo ou arquivo de capa não existe; limpa `cover_path_*` no DB quando arquivo de capa sumiu.
- **Cache de pesquisa:** TMDB detail e sugestões de filtro com cache Redis (TTL máx. 1 dia).
- **Repositório:** `set_cover_paths(..., None, None)` passa a limpar as colunas no SQLite e no Postgres.

### Frontend — Busca (Search)

- Estado: `useMemo` para filtros, `useCallback` + `AbortController` na busca.
- Navegação: `navigate('/downloads')` em vez de `window.location.href`.
- Feedback: toast em vez de `alert()`; estado vazio “Nenhum resultado para …”.
- A11y: `role="search"`, `aria-describedby`, `aria-live`, `aria-label` no botão Adicionar.
- UX: “Limpar filtros” vs “Nova busca”; paginação com primeira/última página.

### Frontend — Downloads

- Polling só quando aba visível (Page Visibility API); `useCallback` para `fetchDownloads`.
- Feedback em start/stop/remove (toast); modal para confirmar remoção em vez de `confirm()`.
- Status em português (Enfileirado, Baixando, etc.); contagem por status no filtro; “Atualizado há X s”.
- A11y: `scope="col"`, caption na tabela, `aria-label` no filtro.
- Mobile: layout em cards em vez de tabela; barra de progresso visual.

### Testes

- 216 testes passando (unit, integration, e2e).

---

## [0.1.0] — Versão inicial

- CLI de busca e download de torrents (música, filmes, séries).
- API web (FastAPI), runner, frontend (React/Vite).
- Docker: frontend (nginx), API, runner, PostgreSQL 18, Redis.
