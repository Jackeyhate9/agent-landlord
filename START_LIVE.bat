@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Agent Landlord Live

echo [Agent Landlord] Starting live services and running health checks...
where pwsh.exe >nul 2>nul
if errorlevel 1 (
  echo [ERROR] PowerShell 7 is required. Install it from https://aka.ms/powershell
  pause
  exit /b 1
)

pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-live.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] Startup failed. Check data\logs for details.
  pause
  exit /b 1
)

echo.
echo [READY] Agent Landlord is ready for OBS and remote agents.
echo [OBS] Table: https://api.thbianhua.cn/table?obs=1
echo [OBS] Queue: https://api.thbianhua.cn/queue?obs=1
echo [OBS] Hall:  https://api.thbianhua.cn/hall?obs=1
echo.
pause
exit /b 0
