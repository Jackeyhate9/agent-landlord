#Requires -Version 7.0
param(
  [int]$Port = 18080,
  [string]$TunnelConfig = "$env:USERPROFILE\.cloudflared\config.yml"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDir = Join-Path $projectRoot "data\logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $venvPython)) {
  $launcher = Get-Command py -ErrorAction SilentlyContinue
  $launcherArgs = @('-3')
  if ($launcher) {
    & $launcher.Source -3 --version *> $null
    if ($LASTEXITCODE -ne 0) { $launcher = $null }
  }
  if (-not $launcher) {
    $launcher = Get-Command python -ErrorAction Stop
    $launcherArgs = @()
  }
  & $launcher.Source @launcherArgs -m venv (Join-Path $projectRoot ".venv")
  & $venvPython -m pip install -e $projectRoot
}

if (-not (Test-Path -LiteralPath $TunnelConfig)) {
  throw "Cloudflare Tunnel config not found: $TunnelConfig"
}
$configText = Get-Content -LiteralPath $TunnelConfig -Raw
$tunnelMatch = [regex]::Match($configText, '(?m)^tunnel:\s*(\S+)\s*$')
if (-not $tunnelMatch.Success) { throw "Missing tunnel id in $TunnelConfig" }
if ($configText -notmatch "service:\s*http://(?:localhost|127\.0\.0\.1):$Port(?:\s|$)") {
  throw "Tunnel ingress must point to http://127.0.0.1:$Port"
}

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
  $bundled = Join-Path $env:USERPROFILE ".cloudflared\bin\cloudflared.exe"
  if (-not (Test-Path -LiteralPath $bundled)) { throw "cloudflared is not installed" }
  $cloudflaredPath = $bundled
} else {
  $cloudflaredPath = $cloudflared.Source
}

$backend = Start-Process -FilePath $venvPython `
  -ArgumentList @('-m','uvicorn','server.app.main:app','--host','127.0.0.1','--port',"$Port") `
  -WorkingDirectory $projectRoot -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $logDir "backend.out.log") `
  -RedirectStandardError (Join-Path $logDir "backend.err.log") -PassThru

try {
  $ready = $false
  foreach ($attempt in 1..20) {
    Start-Sleep -Milliseconds 500
    try {
      $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/ready" -TimeoutSec 2
      if ($health.status -eq 'ok') { $ready = $true; break }
    } catch { }
  }
  if (-not $ready) { throw "Arena backend did not become ready; see data/logs/backend.err.log" }

  $tunnel = Start-Process -FilePath $cloudflaredPath `
    -ArgumentList @('tunnel','--config',$TunnelConfig,'run',$tunnelMatch.Groups[1].Value) `
    -WorkingDirectory $projectRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "tunnel.out.log") `
    -RedirectStandardError (Join-Path $logDir "tunnel.err.log") -PassThru
  Write-Host "Agent Landlord live services started. Backend PID=$($backend.Id), Tunnel PID=$($tunnel.Id)"
  Write-Host "Local:  http://127.0.0.1:$Port/ready"
  Write-Host "Public: https://api.thbianhua.cn/ready"
} catch {
  if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
  throw
}
