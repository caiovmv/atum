# k8s-reset-atum.ps1
# Deleta o namespace atum por completo e o recria com todos os secrets aplicados.
#
# Uso:
#   .\scripts\k8s-reset-atum.ps1
#   .\scripts\k8s-reset-atum.ps1 -EnvFile "C:\segredos\.env.k8s"
#   .\scripts\k8s-reset-atum.ps1 -SkipDelete   # apenas aplica manifests + secrets, sem deletar
#
# Pré-requisitos:
#   - kubectl configurado e conectado ao cluster
#   - .env.k8s preenchido (copie .env.k8s.example e preencha os valores)

param(
    [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent) ".env.k8s"),
    [switch]$SkipDelete
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent

# ── Chaves obrigatórias ────────────────────────────────────────────────────────

$RequiredAtumKeys = @(
    "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_URL",
    "REDIS_URL",
    "TMDB_API_KEY", "TMDB_READ_ACCESS_TOKEN", "LASTFM_API_KEY",
    "BASIC_AUTH_USER", "BASIC_AUTH_PASS",
    "JWT_SECRET", "ADMIN_EMAIL", "ADMIN_PASSWORD",
    "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PUBLISHABLE_KEY"
)

$RequiredMinioKeys = @("MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD")

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Write-Ok([string]$msg) {
    Write-Host "    OK: $msg" -ForegroundColor Green
}

function Write-Fail([string]$msg) {
    Write-Host "    ERRO: $msg" -ForegroundColor Red
    exit 1
}

function Read-EnvFile([string]$path) {
    if (-not (Test-Path $path)) {
        Write-Fail "Arquivo de env nao encontrado: $path`nCopie .env.k8s.example para .env.k8s e preencha os valores."
    }
    $vars = @{}
    foreach ($line in Get-Content $path) {
        $line = $line.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { continue }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { continue }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        $vars[$key] = $val
    }
    return $vars
}

function Assert-Keys([hashtable]$vars, [string[]]$keys) {
    $missing = @()
    foreach ($k in $keys) {
        if (-not $vars.ContainsKey($k) -or $vars[$k] -eq "" -or $vars[$k] -like "*CHANGE_ME*") {
            $missing += $k
        }
    }
    if ($missing.Count -gt 0) {
        Write-Fail "Chaves ausentes ou nao preenchidas em .env.k8s:`n  $($missing -join ', ')"
    }
}

