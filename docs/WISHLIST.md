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
