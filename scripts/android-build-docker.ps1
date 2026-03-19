# Build APK via Docker Compose: frontend + cloudflared + android-build (JDK 25 + Android SDK em volumes)
# Requisitos: Docker. JDK e Android SDK sao instalados no container e persistidos em volumes.

# Continue em vez de Stop: Docker escreve em stderr e PowerShell trata como erro
$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AndroidDir = Join-Path $ProjectRoot "android-twa"

Write-Host "=== Atum: Build APK via Docker Compose ===" -ForegroundColor Cyan

# 1. Build das imagens frontend e android-build
Write-Host "[1/6] Build das imagens (frontend + android-build)..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose build frontend android-build 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "  ERRO: Build das imagens falhou." -ForegroundColor Red
    exit 1
}
Pop-Location
Write-Host "  OK" -ForegroundColor Green

# 2. Subir frontend + cloudflared (e dependencias)
Write-Host "[2/6] Subindo frontend e cloudflared..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose --profile android-build up -d frontend cloudflared 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    Write-Host "  ERRO: Falha ao subir os servicos." -ForegroundColor Red
    exit 1
}
Pop-Location
Write-Host "  OK" -ForegroundColor Green

# 3. Aguardar frontend healthy e cloudflared imprimir URL
Write-Host "[3/6] Aguardando URL do tunnel..." -ForegroundColor Yellow
$url = $null
Push-Location $ProjectRoot
Start-Sleep 15
for ($i = 0; $i -lt 40; $i++) {
    $logs = docker compose logs cloudflared --tail 50 2>&1
    $allMatches = [regex]::Matches($logs, "https://([a-zA-Z0-9\-]+)\.trycloudflare\.com")
    if ($allMatches.Count -gt 0) {
        $url = $allMatches[$allMatches.Count - 1].Value
        break
    }
    Start-Sleep 2
}

if (-not $url) {
    Pop-Location
    Write-Host "  ERRO: URL do tunnel nao obtida. Verifique: docker compose logs cloudflared" -ForegroundColor Red
    Push-Location $ProjectRoot
    docker compose stop cloudflared 2>&1 | Out-Null
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "  URL: $url" -ForegroundColor Green

# Aguardar manifest acessível (tunnel pode levar 30-90s para estabilizar)
Write-Host "  Aguardando manifest acessivel..." -ForegroundColor Gray
$manifestUrl = "$url/manifest.webmanifest"
for ($j = 0; $j -lt 30; $j++) {
    try {
        $r = Invoke-WebRequest -Uri $manifestUrl -Method Get -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            Write-Host "  Manifest OK" -ForegroundColor Green
            break
        }
    } catch { }
    if (($j % 5) -eq 0 -and $j -gt 0) { Write-Host "  Tentativa $($j+1)/30..." -ForegroundColor Gray }
    Start-Sleep 3
}

# 4. Atualizar twa-manifest e rodar bubblewrap update
Write-Host "[4/6] Bubblewrap update..." -ForegroundColor Yellow
$hostName = $url -replace "https://","" -replace "/",""
if (-not (Test-Path $AndroidDir)) { New-Item -ItemType Directory -Path $AndroidDir -Force | Out-Null }

$manifest = @{
    packageId = "com.atum.media"
    host = $hostName
    name = "Atum"
    launcherName = "atum"
    display = "standalone"
    themeColor = "#0a0a0a"
    themeColorDark = "#000000"
    navigationColor = "#0a0a0a"
    navigationColorDark = "#000000"
    backgroundColor = "#0a0a0a"
    enableNotifications = $true
    startUrl = "/"
    iconUrl = "https://placehold.co/512x512/0a0a0a/00e5c8/png?text=ATUM"
    maskableIconUrl = "https://placehold.co/512x512/0a0a0a/00e5c8/png?text=ATUM"
    webManifestUrl = "$url/manifest.webmanifest"
    signingKey = @{ path = "./android.keystore"; alias = "android" }
    appVersionCode = 1
    appVersion = "1"
    splashScreenFadeOutDuration = 300
    shortcuts = @()
    generatorApp = "bubblewrap"
    fallbackType = "customtabs"
    orientation = "any"
    minSdkVersion = 28
}
$manifestJson = $manifest | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText((Join-Path $AndroidDir "twa-manifest.json"), $manifestJson, [System.Text.UTF8Encoding]::new($false))

# Gerar keystore no container se nao existir
if (-not (Test-Path (Join-Path $AndroidDir "android.keystore"))) {
    Write-Host "  Gerando android.keystore..." -ForegroundColor Gray
    Push-Location $ProjectRoot
    docker compose run --rm android-build keytool -genkey -v -keystore /workspace/android-twa/android.keystore -alias android -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android -dname "CN=Atum, OU=Dev, O=Atum, L=Local, ST=Local, C=BR" 2>&1 | Out-Null
    Pop-Location
}

# Bubblewrap update (config.json em ~/.bubblewrap evita prompts)
$updateResult = docker compose run --rm -T android-build sh -c "cd /workspace/android-twa && bubblewrap update --skipVersionUpgrade" 2>&1
$updateResult | Write-Host

if ($updateResult -match "ERROR") {
    Write-Host "  ERRO: Bubblewrap update falhou. Tunnel pode ter expirado." -ForegroundColor Red
    Push-Location $ProjectRoot
    docker compose stop cloudflared 2>&1 | Out-Null
    Pop-Location
    exit 1
}
Write-Host "  OK" -ForegroundColor Green

# 4b. Reaplicar patch Android Auto (bubblewrap sobrescreve build.gradle e manifest)
& (Join-Path $ProjectRoot "scripts\apply-android-auto-patch.ps1")

# 5. Bubblewrap build no container (senhas do keystore via env para automação)
Write-Host "[5/6] Bubblewrap build..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose run --rm -e BUBBLEWRAP_KEYSTORE_PASSWORD=android -e BUBBLEWRAP_KEY_PASSWORD=android android-build sh -c "cd /workspace/android-twa && bubblewrap build" 2>&1 | Out-Host
$buildExit = $LASTEXITCODE
Pop-Location

# 6. Encerrar tunnel (apenas cloudflared; frontend e demais servicos continuam)
Write-Host "[6/6] Encerrando tunnel..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose stop cloudflared 2>&1 | Out-Null
Pop-Location

if ($buildExit -eq 0) {
    Write-Host ""
    Write-Host "APK em: $AndroidDir\app\build\outputs\apk\debug\" -ForegroundColor Green
} else {
    Write-Host "Build falhou." -ForegroundColor Red
    exit 1
}
