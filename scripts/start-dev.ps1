$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

python -m pip install -e ".[test]"
npm.cmd --prefix apps/web install

$env:POSTGRES_URL = ""
$env:REDIS_URL = ""
$env:VITE_API_URL = "http://localhost:8080"
$env:VITE_WS_URL = "ws://localhost:8080"

$api = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "server.app.main:app", "--reload", "--port", "8080" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
$web = Start-Process -FilePath "npm.cmd" -ArgumentList "--prefix", "apps/web", "run", "dev", "--", "--host", "0.0.0.0" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

Write-Host "Agent Landlord dev services started. API PID=$($api.Id), Web PID=$($web.Id)"
Write-Host "Join: http://localhost:5173/join  Table: http://localhost:5173/table?obs=1"
Write-Host "API:  http://localhost:8080/health"
Write-Host "Stop with: Stop-Process -Id $($api.Id),$($web.Id)"

