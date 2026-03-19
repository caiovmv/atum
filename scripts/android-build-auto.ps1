# Script para gerar APK Android (fluxo automatizado com twa-manifest + update)
# Requisitos: Node.js, cloudflared, JDK, Android SDK em ANDROID_HOME

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"
$AndroidDir = Join-Path $ProjectRoot "android-twa"
$Port = 3847
$AndroidSdk = "C:\Users\Caio Villela\AppData\Local\Android\Sdk"

Write-Host "=== Atum: Gerar APK (automatizado) ===" -ForegroundColor Cyan

# 1. Build
Write-Host "[1/6] Build do frontend..." -ForegroundColor Yellow
Push-Location $FrontendDir
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location

# 2. Servidor
Write-Host "[2/6] Iniciando servidor..." -ForegroundColor Yellow
$serveProc = Start-Process -FilePath "npx" -ArgumentList "--yes", "serve", "dist", "-l", $Port -WorkingDirectory $FrontendDir -PassThru -WindowStyle Hidden
Start-Sleep 4

# 3. Tunnel
Write-Host "[3/6] Iniciando Cloudflare Tunnel..." -ForegroundColor Yellow
$tunnelProc = Start-Process -FilePath "cloudflared" -ArgumentList "tunnel", "--url", "http://localhost:$Port" -PassThru -WindowStyle Hidden -RedirectStandardOutput "$env:TEMP\cloudflared-out.txt" -RedirectStandardError "$env:TEMP\cloudflared-err.txt"
Start-Sleep 15

$url = $null
for ($i = 0; $i -lt 10; $i++) {
    $content = Get-Content "$env:TEMP\cloudflared-err.txt" -Raw -ErrorAction SilentlyContinue
    $m = [regex]::Match($content, "https://([a-zA-Z0-9\-]+)\.trycloudflare\.com")
    if ($m.Success) { $url = $m.Value; break }
    Start-Sleep 2
}

if (-not $url) {
    Write-Host "  ERRO: URL do tunnel nao obtida." -ForegroundColor Red
    $serveProc | Stop-Process -Force -ErrorAction SilentlyContinue
    $tunnelProc | Stop-Process -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "  URL: $url" -ForegroundColor Green
Start-Sleep 5

# 4. Preparar android-twa
Write-Host "[4/6] Preparando projeto TWA..." -ForegroundColor Yellow
$hostName = ($url -replace "https://", "" -replace "/", "").Trim()
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
$manifest | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $AndroidDir "twa-manifest.json") -Encoding UTF8

if (-not (Test-Path (Join-Path $AndroidDir "android.keystore"))) {
    & "C:\Program Files\Eclipse Adoptium\jre-21.0.8.9-hotspot\bin\keytool" -genkey -v -keystore (Join-Path $AndroidDir "android.keystore") -alias android -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android -dname "CN=Atum, OU=Dev, O=Atum, L=Local, ST=Local, C=BR" 2>&1 | Out-Null
}

# 5. Bubblewrap update (Android SDK: No, path: C:\Users\Caio Villela\AppData\Local\Android\Sdk)
Write-Host "[5/6] Executando bubblewrap update..." -ForegroundColor Yellow
$bwInput = "n`n$AndroidSdk"
$result = $bwInput | bubblewrap update --skipVersionUpgrade 2>&1
$result | Write-Host

if ($result -match "ERROR") {
    Write-Host "  Tunnel pode ter expirado. Tente rodar .\scripts\android-build.ps1 e manter aberto." -ForegroundColor Yellow
    $serveProc | Stop-Process -Force -ErrorAction SilentlyContinue
    $tunnelProc | Stop-Process -Force -ErrorAction SilentlyContinue
    exit 1
}

# 6. Build
Write-Host "[6/6] Executando bubblewrap build..." -ForegroundColor Yellow
Push-Location $AndroidDir
bubblewrap build 2>&1
$buildExit = $LASTEXITCODE
Pop-Location

$serveProc | Stop-Process -Force -ErrorAction SilentlyContinue
$tunnelProc | Stop-Process -Force -ErrorAction SilentlyContinue

if ($buildExit -eq 0) {
    Write-Host ""
    Write-Host "APK gerado em: $AndroidDir\app\build\outputs\apk\debug\" -ForegroundColor Green
} else {
    Write-Host "Build falhou. Verifique os erros acima." -ForegroundColor Red
    exit 1
}
