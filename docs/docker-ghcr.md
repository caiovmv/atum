# Imagens Docker no GitHub Container Registry (GHCR)

As imagens do projeto são publicadas em **ghcr.io/caiovmv/atum-***.

## Usar imagens publicadas

O [docker-compose.yml](../docker-compose.yml) já referencia as imagens do GHCR. Para rodar sem build local:

```bash
docker-compose pull
docker-compose up -d
```

(Imagens: `ghcr.io/caiovmv/atum-api`, `ghcr.io/caiovmv/atum-frontend`, `ghcr.io/caiovmv/atum-runner`.)

## Publicar novas versões (recomendado: GitHub Actions)

O **build e o push** são feitos no **GitHub Actions**. Ao dar push de uma tag `v*` (ex.: `v0.2.0`), o workflow [.github/workflows/build-and-push-ghcr.yml](../.github/workflows/build-and-push-ghcr.yml) roda, constrói as 3 imagens e publica no GHCR.

1. **Permissões do workflow:** em **Settings → Actions → General**, em "Workflow permissions", marque **Read and write permissions** (para o `GITHUB_TOKEN` poder publicar em `ghcr.io`).

2. **Criar e publicar uma versão:**

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

   O Actions fará o build e o push de `atum-api`, `atum-frontend` e `atum-runner` com a tag `v0.2.0` (e `latest`).

3. **Execução manual:** em **Actions → Build and push to GHCR → Run workflow** você pode rodar o job informando a tag (ex.: `v0.2.0`) sem precisar dar push em uma tag.

### Publicar localmente (opcional)

Se quiser buildar e publicar na sua máquina:

1. Login: `echo SEU_PAT | docker login ghcr.io -u caiovmv --password-stdin`
2. Build: `docker-compose build`
3. Tag e push (PowerShell, troque `v0.2.0` pela versão desejada):

   ```powershell
   $tag = "v0.2.0"
   docker tag dl-torrent-api:latest "ghcr.io/caiovmv/atum-api:$tag"
   docker tag dl-torrent-frontend:latest "ghcr.io/caiovmv/atum-frontend:$tag"
   docker tag dl-torrent-runner:latest "ghcr.io/caiovmv/atum-runner:$tag"
   docker push "ghcr.io/caiovmv/atum-api:$tag"
   docker push "ghcr.io/caiovmv/atum-frontend:$tag"
   docker push "ghcr.io/caiovmv/atum-runner:$tag"
   ```

4. Atualize o `image:` no `docker-compose.yml` para a nova tag se quiser que o compose use essa versão por padrão.
