# Rádio + Sintonias (estilo Spotify)

## Objetivo

Reprodução aleatória da biblioteca (“rádio”), com **sintonias**: presets que definem **o que pode tocar** (incluir) e **o que não pode** (excluir), permitindo várias “rádios” com estilos diferentes (ex.: “Só rock”, “Sem filme”, “Minha lista favorita”).

---

## Modelo de dados

### Tabelas (PostgreSQL)

- **radio_sintonias**
  - `id` (SERIAL), `name` (TEXT, ex.: "Rock", "Só música"), `created_at` (TIMESTAMP).

- **radio_sintonia_rules**
  - `id`, `sintonia_id` (FK), `kind` ('include' | 'exclude'), `type` ('content_type' | 'genre' | 'artist' | 'tag' | 'item'), `value` (TEXT ou JSONB).
  - Para `type = 'item'`: `value` = JSON `{"source": "download"|"import", "id": number}`.
  - Para os demais: `value` = string (ex.: "Rock", "music").

Regras:
- **Include**: se não houver nenhuma regra de include, considera **toda** a biblioteca reproduzível. Caso contrário, o item entra só se bater com **alguma** regra de include (por tipo, gênero, artista, tag ou item explícito).
- **Exclude**: remove itens que batem com **qualquer** regra de exclude.
- Ordem: primeiro aplica include, depois exclude.

---

## Backend (API)

- **GET /api/radio/sintonias** — lista sintonias (id, name, created_at).
- **POST /api/radio/sintonias** — cria sintonia: body `{ name, include?: { content_types?: [], genres?: [], artists?: [], tags?: [], items?: [{ source, id }] }, exclude?: { ... } }`.
- **PATCH /api/radio/sintonias/:id** — atualiza nome e/ou regras.
- **DELETE /api/radio/sintonias/:id** — remove sintonia.
- **POST /api/radio/sintonias/:id/queue?limit=50** — retorna uma **fila embaralhada** de itens da biblioteca que respeitam a sintonia. Resposta: `{ items: [ { id, source, name, content_type, ... } ] }` (mesmo formato dos itens de library). O frontend usa essa fila para tocar em sequência; quando acabar, pode pedir mais (mesmo endpoint ou `?offset=50`).

Lógica de **queue** (em código):
1. Buscar itens da biblioteca (reuso da lógica de `list_library` ou chamada interna).
2. Filtrar por **include**: se há regras include, manter só os que casam (content_type, genre, artist, tag ou item na lista).
3. Filtrar por **exclude**: remover os que casam com exclude.
4. Embaralhar (random) e fatiar `limit` itens; retornar.

---

## Frontend

- **Nova rota** `/radio` e entrada na sidebar (“Rádio”).
- **Página Rádio**:
  - Lista de **sintonias** (cards ou lista): nome, botão “Tocar” (inicia a rádio com essa sintonia), opção “Editar” / “Excluir”.
  - Botão “Nova sintonia” abre formulário/modal.
- **Formulário de sintonia** (criar/editar):
  - Nome.
  - **Incluir**: opcional; escolher tipo de conteúdo (Música / Filmes / Séries), gêneros, artistas, tags (sugestões vindas de `/api/library/facets`) e/ou escolher itens específicos da biblioteca (lista com checkboxes ou multi-select).
  - **Excluir**: mesma ideia (gêneros, artistas, tags, itens).
  - Salvar chama POST ou PATCH.
- **Reprodução**:
  - Ao clicar “Tocar” numa sintonia: POST `/api/radio/sintonias/:id/queue?limit=50` → recebe fila; redirecionar para o Player com o **primeiro** item e passar a fila (ex.: state ou contexto) para que “Próximo” avance na fila (e, se necessário, pedir mais itens ao backend quando a fila estiver acabando).

Persistência da fila no frontend: usar React state/context (ex.: `RadioQueueContext`) com lista de itens e índice atual; Player lê desse contexto quando estiver em “modo rádio”.

---

## Fluxo resumido

1. Usuário cria sintonias (ex.: “Rock”, “Só música”, “Sem filmes”).
2. Em “Rádio”, escolhe uma sintonia e clica “Tocar”.
3. Backend devolve fila embaralhada; o player toca em sequência.
4. Botão “Próximo” na player avança na fila (e pode pedir mais itens ao backend quando restar poucos).

---

## Arquivos a criar/alterar

| Área | Arquivo | Ação |
|------|--------|------|
| Schema | `scripts/schema_postgres.sql` | CREATE TABLE radio_sintonias + radio_sintonia_rules |
| Backend | `src/app/repositories/radio_repository.py` (ou _postgres) | CRUD sintonias + regras |
| Backend | `src/app/web/routers/radio.py` | Rotas GET/POST/PATCH/DELETE sintonias + POST queue |
| Backend | `src/app/web/app.py` + `routers/__init__.py` | Registrar router de radio |
| Frontend | `src/app/contexts/RadioQueueContext.tsx` (opcional) | Estado da fila rádio |
| Frontend | `frontend/src/pages/Radio.tsx` + `Radio.css` | Página lista + form sintonias |
| Frontend | `frontend/src/App.tsx` | Rota `/radio` |
| Frontend | `frontend/src/components/Layout.tsx` | Link “Rádio” na sidebar |
| Frontend | `frontend/src/pages/Player.tsx` | Integrar “Próximo” com fila rádio (e pedir mais ao backend se precisar) |

---

## Ordem de implementação sugerida

1. Schema + repositório (radio_sintonias, radio_sintonia_rules, CRUD).
2. API: CRUD sintonias + endpoint `queue`.
3. Frontend: página Rádio (lista + criar/editar sintonia), chamada ao queue e início da reprodução.
4. Player: usar fila rádio para “Próximo” e, se quiser, carregar mais itens ao chegar perto do fim da fila.
