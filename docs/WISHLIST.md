# Wishlist — Melhorias Futuras

Itens identificados durante o desenvolvimento que agregam valor mas não são prioridade imediata.

---

## Infraestrutura / Kubernetes

### GitOps com ArgoCD ou Flux

**Contexto:** O pipeline atual usa `kubectl apply -k k8s/` que é puramente aditivo.
Recursos removidos do repositório **não são deletados** do cluster automaticamente.
Isso exige intervenção manual em casos como remoção de um CRD ou renomeação de recursos.

**O que seria ganho:**
- Cluster sincronizado 1:1 com o repositório (inclusive deleções)
- Rollback automático por commit/tag
- Interface visual para acompanhar o estado do deploy (ArgoCD)
- Reconciliação contínua — cluster volta ao estado desejado se alguém alterar algo manualmente
- Audit trail completo de quem fez o quê no cluster

**Opções:**
- **ArgoCD** — interface web rica, bom para times, curva de aprendizado moderada
- **Flux** — mais leve, GitOps puro via CLI, integração nativa com GitHub

**Referências:**
- https://argo-cd.readthedocs.io
- https://fluxcd.io

---

## Cloudflare

### Desabilitar QUIC/HTTP3 para rotas SSE

**Contexto:** Os endpoints de Server-Sent Events (`/api/indexers/events`, `/api/downloads/events`, `/api/notifications/events`) falham com `ERR_QUIC_PROTOCOL_ERROR` quando acessados via Cloudflare Tunnel. O protocolo QUIC/HTTP3 encerra conexões de longa duração que não têm o perfil de uma requisição HTTP convencional, quebrando o SSE.

**O que deve ser feito:**
Criar uma **Transform Rule** ou **Page Rule** no Cloudflare para o domínio `atum.loombeat.com` que force HTTP/2 (desabilitando QUIC) nas rotas que correspondam a `/api/*events*`.

Alternativa mais simples: desabilitar QUIC globalmente para o domínio em **Speed → Optimization → Protocol Optimization → HTTP/3 (QUIC)**.

**Impacto se não corrigido:** Os eventos em tempo real (downloads ativos, notificações, status de indexers) não chegam ao frontend — o app precisa fazer polling manual ou perde reatividade.
