# Análise Profunda de Coerência UX/UI — Atum PWA

> Auditoria de design tokens, componentes e padrões de UX/UI com foco em consistência profissional para PWA.  
> Documento gerado a partir do plano de implementação.

---

## Resumo Executivo

O projeto Atum possui documentação sólida ([FRONTEND_STANDARDS.md](../frontend/FRONTEND_STANDARDS.md), [FRONTEND_COMPLIANCE_ANALYSIS.md](FRONTEND_COMPLIANCE_ANALYSIS.md)), mas a exploração do código revelou **divergências** entre o estado documentado e o real. Esta análise cobre tokens, componentes, padrões de interação e requisitos de PWA.

### Status Pós-Implementação

| Categoria | Status |
|-----------|--------|
| Design Tokens | Corrigido — fallbacks e hardcoded removidos |
| Sistema de Botões | Unificado — atum-btn em todos os contextos |
| Touch Targets | Padronizado — var(--touch-target-min) |
| Semântica de cores | Corrigido — --atum-accent em vez de --atum-primary |
| FRONTEND_STANDARDS | Atualizado — checklist de conformidade UX/UI |

---

## 1. Design Tokens — Coerência e Violações

### 1.1 Estado Atual

Os tokens estão centralizados em [frontend/src/index.css](../frontend/src/index.css) (`:root`): cores, espaçamento, tipografia, radius, sombras, z-index, transições, touch targets e safe areas.

### 1.2 Violações Corrigidas

