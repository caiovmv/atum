# Script para gerar APK Android do Atum (PWA via Bubblewrap)
# Requisitos: Node.js, cloudflared, JDK 17, Android SDK (ou Bubblewrap instala JDK)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"
$DistDir = Join-Path $FrontendDir "dist"
$AndroidDir = Join-Path $ProjectRoot "android-twa"
$Port = 3847

Write-Host "=== Atum: Gerar APK Android ===" -ForegroundColor Cyan
Write-Host ""

# 1. Build do frontend
Write-Host "[1/5] Build do frontend..." -ForegroundColor Yellow
Push-Location $FrontendDir
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location
Write-Host "  OK" -ForegroundColor Green

# 2. Iniciar servidor local
Write-Host "[2/5] Iniciando servidor em porta $Port..." -ForegroundColor Yellow
$serveJob = Start-Job -ScriptBlock {
    param($d, $p)
    Set-Location $d
    & npx --yes serve dist -l $p 2>&1 | Out-Null
} -ArgumentList $FrontendDir, $Port

Start-Sleep -Seconds 3
Write-Host "  OK" -ForegroundColor Green

# 3. Expor via Cloudflare Tunnel (HTTPS)
Write-Host "[3/5] Expondo via Cloudflare Tunnel (aguarde URL HTTPS)..." -ForegroundColor Yellow
$tunnelJob = Start-Job -ScriptBlock {
    cloudflared tunnel --url "http://localhost:$using:Port" 2>&1
}

$url = $null
$maxWait = 30
for ($i = 0; $i -lt $maxWait; $i++) {
    $output = Receive-Job $tunnelJob
    if ($output) {
        $match = [regex]::Match($output, "https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
        if ($match.Success) {
            $url = $match.Value
            break
        }
    }
    Start-Sleep -Seconds 1
}

if (-not $url) {
    Stop-Job $serveJob, $tunnelJob
    Remove-Job $serveJob, $tunnelJob
    Write-Host "  ERRO: Nao foi possivel obter URL do tunnel. Verifique se cloudflared esta instalado." -ForegroundColor Red
    exit 1
}

$manifestUrl = "$url/manifest.webmanifest"
Write-Host "  URL: $url" -ForegroundColor Green
Write-Host "  Manifest: $manifestUrl" -ForegroundColor Gray

# 4. Instrucoes para Bubblewrap
Write-Host "[4/5] Proximos passos (em outro terminal):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  MANTER ESTE TERMINAL ABERTO - servidor e tunnel precisam estar ativos." -ForegroundColor Red
Write-Host ""
Write-Host "  Em um NOVO terminal, execute:" -ForegroundColor White
Write-Host ""
Write-Host "    cd $ProjectRoot" -ForegroundColor Cyan
Write-Host "    bubblewrap init --manifest=$manifestUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "  JDK: escolha 'Yes' para instalar." -ForegroundColor Gray
Write-Host "  Android SDK: escolha 'No' e use: C:\Users\Caio Villela\AppData\Local\Android\Sdk" -ForegroundColor Gray
Write-Host "  Use package name: com.atum.media" -ForegroundColor Gray
Write-Host ""
Write-Host "  Apos o init, edite android-twa/app/build.gradle:" -ForegroundColor White
Write-Host "    minSdk 28" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Depois rode:" -ForegroundColor White
Write-Host "    cd android-twa" -ForegroundColor Cyan
Write-Host "    bubblewrap build" -ForegroundColor Cyan
Write-Host ""
Write-Host "  O APK estara em: android-twa/app/build/outputs/apk/debug/" -ForegroundColor Gray
Write-Host ""
Write-Host "  Pressione Enter quando terminar para encerrar servidor e tunnel..." -ForegroundColor Yellow
Read-Host

Stop-Job $serveJob, $tunnelJob -ErrorAction SilentlyContinue
Remove-Job $serveJob, $tunnelJob -ErrorAction SilentlyContinue
Write-Host "Encerrado." -ForegroundColor Green
