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
- liveness + eadiness via pgrep adicionados em feed-daemon, sync-daemon, indexers-daemon
- eadinessProbe adicionado no enrichment-daemon (ja tinha liveness)
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