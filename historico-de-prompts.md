# Histórico de Prompts

## 2026-03-19

### Prompt 1

quero uma pasta chamada k8s, ela deve conter todas definicoes para publicarmos essa aplicacao em um cluster kubernetes. quero arrumar o meu github actions para deployar o que esta no k8s no kubernetes configurado na variavel KUBECONFIG do github

**Resultado:** Criada a pasta `k8s/` com manifests Kubernetes completos para toda a aplicação Atum: namespace, configmap, secret (template), StatefulSets para postgres e redis, Deployments para api, runner, frontend, feed-daemon, sync-daemon, indexers-daemon, enrichment-daemon e flaresolverr, Services (incluindo LoadBalancer para portas BitTorrent), Ingress e PVCs compartilhados. Kustomization.yaml como ponto de entrada. GitHub Actions (`build-and-push-ghcr.yml`) atualizado com job `deploy` que usa `kubectl apply -k k8s/` com kubeconfig via secret `KUBECONFIG`. `k8s/secret.yaml` adicionado ao `.gitignore`.

### Prompt 2

acho melhor o pvc library-music e library-videos virarem apenas library e dentro deste pvc vai ter pasta music, video, series, concert and others in the future.

**Resultado:** PVCs `library-music` (100Gi) e `library-videos` (500Gi) consolidados em único PVC `library` (1Ti) em `k8s/shared-pvcs.yaml`. Todos os deployments (api, runner, sync-daemon, enrichment) atualizados para montar o PVC `library` com `subPath` por categoria (`music`, `videos`, `series`, `concerts`). Paths visíveis nos containers permanecem inalterados.

### Prompt 3

agora quero adicionar health check nos services. e quero implementar todos os headers de seguranca possiveis

### Prompt 4

continuar (after HLS+Shaka implementation — fix lock file and build config)

**Resultado:** Atualizado `package-lock.json` com `shaka-player@4.16.23` (via `npm install`) e `vite.config.ts` com chunk separado `'shaka'` para isolar a lib (~1.5 MB) do bundle vendor. Build corrigido para passar em `npm ci`. Push em `master`.

### Prompt 5

o que mais falta? / continuar terminar todos os to-dos

**Resultado:** Implementados todos os gaps identificados na análise pós-HLS:
- `hls_service.py`: `invalidate_cache()`, `invalidate_all_for_item()`, `cleanup_partial_caches()`, `_get_video_duration()` (ffprobe), progress tracking real via parse de stderr do FFmpeg (regex `time=HH:MM:SS`)
- `library.py`: endpoints `DELETE /api/library/{id}/hls/{file_index}` e `DELETE /api/library/{id}/hls`
- `app.py`: limpeza automática de caches parciais no lifespan (pod restart recovery)
- `ShakaPlayer.tsx`: barra de progresso % real, botão "Reproduzir agora (sem HLS)", botão "Reiniciar transcodificação" (chama DELETE + reinicia)
- `ShakaPlayer.css`: estilos da barra de progresso e dos botões
- Correção crítica: `hls_serve` agora serve `master.m3u8` assim que primeiro segmento existe (reprodução progressiva ~6-12s após início), não aguarda 100% da transcodificação
- Cache headers: `.m3u8` recebe `no-store` durante transcodificação, `.ts` recebe `max-age=86400`
- FFmpeg: `-hls_playlist_type event` para playlist crescer incrementalmente
- Tags v1.13.1, v1.13.2, v1.13.3 criadas e publicadas

### Prompt 6

Streaming HLS + Shaka Player — Roadmap e Phase 1 (implement the plan)

**Resultado:** Implementada a Phase 1 completa do roadmap HLS:
- `src/app/web/hls_service.py` (novo): serviço de transcodificação FFmpeg multi-bitrate (360p/720p/1080p) com cache em `/app/hls_cache`, estado de job in-memory com polling
- `src/app/runner/app.py`: endpoint `GET /downloads/{id}/file-path` para resolver caminho absoluto do arquivo
- `src/app/config.py`: propriedade `hls_cache_path` (via env `HLS_CACHE_DIR`)
- `src/app/web/routers/library.py`: endpoints `GET /hls/{idx}/status` e `GET /hls/{idx}/{path:path}` (master.m3u8, playlists e segmentos .ts)
- `frontend/src/components/ShakaPlayer.tsx` (novo): componente React com polling de status, spinner de processamento e fallback automático para stream progressivo
- `frontend/src/pages/Player.tsx` e `ReceiverPlayer.tsx`: usam ShakaPlayer para conteúdo de vídeo
- `frontend/src/hooks/useReceiverPlayer.ts`: expõe `hlsUrl` calculado
- `k8s/shared-pvcs.yaml`: PVC `hls-cache` (200Gi)
- `k8s/api/deployment.yaml`: monta PVC em `/app/hls_cache`
- Tag v1.13.0 criada e publicada

