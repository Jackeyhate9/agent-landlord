$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

docker compose up -d postgres redis
python -m pip install -e ".[test]"

$api = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "server.app.main:app", "--reload", "--port", "8080" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
$web = Start-Process -FilePath "npm.cmd" -ArgumentList "--prefix", "apps/web", "run", "dev", "--", "--host", "0.0.0.0" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru

Write-Host "Agent Landlord dev services started. API PID=$($api.Id), Web PID=$($web.Id)"
Write-Host "Web: http://localhost:5173/table  API: http://localhost:8080/health"
Write-Host "Stop with: Stop-Process -Id $($api.Id),$($web.Id)"