| Arquivo | Problema | Correção |
|---------|----------|----------|
| Feeds.css | Fallbacks incorretos (#2ecc71) | Removidos; uso direto de var(--atum-*) |
| Layout.css | Cores hardcoded (#fff, #333, etc.) | Substituídos por tokens |
| NowPlayingBar.css | Hex e rgba diretos | Substituídos por tokens |
| Playlists.css | Fallback accent errado | Removido |
| Downloads.css | Token inexistente (--color-danger) | Substituído por --atum-error |
| Search.css | Overlay hardcoded | Substituído por var(--atum-overlay) |
| AudioVisualizer.css | Valores diretos | Substituídos por tokens |
| Wishlist.css | Fallbacks (#2ecc71, #333, etc.) | Removidos |
| PlaylistDetail.css | Fallbacks e hardcoded (#3498db, #2ecc71) | Substituídos por tokens |
| Radio.css | Fallback --atum-error | Removido |
| MediaCard.css | Fallback --atum-text-muted | Removido |
| receiver.css | Fallbacks no Receiver AI | Removidos |
| receiver.css | #0a0a0a, #080808 em sliders/dots | var(--atum-bg), var(--atum-bg-darkest) |
| Radio.css | #000 em botões accent | var(--atum-text-on-accent) |
| Library.css | #000 em tabs/chips ativos | var(--atum-text-on-accent) |
| Player.css | #080808, #000 | var(--atum-bg-darkest), var(--atum-text-on-accent) |
| ContentRail.css | #000 em play/arrows | var(--atum-text-on-accent) |
| smarteq.css | #111, #ff6b6b | var(--atum-vfd-bg-black), var(--atum-error) |

### 1.3 Redundância e Confusão Semântica

- **--atum-primary** (#3498db) foi deprecado em favor de **--atum-accent** (#00e5c8) para ações primárias.
- Fallbacks desnecessários removidos em componentes.

---

## 2. Componentes — Inconsistências Corrigidas

### 2.1 Sistema de Botões (Unificado)

| Antes | Depois |
|------|--------|
| `primary add-btn`, `secondary add-btn` (SearchAddModal, SearchFilesModal, SearchResultsGrid) | `atum-btn atum-btn-primary`, `atum-btn` |
| `class="primary"` (DownloadsTable) | `atum-btn atum-btn-primary`, `atum-btn` |

### 2.2 CSS de Botões (Centralizado)

- `.atum-btn` e variantes centralizados em index.css.
- Duplicações removidas de Feeds.css, Library.css, PlaylistDetail.css.
- `.add-btn` em Search.css migrado para classes atum-btn.

### 2.3 Modais

- **BottomSheet** (padrão): LayoutNotifications, LibraryEditBottomSheet, CoverRefreshBottomSheet, SearchAddModal, SearchFilesModal, PlaylistEditModal.
- Todos os modais migrados para BottomSheet; `showCloseButton` para botão × no header.

---

## 3. Touch Targets e Acessibilidade (PWA)

### 3.1 Padronização

- Tokens: `--touch-target-min: 44px`, `--touch-target-comfortable: 48px`.
- Uso padronizado: `min-height: var(--touch-target-min)` em elementos interativos.
- Layout.css, Home.css, Library.css, Search.css, Downloads.css atualizados.

---

## 4. PWA — UX Específica

### 4.1 Pontos Fortes

- Manifest com `display: standalone`, `theme_color`, `lang: pt-BR`, shortcuts.
- Safe areas em tab bar, main, modais.
- Service worker (injectManifest): precache, fallback para `index.html`, `offline.html` em falhas de rede, runtime caching.
- Meta tags Apple (`viewport-fit=cover`, `apple-mobile-web-app-capable`, etc.).

### 4.2 Gaps (Recomendações Futuras)

| Aspecto | Estado | Recomendação |
|---------|--------|---------------|
| Install prompt | Implementado | PWAInstallBanner com beforeinstallprompt |
| offline.html | Implementado | injectManifest + setCatchHandler serve offline.html em falhas de rede |
| Feedback de atualização | Implementado | registerType: 'prompt', PWAUpdatePrompt com Recarregar/Depois |

---

## 5. Hierarquia Visual e Tipografia

### 5.1 Identidade

- **Tema:** Escuro, media center hi-fi.
- **Accent:** VFD teal `#00e5c8` (--atum-accent).
- **Fontes:** Inter (corpo), Barlow (secundária), Orbitron (labels técnicos).

### 5.2 Consistência

- MediaCard, CoverImage, ContentRail seguem tokens.
- Labels VFD (Orbitron + letter-spacing + text-shadow) documentados e usados no receiver.

---

## 6. Estados de UI e Feedback

### 6.1 Loading / Empty / Error

- Skeleton, EmptyState e `role="alert"` + retry implementados conforme padrão.
- DownloadsTable com `role="progressbar"` e `aria-valuenow/min/max`.

### 6.2 Micro-interações

- MediaCard: hover com transition, overlay com scale.
- Focus-visible em MediaCard e Layout.
- Transições definidas em tokens.

---

## 7. Checklist de Conformidade UX/UI

- [ ] Tokens: sempre `var(--atum-*)` ou `var(--space-*)`; nunca cores hardcoded.
- [ ] Botões: usar `atum-btn`, `atum-btn-primary`, `atum-btn-small`, `atum-btn--danger`.
- [ ] Touch targets: `min-height: var(--touch-target-min)` em controles interativos.
- [ ] Modais: preferir BottomSheet; se custom: `role="dialog"`, `aria-modal="true"`, `useFocusTrap`.
- [ ] Estados: Loading → Skeleton; Empty → EmptyState; Error → role="alert" + retry.
- [ ] Focus: `:focus-visible` em todos os controles interativos.
- [ ] PWA: safe areas, manifest, offline, theme-color.

---

## 8. Arquivos Modificados

- `frontend/src/index.css` — tokens atum-btn centralizados, --atum-primary deprecado
- `frontend/src/components/Layout.css` — cores hardcoded → tokens
- `frontend/src/components/NowPlayingBar.css` — hex/rgba → tokens
- `frontend/src/pages/Feeds.css` — fallbacks removidos, --atum-primary → --atum-accent
- `frontend/src/pages/Playlists.css` — fallbacks removidos
- `frontend/src/pages/Downloads.css` — --color-danger → --atum-error
- `frontend/src/pages/Search.css` — overlay → token, add-btn → atum-btn
- `frontend/src/pages/Library.css` — duplicação atum-btn removida
- `frontend/src/pages/PlaylistDetail.css` — duplicação atum-btn removida
- `frontend/src/pages/Home.css` — touch target tokenizado
- `frontend/src/components/receiver/AudioVisualizer/AudioVisualizer.css` — tokens
- `frontend/src/components/search/SearchAddModal.tsx` — migrado para BottomSheet
- `frontend/src/components/search/SearchFilesModal.tsx` — migrado para BottomSheet
- `frontend/src/components/playlists/PlaylistEditModal.tsx` — migrado para BottomSheet, usa Input/Textarea
- `frontend/src/components/search/SearchResultsGrid.tsx` — add-btn → atum-btn
- `frontend/src/components/downloads/DownloadsTable.tsx` — primary → atum-btn
- `frontend/FRONTEND_STANDARDS.md` — checklist UX/UI atualizado
- `frontend/src/sw.ts` — injectManifest, setCatchHandler para offline.html
- `frontend/src/components/Input.tsx` — Input, Textarea, Select reutilizáveis