**Resultado:** Implementado em 10 arquivos:
- Criado docker/security-headers.conf com 7 headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, HSTS e Content-Security-Policy (CSP restrita para SPA React com WebGL e TMDB)
- Dockerfile.frontend atualizado para copiar o arquivo de headers para a imagem
- docker/nginx.conf e k8s/frontend/nginx-k8s-configmap.yaml atualizados com server_tokens off e include do snippet em cada location block (estrategia necessaria pois nginx nao herda add_header de blocos pai)
- startupProbe adicionado na api e runner (30 tentativas de 10s = 5min maximos de startup)
- initialDelaySeconds removido do liveness/readiness apos startupProbe (redundante)
- liveness + 
eadiness via pgrep adicionados em feed-daemon, sync-daemon, indexers-daemon
- 
eadinessProbe adicionado no enrichment-daemon (ja tinha liveness)
- Tag v1.12.0 criada e publicada

### Prompt 8

resolva todos (em resposta ao diagnóstico de gaps: assert, resolução de variante, evicção de cache, testes backend, testes frontend)

**Resultado:** v1.13.4 — 6 itens resolvidos em 8 arquivos:
- `hls_service.py`: `assert proc.stderr` substituído por guard explícito; `_get_video_info` (substitui `_get_video_duration`) detecta também a resolução; `_select_variants(height)` seleciona apenas variantes ≤ resolução original (sem upscale); `_build_master_m3u8` e `_build_ffmpeg_cmd` gerados dinamicamente; `is_playable` e `cleanup_partial_caches` usam `glob("stream_*")` em vez de `range(3)` fixo; adicionada função `evict_caches(max_age_days, max_size_gb)`
- `library.py`: endpoint `POST /hls/evict?max_age_days=30&max_size_gb=100`
- `k8s/api/hls-cache-eviction-cronjob.yaml` (novo): CronJob diário às 3h que chama o endpoint de evicção
- `k8s/kustomization.yaml`: inclui o novo CronJob
- `tests/unit/test_hls_service.py` (novo): 36 testes pytest cobrindo seleção de variantes, geração de m3u8, regex de progresso, cleanup, invalidate, is_playable e evict
- `ShakaPlayer.tsx`: fix crítico — `<video>` agora sempre está no DOM (overlay de spinner é absoluto); resolve bug onde `videoRef.current` virava null durante 'checking'/'processing' impedindo o Shaka de se anexar
- `ShakaPlayer.css`: `.shaka-processing-overlay` como camada absoluta sobre o vídeo
- `frontend/src/components/__tests__/ShakaPlayer.test.tsx` (novo): 14 testes vitest cobrindo todos os estados do componente (ready, processing, fallback, unmount)

### Prompt 9

continuar (em resposta ao diagnóstico: _jobs leak, sem semáforo FFmpeg, shaka sem tipos)

**Resultado:** v1.13.5 — 3 itens técnicos resolvidos:
- `config.py`: `hls_max_concurrent_jobs: int = 2` (configurável via env `HLS_MAX_CONCURRENT_JOBS`)
- `hls_service.py`: semáforo `asyncio.Semaphore` criado lazily; `_run_ffmpeg` split em wrapper (adquire semáforo) + `_run_ffmpeg_inner`; `evict_caches()` limpa entradas órfãs do dict `_jobs`; `get_active_job_count()` exposta para monitoramento
- `frontend/src/types/shaka-player.d.ts` (novo): declarações TypeScript para a API do Shaka Player
- `ShakaPlayer.tsx`: `any` substituído por tipos `ShakaModule` e `ShakaPlayer`; 4 novos testes no backend (total: 40 testes passando)
- Tag v1.13.5 criada e publicada

### Prompt 10

"crie o arquivo e implemente o plano" (POSICIONAMENTO.md + Phase 2 completa)

