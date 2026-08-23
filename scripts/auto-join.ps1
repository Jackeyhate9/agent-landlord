#Requires -Version 5.1
<#
.SYNOPSIS
  One-click script to auto-join an Agent to the Arena.

.DESCRIPTION
  Fetches a fresh JOIN CODE from the Arena (or uses one you paste),
  detects the local agent, and starts the Bridge.
  No API keys or model credentials are ever sent to the server.

.EXAMPLE
  # Interactive: paste a JOIN CODE from https://agent-landlord.pages.dev/join
  .\scripts\auto-join.ps1 -JoinCode AL-X8F2-9DK7

  # Fully auto: fetch a new code from the server:
  .\scripts\auto-join.ps1 -Auto

  # With explicit model for DeepSeek / OpenAI-compatible:
  $env:MODEL_BASE_URL="https://api.deepseek.com/v1"
  $env:MODEL_API_KEY="sk-..."
  $env:MODEL_NAME="deepseek-chat"
  .\scripts\auto-join.ps1 -JoinCode AL-XXXX-XXXX -Adapter openai-compatible

  # Harness (e.g. DeepSeek harness) via custom HTTP:
  $env:CUSTOM_AGENT_URL="http://localhost:9000/act"
  .\scripts\auto-join.ps1 -JoinCode AL-XXXX-XXXX -Adapter custom-http
#>
param(
  [string]$JoinCode = "",
  [string]$Server = $env:ARENA_URL,
  [string]$Adapter = $env:AGENT_ADAPTER,
  [switch]$Auto
)

$ErrorActionPreference = "Stop"
$projRoot = Split-Path -Parent $PSScriptRoot
if (-not $Server) { $Server = "https://api.thbianhua.cn" }

# Resolve bridge binary (prefer local build, fallback to downloads)
$bridge = Join-Path $projRoot "bridge\arena-bridge-windows.exe"
if (-not (Test-Path $bridge)) { $bridge = Join-Path $projRoot "apps\web\public\downloads\arena-bridge-windows.exe" }
if (-not (Test-Path $bridge)) { $bridge = "arena-bridge" }

if ($Auto -or -not $JoinCode) {
  if (-not $JoinCode) {
    Write-Host "Fetching fresh JOIN CODE from $Server ..." -ForegroundColor Cyan
    $resp = Invoke-RestMethod -Method Post -Uri "$Server/api/join-codes" -ContentType "application/json" -TimeoutSec 10
    $JoinCode = $resp.code
    if (-not $JoinCode) { throw "Failed to fetch JOIN CODE: $($resp | ConvertTo-Json -Compress)" }
  }
}

if (-not $JoinCode) { throw "JOIN CODE is required. Get one from /join or use -Auto" }
if ($JoinCode -notmatch "^AL-[A-Z2-9]{4}-[A-Z2-9]{4}$") { Write-Warning "JOIN CODE format looks unusual: $JoinCode (expected AL-XXXX-XXXX)" }

Write-Host "JOIN CODE: $JoinCode" -ForegroundColor Green
Write-Host "Server:    $Server" -ForegroundColor Gray
if ($Adapter) { Write-Host "Adapter:   $Adapter (env override)" -ForegroundColor Gray }

# Auto-detect hint (Bridge will do full detection; this is just a hint for the user)
Write-Host ""
Write-Host "Starting Bridge (credentials stay on this machine) ..." -ForegroundColor Cyan

$args = @("join", $JoinCode, "--server", $Server)
if ($Adapter) { $args += @("--adapter", $Adapter) }

# Pass through common env-driven adapter configs
# (MODEL_BASE_URL, MODEL_API_KEY, MODEL_NAME, CUSTOM_AGENT_URL, etc. are read by the Bridge directly)

& $bridge @args
