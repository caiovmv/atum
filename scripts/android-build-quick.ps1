# Script rapido: tunnel + bubblewrap update IMEDIATO (antes do tunnel expirar)
# JDK ja deve estar instalado em ~/.bubblewrap/jdk

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"
$AndroidDir = Join-Path $ProjectRoot "android-twa"
$Port = 3847
$AndroidSdk = "C:\Users\Caio Villela\AppData\Local\Android\Sdk"

Write-Host "=== Atum: Build APK (fluxo rapido) ===" -ForegroundColor Cyan

# 1. Build
Write-Host "[1/5] Build..." -ForegroundColor Yellow
Push-Location $FrontendDir
npm run build 2>&1 | Out-Null
Pop-Location

# 2. Serve em background (cmd /c para npx no Windows)
Write-Host "[2/5] Servidor..." -ForegroundColor Yellow
$serve = Start-Process -FilePath "cmd" -ArgumentList "/c","npx","--yes","serve","dist","-l",$Port -WorkingDirectory $FrontendDir -PassThru -WindowStyle Hidden
Start-Sleep 4

# 3. Tunnel
Write-Host "[3/5] Tunnel (aguarde URL)..." -ForegroundColor Yellow
$tunnel = Start-Process -FilePath "cloudflared" -ArgumentList "tunnel","--url","http://localhost:$Port" -PassThru -WindowStyle Hidden -RedirectStandardError "$env:TEMP\cf-err.txt"
Start-Sleep 12

$url = $null
for ($i = 0; $i -lt 5; $i++) {
    $c = Get-Content "$env:TEMP\cf-err.txt" -Raw -ErrorAction SilentlyContinue
    $m = [regex]::Match($c, "https://([a-zA-Z0-9\-]+)\.trycloudflare\.com")
    if ($m.Success) { $url = $m.Value; break }
    Start-Sleep 2
}

if (-not $url) {
    Write-Host "  ERRO: URL nao obtida" -ForegroundColor Red
    $serve,$tunnel | Stop-Process -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "  URL: $url" -ForegroundColor Green

# 4. Preparar twa-manifest e rodar update IMEDIATAMENTE
Write-Host "[4/5] Bubblewrap update (execute rapido)..." -ForegroundColor Yellow
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
$manifest | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $AndroidDir "twa-manifest.json") -Encoding UTF8

if (-not (Test-Path (Join-Path $AndroidDir "android.keystore"))) {
    & "C:\Program Files\Eclipse Adoptium\jre-21.0.8.9-hotspot\bin\keytool" -genkey -v -keystore (Join-Path $AndroidDir "android.keystore") -alias android -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android -dname "CN=Atum, OU=Dev, O=Atum, L=Local, ST=Local, C=BR" 2>&1 | Out-Null
}

# JDK ja instalado - pode pedir Android SDK: n + path
$bwInput = "n`n$AndroidSdk"
$updateResult = $bwInput | bubblewrap update --skipVersionUpgrade 2>&1
$updateResult | Write-Host

if ($updateResult -match "ERROR") {
    Write-Host "  Tunnel pode ter expirado. Tente novamente." -ForegroundColor Red
    $serve,$tunnel | Stop-Process -Force -ErrorAction SilentlyContinue
    exit 1
}

# 5. Build
Write-Host "[5/5] Bubblewrap build..." -ForegroundColor Yellow
Push-Location $AndroidDir
bubblewrap build 2>&1
$buildExit = $LASTEXITCODE
Pop-Location

$serve | Stop-Process -Force -ErrorAction SilentlyContinue
$tunnel | Stop-Process -Force -ErrorAction SilentlyContinue

if ($buildExit -eq 0) {
    Write-Host ""
    Write-Host "APK em: $AndroidDir\app\build\outputs\apk\debug\" -ForegroundColor Green
} else {
    Write-Host "Build falhou." -ForegroundColor Red
    exit 1
}
