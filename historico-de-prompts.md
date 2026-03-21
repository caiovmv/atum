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