# Padrões do Frontend Atum

> Documento de regras para o agente de IA ao desenvolver no frontend. Manter consistência de produto (UX/UI), padrões técnicos (SOLID, KISS, Clean Architecture) e convenções obrigatórias.

---

## 1. Visão Geral

- **Propósito:** Regras obrigatórias para desenvolvimento no frontend
- **Escopo:** Componentes, páginas, hooks, contexts, estilos
- **Stack:** React 19, TypeScript, Vite, PWA (vite-plugin-pwa)

---

## 2. Design System Atum

### 2.1 Identidade visual

- **Tema:** Escuro, media center hi-fi
- **Acento:** VFD teal `#00e5c8` (`--atum-accent`)
- **Fontes:** Inter (corpo), Barlow (secundária), Orbitron (labels técnicos, receiver)

### 2.2 Tokens obrigatórios (index.css)

| Categoria | Tokens |
|-----------|--------|
| **Cores** | `--atum-bg`, `--atum-sidebar`, `--atum-card`, `--atum-card-hover`, `--atum-accent`, `--atum-accent-hover`, `--atum-text`, `--atum-text-muted`, `--atum-muted`, `--atum-fg`, `--atum-border`, `--atum-error`, `--atum-success`, `--atum-warning`, `--atum-surface`, `--atum-elevated`, `--atum-overlay`, `--atum-bg-input`, `--atum-hover`, `--atum-text-on-accent`, `--atum-white` |
| **Espaçamento** | `--space-1` a `--space-10` (base 4px) |
| **Tipografia** | `--text-xs` a `--text-display`, `--weight-normal` a `--weight-bold` |
| **Radius** | `--radius-sm` a `--radius-full` |
| **Sombras** | `--shadow-sm` a `--shadow-xl` |
| **Z-index** | `--z-base` a `--z-tooltip` |
| **Transições** | `--transition-fast`, `--transition-normal`, `--transition-slow`, `--transition-spring` |
| **Touch** | `--touch-target-min: 44px`, `--touch-target-comfortable: 48px` |
| **Safe areas** | `--safe-top`, `--safe-right`, `--safe-bottom`, `--safe-left` |

