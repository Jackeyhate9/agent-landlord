param(
  [Parameter(Mandatory=$true)][string]$RepoUrl,  # e.g. https://github.com/xxx/agent-landlord.git
  [string]$Tag = "v0.1.0"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path ".git")) { git init }
git remote remove origin 2>$null | Out-Null
git remote add origin $RepoUrl
git add .
git commit -m "feat: one-click Bridge + Cloudflare Pages" 2>$null | Out-Null
git branch -M main
git push -u origin main
Write-Host "Push complete. Now create release:"
Write-Host "  gh release create $Tag --generate-notes"
Write-Host "  or push tag: git tag $Tag; git push origin $Tag"
Write-Host "Release workflow will build:"
Write-Host "  arena-bridge-windows.exe / arena-bridge-macos / arena-bridge-linux"
Write-Host "  + aliases -amd64/-arm64 and ghcr.io/.../agent-landlord-bridge:latest"
