#Requires -Version 7.0
param(
  [int]$Port = 18080,
  [string]$TunnelConfig = "$env:USERPROFILE\.cloudflared\config.yml"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDir = Join-Path $projectRoot "data\logs"
$webRoot = Join-Path $projectRoot "apps\web"
$distIndex = Join-Path $webRoot "dist\index.html"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Test-Python([string]$Path, [string[]]$Arguments = @()) {
  if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $false }
  try {
    & $Path @Arguments --version *> $null
    return $LASTEXITCODE -eq 0
  } catch { return $false }
}

function Invoke-Checked([string]$Label, [string]$FilePath, [string[]]$Arguments = @()) {
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE" }
}

function Test-AgentTools([string]$PythonPath) {
  $scriptsDir = Split-Path -Parent $PythonPath
  $mcpLauncher = Join-Path $scriptsDir "agent-landlord-mcp.exe"
  $joinLauncher = Join-Path $scriptsDir "agent-landlord-join.exe"
  if (-not (Test-Path -LiteralPath $mcpLauncher) -or -not (Test-Path -LiteralPath $joinLauncher)) {
    return $false
  }
  try {
    & $PythonPath -c "import mcp, agent_landlord_mcp.server, agent_landlord_mcp.cli" *> $null
    return $LASTEXITCODE -eq 0
  } catch { return $false }
}

function Get-LatestWriteTimeUtc([string[]]$Paths) {
  $latest = [datetime]::MinValue
  foreach ($path in $Paths) {
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $item = Get-Item -LiteralPath $path
    $files = if ($item.PSIsContainer) { Get-ChildItem -LiteralPath $path -Recurse -File } else { @($item) }
    foreach ($file in $files) {
      if ($file.LastWriteTimeUtc -gt $latest) { $latest = $file.LastWriteTimeUtc }
    }
  }
  return $latest
}

function Test-FrontendBuild {
  if (-not (Test-Path -LiteralPath $distIndex)) { return $false }
  $html = Get-Content -LiteralPath $distIndex -Raw
  $assets = [regex]::Matches($html, '(?:src|href)="(/assets/[^"]+)"')
  if ($assets.Count -eq 0) { return $false }
  foreach ($asset in $assets) {
    $assetPath = Join-Path $webRoot $asset.Groups[1].Value.TrimStart('/')
    if (-not (Test-Path -LiteralPath $assetPath)) { return $false }
  }
  return $true
}

if (-not (Test-Python $venvPython)) {
  $fallbackVenv = Join-Path $projectRoot ".venv-live"
  $fallbackPython = Join-Path $fallbackVenv "Scripts\python.exe"
  if (Test-Python $fallbackPython) {
    $venvPython = $fallbackPython
  } else {
    $candidates = @()
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { $candidates += [pscustomobject]@{ Path = $py.Source; Args = @('-3') } }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { $candidates += [pscustomobject]@{ Path = $python.Source; Args = @() } }
    $launcher = $candidates | Where-Object { Test-Python $_.Path $_.Args } | Select-Object -First 1
    if (-not $launcher) {
      throw "Python 3.11+ was not found. Install Python from https://www.python.org/downloads/"
    }
    $launcherArgs = @($launcher.Args)
    & $launcher.Path @launcherArgs -m venv $fallbackVenv
    $venvPython = $fallbackPython
    & $venvPython -m pip install -e $projectRoot
  }
}

if (-not (Test-AgentTools $venvPython)) {
  Write-Host "[SETUP] Installing local MCP and Agent join commands..."
  $editableMcpTarget = $projectRoot + "[mcp]"
  Invoke-Checked "MCP installation" $venvPython @('-m','pip','install','--disable-pip-version-check','-e',$editableMcpTarget)
}