function Wait-NamespaceGone([string]$ns, [int]$timeoutSec = 180) {
    Write-Host "    Aguardando namespace '$ns' ser removido..." -NoNewline
    $elapsed = 0
    while ($elapsed -lt $timeoutSec) {
        $exists = kubectl get namespace $ns --ignore-not-found 2>$null
        if (-not $exists) {
            Write-Host " removido." -ForegroundColor Green
            return
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
    Write-Fail "Timeout: namespace '$ns' ainda existe apos ${timeoutSec}s."
}

function Wait-NamespaceReady([string]$ns, [int]$timeoutSec = 60) {
    Write-Host "    Aguardando namespace '$ns' estar pronto..." -NoNewline
    $elapsed = 0
    while ($elapsed -lt $timeoutSec) {
        $exists = kubectl get namespace $ns --ignore-not-found 2>$null
        if ($exists) {
            Write-Host " pronto." -ForegroundColor Green
            return
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 3
        $elapsed += 3
    }
    Write-Fail "Timeout: namespace '$ns' nao apareceu apos ${timeoutSec}s."
}

function New-LiteralArgs([hashtable]$vars, [string[]]$keys) {
    $args = @()
    foreach ($k in $keys) {
        $args += "--from-literal=$k=$($vars[$k])"
    }
    return $args
}

# ── Início ────────────────────────────────────────────────────────────────────

Write-Host "`nk8s-reset-atum.ps1" -ForegroundColor Yellow
Write-Host "EnvFile : $EnvFile"
Write-Host "SkipDelete: $SkipDelete"

# 1. Ler e validar .env.k8s
Write-Step "Lendo $EnvFile"
$env = Read-EnvFile $EnvFile
Assert-Keys $env $RequiredAtumKeys
Assert-Keys $env $RequiredMinioKeys
Write-Ok "Todas as chaves obrigatorias presentes."

# 2. Verificar conectividade com o cluster
Write-Step "Verificando conectividade com o cluster"
kubectl cluster-info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "kubectl nao consegue conectar ao cluster. Verifique o kubeconfig."
}
Write-Ok "Cluster acessivel."

# 3. Deletar namespace (opcional)
if (-not $SkipDelete) {
    Write-Host ""
    Write-Host "  ATENCAO — OPERACAO DESTRUTIVA E IRREVERSIVEL" -ForegroundColor Red
    Write-Host "  O namespace 'atum' sera deletado por completo, incluindo:" -ForegroundColor Yellow
    Write-Host "    - Todos os pods, deployments e services" -ForegroundColor Yellow
    Write-Host "    - Todos os PVCs (library 1Ti, postgres 10Gi, minio 500Gi, hls-cache 200Gi, covers 5Gi, redis 2Gi)" -ForegroundColor Yellow
    Write-Host "    - Os dados fisicos nos PVs serao apagados (reclaimPolicy: Delete)" -ForegroundColor Yellow
    Write-Host "    - A biblioteca de midia e o banco de dados serao perdidos permanentemente" -ForegroundColor Yellow
    Write-Host ""
    $confirm = Read-Host "  Digite 'DELETAR' para confirmar"
    if ($confirm -ne "DELETAR") {
        Write-Host "  Operacao cancelada." -ForegroundColor Green
        exit 0
    }

    Write-Step "Deletando namespace atum"
    kubectl delete namespace atum --ignore-not-found --wait=false
    Wait-NamespaceGone "atum"
} else {
    Write-Host "`n==> -SkipDelete ativo: pulando delete do namespace." -ForegroundColor Yellow
}

# 4. Aplicar todos os manifestos via Kustomize
Write-Step "Aplicando manifests (kubectl apply -k k8s/)"
kubectl apply -k (Join-Path $ProjectRoot "k8s")
if ($LASTEXITCODE -ne 0) { Write-Fail "kubectl apply -k falhou." }
Write-Ok "Manifests aplicados."

# 5. Aguardar namespace estar pronto
Wait-NamespaceReady "atum"

# 6. Criar atum-secrets
Write-Step "Criando secret atum-secrets"
$atumKeys = @(
    "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_URL",
    "REDIS_URL",
    "TMDB_API_KEY", "TMDB_READ_ACCESS_TOKEN", "LASTFM_API_KEY",
    "BASIC_AUTH_USER", "BASIC_AUTH_PASS",
    "JWT_SECRET", "ADMIN_EMAIL", "ADMIN_PASSWORD",
    "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PUBLISHABLE_KEY"
)
$literalArgs = New-LiteralArgs $env $atumKeys

kubectl delete secret atum-secrets -n atum --ignore-not-found | Out-Null
kubectl create secret generic atum-secrets -n atum @literalArgs
if ($LASTEXITCODE -ne 0) { Write-Fail "Falha ao criar atum-secrets." }
Write-Ok "atum-secrets criado."

# 7. Criar minio-secret
Write-Step "Criando secret minio-secret"
$minioArgs = New-LiteralArgs $env @("MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD")

kubectl delete secret minio-secret -n atum --ignore-not-found | Out-Null
kubectl create secret generic minio-secret -n atum @minioArgs
if ($LASTEXITCODE -ne 0) { Write-Fail "Falha ao criar minio-secret." }
Write-Ok "minio-secret criado."

# 8. Criar traefik-dashboard-auth (opcional)
$traefUser = $env["TRAEFIK_DASHBOARD_USER"]
$traefPass = $env["TRAEFIK_DASHBOARD_PASSWORD"]

if ($traefUser -and $traefUser -ne "" -and $traefPass -and $traefPass -ne "") {
    Write-Step "Criando secret traefik-dashboard-auth (kube-system)"
    $hash = kubectl run htpasswd-gen --rm -i --restart=Never --image=httpd:alpine `
        -- htpasswd -nb $traefUser $traefPass 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $hash) {
        Write-Host "    AVISO: falha ao gerar hash htpasswd. Pulando traefik-dashboard-auth." -ForegroundColor Yellow
    } else {
        kubectl delete secret traefik-dashboard-auth -n kube-system --ignore-not-found | Out-Null
        kubectl create secret generic traefik-dashboard-auth `
            --from-literal=users="$hash" -n kube-system
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    AVISO: falha ao criar traefik-dashboard-auth." -ForegroundColor Yellow
        } else {
            Write-Ok "traefik-dashboard-auth criado."
        }
    }
} else {
    Write-Host "`n==> Traefik dashboard auth: pulado (TRAEFIK_DASHBOARD_USER/PASSWORD nao definidos)." -ForegroundColor Yellow
}

# 9. Aguardar rollouts principais
Write-Step "Aguardando rollouts"
$deployments = @(
    @{ name = "api";               ns = "atum" },
    @{ name = "runner";            ns = "atum" },
    @{ name = "frontend";          ns = "atum" },
    @{ name = "enrichment-daemon"; ns = "atum" }
)

foreach ($d in $deployments) {
    Write-Host "    Rollout: $($d.name)..." -NoNewline
    kubectl rollout status deployment/$($d.name) -n $($d.ns) --timeout=180s 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " TIMEOUT (verifique manualmente)" -ForegroundColor Yellow
    }
}

Write-Host "`nCluster atum resetado com sucesso.`n" -ForegroundColor Green