**Resultado:** v2.0.0 — implementação completa da Phase 2 em 66 arquivos:
- `docs/POSICIONAMENTO.md`: análise fria e técnica comparando Atum com concorrentes (Plex, Jellyfin, Navidrome, Roon, arr stack, Spotify/Tidal) com scorecard, posicionamento, fraquezas e oportunidades
- Migrations 014–017: `plans`, `families`, `users`, `user_devices`, `refresh_tokens`, `invite_codes`, `storage_addons`, `subscriptions`, `payments`, `promo_codes`, `audit_log`, `hls_jobs`, `play_positions`, `cloud_sync_queue`; data ownership via `family_id` em todas as tabelas existentes
- `storage_service.py`: abstração S3/local com `MinIOBackend` (boto3) e `LocalBackend` (filesystem); factory por `STORAGE_BACKEND` env; helpers de convenção de chaves; `init_storage()` no startup
- `auth_service.py`: bcrypt, PyJWT (HS256), `AuthUser`, `create_access_token`, `create_refresh_token`, `get_current_user`, `require_backoffice`, `require_owner`, `seed_admin_user`
- `routers/auth.py`: `POST /api/auth/register`, `login`, `refresh`, `logout`, `GET /me`, `GET /devices`, `DELETE /devices/{id}`, `POST /invite`
- `web/app.py`: `_JWTAuthMiddleware` com fallback para BasicAuth; `seed_admin_user` e `init_storage` no lifespan; routers auth/admin/stripe incluídos
- `config.py`: `jwt_secret`, `jwt_access_expire_min`, `jwt_refresh_expire_days`, `registration_open`, `admin_email`, `admin_password`, `stripe_*`, `minio_*`, `cold_tier_days`, `storage_pressure_pct`, `cloud_sync_hours`, `prefetch_count`
- `daemons/hls_daemon.py`: daemon isolado com polling de `hls_jobs`, FFmpeg com upload incremental de segmentos para MinIO, estratégias on_demand/automatic/lru, evicção LRU, CLI `dl-torrent hls daemon`
- `daemons/cloud_sync_daemon.py`: cold tiering, storage pressure release, janela de horário de sync, offline prefetch, processamento da fila `cloud_sync_queue`, CLI `dl-torrent cloud-sync daemon`
- `library.py`: endpoints HLS v2 (`/start`, `/status-v2`, `/presign/{path}`) baseados em DB jobs + presigned MinIO URLs
- `routers/admin/`: pacote completo com users, plans, subscriptions, financial (MRR/ARR/churn/revenue chart), invites, promo_codes, settings (platform-level), storage (MinIO/HLS/sync overview)
- `stripe_service.py + stripe_webhooks.py`: checkout session, customer portal, webhook com validação HMAC, handlers para subscription.created/updated/deleted, invoice.payment_succeeded/failed
- Frontend: `AuthContext` com auto-refresh, `api/auth.ts`, páginas `Login`, `Register`, `Account` (devices, plano, convites), `RequireAuth` guard em `App.tsx`
- `frontend-admin/`: Vite+React para `admin.loombeat.com` com layout, login (verifica `backoffice_role`), Dashboard (MRR/ARR/churn), Users, Plans, Subscriptions, Financial, Invites, PromoCodes, Storage, PlatformSettings
- `Dockerfile.admin` + `k8s/admin/` + `k8s/minio/` + `k8s/hls-daemon/` + `k8s/cloud-sync-daemon/`
- `docker-compose.yml`: serviços `minio`, `hls-daemon`, `cloud-sync-daemon`
- `kustomization.yaml` + GitHub Actions: build/push da imagem `atum-admin`
- Tag v2.0.0 criada e publicada

### Prompt 6

sim por favor