$frontendInputs = @(
  (Join-Path $webRoot "src"),
  (Join-Path $webRoot "index.html"),
  (Join-Path $webRoot "package.json"),
  (Join-Path $webRoot "pnpm-lock.yaml"),
  (Join-Path $webRoot "vite.config.ts"),
  (Join-Path $webRoot "tsconfig.json"),
  (Join-Path $webRoot "tsconfig.app.json"),
  (Join-Path $webRoot "tsconfig.node.json"),
  (Join-Path $projectRoot "packages\protocol")
)
$latestFrontendInput = Get-LatestWriteTimeUtc $frontendInputs
$frontendBuildCurrent = Test-FrontendBuild
if ($frontendBuildCurrent) {
  $frontendBuildCurrent = (Get-Item -LiteralPath $distIndex).LastWriteTimeUtc -ge $latestFrontendInput
}

if (-not $frontendBuildCurrent) {
  $node = Get-Command node -ErrorAction SilentlyContinue
  $pnpm = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
  if (-not $pnpm) { $pnpm = Get-Command pnpm -ErrorAction SilentlyContinue }
  if (-not $node) { throw "Node.js 20+ is required to build the live frontend" }
  if (-not $pnpm) { throw "pnpm is required to build the live frontend" }
  Write-Host "[SETUP] Frontend sources changed; building the current live UI..."
  Push-Location -LiteralPath $webRoot
  try {
    Invoke-Checked "Frontend dependency installation" $pnpm.Source @('install','--frozen-lockfile','--prefer-offline')
    Invoke-Checked "Frontend build" $pnpm.Source @('run','build')
  } finally {
    Pop-Location
  }
  if (-not (Test-FrontendBuild)) { throw "Frontend build completed without valid dist assets" }
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

$backend = $null
$localReady = $false
try {
  $existingHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/ready" -TimeoutSec 2
  $localReady = $existingHealth.status -eq 'ok'
} catch { }

if (-not $localReady) {
  $backend = Start-Process -FilePath $venvPython `
    -ArgumentList @('-m','uvicorn','server.app.main:app','--host','127.0.0.1','--port',"$Port") `
    -WorkingDirectory $projectRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "backend.out.log") `
    -RedirectStandardError (Join-Path $logDir "backend.err.log") -PassThru
}

try {
  $ready = $localReady
  if (-not $ready) {
    foreach ($attempt in 1..30) {
      Start-Sleep -Milliseconds 500
      try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/ready" -TimeoutSec 2
        if ($health.status -eq 'ok') { $ready = $true; break }
      } catch { }
    }
  }
  if (-not $ready) { throw "Arena backend did not become ready; see data/logs/backend.err.log" }

  $publicReady = $false
  try {
    $publicHealth = Invoke-RestMethod -Uri "https://api.thbianhua.cn/ready" -TimeoutSec 4
    $publicReady = $publicHealth.status -eq 'ok'
  } catch { }
  $tunnel = $null
  if (-not $publicReady) {
    $tunnel = Start-Process -FilePath $cloudflaredPath `
      -ArgumentList @('tunnel','--config',$TunnelConfig,'run',$tunnelMatch.Groups[1].Value) `
      -WorkingDirectory $projectRoot -WindowStyle Hidden `
      -RedirectStandardOutput (Join-Path $logDir "tunnel.out.log") `
      -RedirectStandardError (Join-Path $logDir "tunnel.err.log") -PassThru
    foreach ($attempt in 1..30) {
      Start-Sleep -Seconds 1
      try {
        $publicHealth = Invoke-RestMethod -Uri "https://api.thbianhua.cn/ready" -TimeoutSec 4
        if ($publicHealth.status -eq 'ok') { $publicReady = $true; break }
      } catch { }
    }
  }
  if (-not $publicReady) { throw "Public tunnel did not become ready; see data/logs/tunnel.err.log" }
  $backendState = if ($backend) { "started PID=$($backend.Id)" } else { "already healthy" }
  $tunnelState = if ($tunnel) { "started PID=$($tunnel.Id)" } else { "already healthy" }
  Write-Host "[OK] Backend: $backendState"
  Write-Host "[OK] Tunnel:  $tunnelState"
  Write-Host "[OK] Local:   http://127.0.0.1:$Port/ready"
  Write-Host "[OK] Public:  https://api.thbianhua.cn/ready"
} catch {
  if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
  if ($tunnel -and -not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -Force }
  throw
}
