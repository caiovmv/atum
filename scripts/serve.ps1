# dl-torrent: Build, iniciar, parar ou reiniciar API Web (8000) e Download Runner (9092)
# Uso: .\scripts\serve.ps1 [ build | start | stop | restart ]
#   build   - apenas build do frontend (npm run build)
#   start   - inicia o Runner (9092) em background e o servidor (8000) em primeiro plano
#   stop    - encerra processos nas portas 8000 e 9092
#   restart - stop + build + start (padrão)

param(
    [ValidateSet("build", "start", "stop", "restart")]
    [string]$Action = "restart"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot

$PortServe = 8000
$PortRunner = 9092

function Stop-ProcessOnPort {
    param([int]$Port)
    $pids = (Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique
    foreach ($p in $pids) {
        if ($p -gt 0) {
            Write-Host "Encerrando processo $p (porta $Port)..."
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }
    $line = netstat -ano 2>$null | findstr "LISTENING" | findstr ":$Port "
    if ($line) {
        $parts = $line.Trim() -split "\s+"
        $pid = $parts[-1]
        if ($pid -match '^\d+$') {
            Write-Host "Encerrando processo $pid (porta $Port)..."
            taskkill /PID $pid /F 2>$null
        }
    }
}

function Stop-All {
    Write-Host "Parando API Web (porta $PortServe) e Runner (porta $PortRunner)..."
    Stop-ProcessOnPort -Port $PortServe
    Stop-ProcessOnPort -Port $PortRunner
    Write-Host "Concluído."
}

function Build-Frontend {
    Write-Host "Build do frontend..."
    Push-Location (Join-Path $ProjectRoot "frontend")
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build falhou" }
        Write-Host "Frontend build OK."
    } finally {
        Pop-Location
    }
}

function Start-Runner {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"
    Write-Host "Iniciando Download Runner em http://127.0.0.1:$PortRunner ..."
    Start-Process -FilePath "python" -ArgumentList "-m", "app.main", "runner", "-p", $PortRunner -NoNewWindow -PassThru | Out-Null
    Start-Sleep -Seconds 1
}

function Start-Serve {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"
    Write-Host "Iniciando API Web em http://0.0.0.0:$PortServe ..."
    python -m app.main serve --port $PortServe --host 0.0.0.0
}

switch ($Action) {
    "build"  {
        Build-Frontend
    }
    "stop"   {
        Stop-All
    }
    "start"  {
        Start-Runner
        Start-Serve
    }
    "restart" {
        Stop-All
        Build-Frontend
        Start-Runner
        Start-Serve
    }
}