**Regra:** Nunca usar cores hardcoded (#fff, #000, rgba(...)); sempre `var(--atum-*)` ou `var(--space-*)`.

**Tokens Receiver/VFD:** Para Player e receiver: `--atum-vfd-ow-04` (overlay branco 4%), `--atum-border` (bordas), `--atum-tab-bar-start`/`--atum-tab-bar-end` (gradientes escuros), `--atum-bg`. Evitar `#2a2a2a`, `#0e0e0e`, `#0a0a0a`, `rgba(255,255,255,0.04)` — usar os tokens acima.

**Labels VFD:** Orbitron + `letter-spacing: 0.15em` + `text-transform: uppercase` + `color: var(--atum-accent)` + `text-shadow: 0 0 8px rgba(0, 229, 200, 0.3)`.

---

## 3. Responsividade

| Breakpoint | Range | Layout |
|------------|-------|--------|
| Phone | ≤599px | Tab bar inferior, sem sidebar, BottomSheet como sheet, padding com safe-area |
| Tablet | 600–1023px | Sidebar overlay (hamburger), BottomSheet como modal centrado |
| Desktop | ≥1024px | Sidebar fixa (colapsável), rail arrows visíveis |

**Mobile-first:** Estilos base para phone; `@media (min-width: 600px)` e `@media (min-width: 1024px)` para upgrades.

**Touch targets:** Mínimo 44px. Usar `min-height: var(--touch-target-min)`.

---

## 4. Estados de UI (obrigatórios)

| Estado | Componente | Uso |
|--------|------------|-----|
| **Loading** | `SkeletonHero`, `SkeletonRail`, `SkeletonCard`, `SkeletonRow` | Nunca "Carregando..."; sempre skeleton com shimmer |
| **Empty** | `EmptyState` | Listas vazias; props: `icon`, `title`, `description`, `action` |
| **Error** | `role="alert"` + botão "Tentar novamente" | Sempre `setFetchKey(k=>k+1)` ou `refetch()` no retry |
| **Reconnecting** | `aria-live="polite"` | SSE: "Reconectando…" |

---

## 5. Componentes obrigatórios

| Componente | Quando usar | Props críticas |
|------------|-------------|----------------|
| **MediaCard** | Cards de mídia (biblioteca, playlists, busca) | `cover`, `title`, `meta`, `actions`, `primaryAction`, `coverShape`, `badge`, `overlay` |
| **CoverImage** | Qualquer capa (card, hero, now playing) | `contentType`, `title`, `size`, `downloadId`/`importId` |
| **EmptyState** | Lista vazia, busca sem resultados | `title`, `description`, `action` |
| **SkeletonHero** | Loading da Home (hero) | — |
| **SkeletonRail** | Loading de rails (Home) | — |
| **SkeletonCard** | Loading de grid (Library, Playlists) | — |
| **SkeletonRow** | Loading de lista (Downloads) | — |
| **SkeletonSearchResultCard** | Loading de resultados de busca | — |
| **BottomSheet** | Modais (notificações, menus, formulários) | `open`, `onClose`, `title`, `showCloseButton`, `children` |
| **Input** | Campos de texto, número, textarea, select | `Input`, `Textarea`, `Select` com `size: 'default' | 'small'`; classes `atum-input`, `atum-select` |
| **CircularProgress** | Progresso circular (download, overlay em card) | `percent`, `size`, `strokeWidth` |
| **ContentRail** | Seções horizontais com scroll (Home, etc.) | `title`, `linkTo`, `items`, `renderItem`, `getKey` |
| **CommandPalette** | Navegação rápida (Ctrl+K) | — (global) |
| **NowPlayingBar** | Mini-player persistente | — (global) |

**Regra:** Não criar componentes custom para listas vazias ou loading; usar EmptyState e Skeleton.

---

## 6. Templates de página

| Template | Classe raiz | Exemplos |
|----------|-------------|----------|
| **Hero + Rails** | `atum-page home-page` | Home |
| **Grid de cards** | `atum-page` | Library, Playlists |
| **Lista/Table** | `atum-page` | Downloads |
| **Busca** | `atum-page` | Search |
| **Detail** | `atum-page` | Detail |
| **Fullscreen** | (sem Layout) | ReceiverPlayer, Player |
| **Form** | `atum-page` | Settings |

**Convenção:** Toda página dentro de Layout usa `className="atum-page [page-name]-page"`.

---

## 7. PWA (obrigatório)

- **Manifest:** `display: standalone`, `theme_color: #0a0a0a`, `lang: pt-BR`, shortcuts (Buscar, Biblioteca, Downloads)
- **App Shell:** Layout com sidebar/tab bar + Outlet; NowPlayingBar fixo; CommandPalette global
- **Offline:** injectManifest (src/sw.ts), precache, `offline.html` em falhas de rede (setCatchHandler), runtime caching para `/api/cover/*` e `/api/*`
- **Meta tags:** `viewport-fit=cover`, `theme-color`, `apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style: black-translucent`
- **Safe areas:** `env(safe-area-inset-*)` em tab bar, main, modais
- **Service Worker:** `registerSW({ immediate: true })`, `registerType: 'prompt'` (feedback de atualização via PWAUpdatePrompt)
- **Offline:** setCatchHandler serve `offline.html` quando navegação falha (rede indisponível).

---

## 8. Padrões de layout

- **ContentRail:** Seção com h2 + link "Ver tudo" + scroll horizontal (`overflow-x: auto`, `scroll-snap-type: x proximity`). Cards com `scroll-snap-align: start`. Arrows só em desktop.
- **Grid:** `atum-library-grid` (CSS Grid). Variante vídeos: `atum-library-grid--videos`.
- **Facets/Chips:** `atum-library-facet-chip`, `atum-library-facet-chip--active`. `type="button"`, `min-height: var(--touch-target-min)`.
- **Botões:** `atum-btn` (secundário), `atum-btn-primary` (acento), `atum-btn-small`, `atum-btn--danger`. Centralizados em `index.css`; nunca duplicar em páginas.
- **Modais:** Preferir `BottomSheet`. Se custom: `role="dialog"`, `aria-modal="true"`, `aria-label`, `useFocusTrap`.

---

## 9. Acessibilidade

- Skip link: "Pular para conteúdo principal" → `#main-content`
- Modais: `role="dialog"`, `aria-modal="true"`, `aria-label`, `useFocusTrap`
- Progresso: `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Listas vazias: `EmptyState` com `role="status"`
- Erros: `role="alert"`
- Loading: `aria-busy="true"` no container; skeletons com `aria-hidden`
- Botões: `aria-label` descritivo (ex.: "Reproduzir [nome]")

---

## 10. Convenções CSS

- **Layout:** prefixo `atum-` (atum-sidebar, atum-nav-item, atum-tab-bar)
- **Páginas:** prefixo `[page]-` (home-rail, home-hero, library-grid)
- **Receiver:** `receiver-*`, `styles/receiver.css`

---

## 11. Princípios técnicos (SOLID, KISS)

| Princípio | Regras |
|-----------|--------|
| **SRP** | Um componente/hook = uma responsabilidade |
| **OCP** | Extensão por composição (props `children`, `actions`); evitar switch/if por tipo |
| **DIP** | Injetar `cachedFetch` ou abstração de API; não acoplar fetch em componentes de UI |
| **KISS** | Preferir `useState` + `useEffect` simples; máximo ~150 linhas por componente |
| **Clean Architecture** | `pages` (orquestração) → `components` (UI) → `hooks` (lógica) → `utils`/`api` (infra) |

---

## 12. Anti-patterns a evitar

- Duplicar interfaces (`LibraryItem`, `ContentType`) — centralizar em `types/`
- Fetch inline em páginas sem abstração — usar `cachedFetch` ou service
- Componentes >200 linhas — extrair subcomponentes ou hooks
- CSS sem tokens — sempre `var(--atum-*)`
- Ignorar erros com `.catch(() => {})` — logar ou mostrar toast

---

## 13. Estrutura de pastas

```
frontend/src/
├── api/           # services de API centralizados
├── types/         # tipos compartilhados (LibraryItem, Feed, etc.)
├── components/    # UI pura, sem fetch direto
├── pages/         # containers, orquestram fetch + componentes
├── hooks/         # lógica reutilizável
├── contexts/      # estado global por domínio
├── utils/         # funções puras
└── styles/        # CSS por domínio
```

---

## 14. Checklist para o agente

Antes de commitar:

- [ ] Tipos em `types/` se reutilizados
- [ ] Fetch via `cachedFetch` ou service
- [ ] Loading/Error/Empty tratados
- [ ] ARIA em modais e controles
- [ ] CSS com tokens
- [ ] Componente < 200 linhas

## 15. Checklist UX/UI (conformidade PWA)

- [ ] **Tokens:** Sempre `var(--atum-*)` ou `var(--space-*)`; nunca cores hardcoded (#fff, #000, rgba).
- [ ] **Botões:** Usar `atum-btn`, `atum-btn-primary`, `atum-btn-small`, `atum-btn--danger`; nunca `primary add-btn` ou classes custom.
- [ ] **Touch targets:** `min-height: var(--touch-target-min)` em controles interativos (botões, chips, tabs).
- [ ] **Modais:** Preferir `BottomSheet`; se custom: `role="dialog"`, `aria-modal="true"`, `useFocusTrap`.
- [ ] **Estados:** Loading → Skeleton; Empty → EmptyState; Error → `role="alert"` + retry.
- [ ] **Focus:** `:focus-visible` em todos os controles interativos.
- [ ] **PWA:** Safe areas, manifest, theme-color; evitar fallbacks de cores incorretos.
- [ ] **Inputs:** Usar `Input`, `Textarea`, `Select`; não criar classes custom (`atum-settings-input`, `pd-edit-input`, etc.).
- [ ] **Modais:** Preferir BottomSheet; migrar overlays custom para BottomSheet.
