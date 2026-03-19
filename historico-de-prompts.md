# Histórico de Prompts

## 2026-03-19

### Prompt 1

quero uma pasta chamada k8s, ela deve conter todas definicoes para publicarmos essa aplicacao em um cluster kubernetes. quero arrumar o meu github actions para deployar o que esta no k8s no kubernetes configurado na variavel KUBECONFIG do github

**Resultado:** Criada a pasta `k8s/` com manifests Kubernetes completos para toda a aplicação Atum: namespace, configmap, secret (template), StatefulSets para postgres e redis, Deployments para api, runner, frontend, feed-daemon, sync-daemon, indexers-daemon, enrichment-daemon e flaresolverr, Services (incluindo LoadBalancer para portas BitTorrent), Ingress e PVCs compartilhados. Kustomization.yaml como ponto de entrada. GitHub Actions (`build-and-push-ghcr.yml`) atualizado com job `deploy` que usa `kubectl apply -k k8s/` com kubeconfig via secret `KUBECONFIG`. `k8s/secret.yaml` adicionado ao `.gitignore`.