**Resultado:** v2.0.1 — correção de 6 bugs críticos de produção introduzidos na v2.0.0:
1. `requirements.txt`: adicionado `bcrypt>=4.0.0`, `PyJWT>=2.8.0`, `stripe>=8.0.0`, `boto3>=1.34.0` (dependências da Phase 2 ausentes)
2. `routers/auth.py`: corrigido import de `...db` (inexistente) para `...db_postgres.get_async_pool`
3. `auth_service.py`: adicionados helpers pré-construídos `require_super_admin`, `require_financial`, `require_support`, `require_any_backoffice` (funções FastAPI-resolvíveis sem precisar de `Depends()` manual)
4. Todos admin routers: substituído `actor: AuthUser = require_backoffice(...)` (inválido como default) por `actor: AuthUser = Depends(require_*)` (padrão correto do FastAPI)
5. `k8s/secret.yaml`: adicionados `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `STRIPE_*` ao secret existente + novo secret `minio-secret` separado para rotação independente
6. `k8s/configmap.yaml`: adicionadas variáveis `STORAGE_BACKEND`, `MINIO_ENDPOINT`, `MINIO_REGION`, `HLS_MAX_CONCURRENT_JOBS`, `COLD_TIER_DAYS`, `STORAGE_PRESSURE_PCT`, `CLOUD_SYNC_HOURS`, `PREFETCH_COUNT`, `JWT_ACCESS_EXPIRE_MIN`, `JWT_REFRESH_EXPIRE_DAYS`, `REGISTRATION_OPEN`
7. `.env.example`: documentadas todas as novas variáveis da Phase 2 com comentários e instruções

### Prompt 7

o que mais falta ?

**Resultado:** v2.0.2 — diagnóstico ativo e correção de 4 bugs de schema que causariam falhas em runtime:
1. `admin/invites.py`: `used_count` → `uses_count` (nome correto da coluna na migration 014)
2. `admin/invites.py`: coluna `plan_code` não existe em `invite_codes` — resolvido plan_code → plan_id via SELECT antes do INSERT; `created_by UUID NOT NULL` ausente no INSERT → preenchido com `actor.id`
3. `admin/settings.py`: `app_settings.value JSONB` exige JSON válido → corrigido com `json.dumps()` + cast `::jsonb`
4. `auth_service.py`: variável `raw` não usada em `create_refresh_token` → removida

### Prompt 8

[log de falha do GitHub Actions — build Docker do frontend falhando com erros TypeScript no `tsc -b`]

**Resultado:** Corrigidos 3 erros que quebravam o build do `Dockerfile.frontend`:
1. `ShakaPlayer.test.tsx`: substituídos todos os `global.fetch = ...` por `vi.stubGlobal('fetch', ...)` (API idiomática do Vitest; `global` não existe no contexto DOM/browser do TypeScript)
2. `ShakaPlayer.test.tsx`: adicionado `vi.unstubAllGlobals()` no `afterEach` para limpeza correta dos stubs
3. `ShakaPlayer.test.tsx`: corrigido tipo no `.filter()` — cast explícito `fetchMock.mock.calls as [string, RequestInit | undefined][]` eliminando o erro TS2769
4. `Account.tsx`: já estava correto (sem `import React` desnecessário) — o erro era da versão da tag v2.0.2 anterior às correções locais

### Prompt 9

voce padronizou os builds ? / sim

**Resultado:** Padronizados builds do CI/CD:
1. `Dockerfile.frontend`: substituído `npm run build` (`tsc -b && vite build`) por `npx vite build` — type-check já acontece no `ci.yml` antes do push da tag; rodar novamente no Docker era redundante e frágil
2. `build-and-push-ghcr.yml`: fundidos steps "Build API" e "Build Runner" em um único step com múltiplas tags — ambos usavam o mesmo `Dockerfile`, gerando build duplicado com cache separado desnecessário
3. `build-and-push-ghcr.yml`: adicionado `atum-admin` ao `kustomize edit set image` no job de deploy — a imagem era construída mas nunca atualizada no cluster

### Prompt 10

[log de falha — `npm ci` no `Dockerfile.admin` falha por ausência de `package-lock.json`]

**Resultado:**
1. Gerado `frontend-admin/package-lock.json` via `npm install --package-lock-only` (Node v22 no host)
2. `Dockerfile.admin`: substituído `npm run build` (`tsc && vite build`) por `npx vite build` — mesmo padrão adotado no `Dockerfile.frontend`

### Prompt 11

include pip upgrade before installing packages in all Dockerfiles that use python

**Resultado:** Adicionado `RUN pip install --upgrade pip` antes do primeiro `pip install` em `Dockerfile` e `Dockerfile.enrichment` (únicos com Python). Camada separada para aproveitar cache do Docker. Builds testados localmente antes do commit.

### Prompt 12

quais secrets da minha stack kubernetes não existem ?

**Resultado:** Análise de todos os manifestos vs `secret.yaml`. Encontrados e corrigidos 2 bugs:
1. `hls-daemon` e `cloud-sync-daemon` referenciavam `postgres-secret` (inexistente) — corrigido para `atum-secrets` (nome correto, consistente com todos os outros workloads)
2. `api/deployment.yaml`: `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`, `LASTFM_API_KEY`, `TMDB_READ_ACCESS_TOKEN` definidos em `atum-secrets` mas não injetados no pod — adicionadas as entradas `env` correspondentes
3. `traefik-dashboard-auth` (namespace kube-system): ausente intencionalmente — criação manual com htpasswd já documentada no `traefik-dashboard.yaml`

### Prompt 13

monte um script em scripts/ que faça um delete do workspace atum completo. quero todos os secrets deployados, não quero nada mais sendo feito manualmente. [+ ModuleNotFoundError: No module named 'bcrypt']

**Resultado:**
1. `pyproject.toml`: adicionadas dependências ausentes `bcrypt>=4.0.0`, `PyJWT>=2.8.0`, `stripe>=8.0.0`, `boto3>=1.34.0` (causavam ModuleNotFoundError em runtime)
2. `scripts/k8s-reset-atum.ps1`: script PowerShell que deleta o namespace atum, aguarda remoção completa, aplica `kubectl apply -k k8s/`, cria `atum-secrets` e `minio-secret` a partir do `.env.k8s`, e opcionalmente cria `traefik-dashboard-auth`. Suporte a `-SkipDelete` para reaplicar sem destruir.
3. `.env.k8s.example`: template com todas as chaves necessárias
4. `.gitignore`: `.env.k8s` adicionado