@echo off
setlocal
set "CAIN_RESEARCH_POLICY=%~dp0config\research-policy.json"
set "CAIN_RESEARCH_DB=%~dp0dados\research.db"
set "CAIN_DB=%~dp0dados\workspace.db"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0projeto\scripts\start-cain.ps1" -Mode web -Port 8877 %*
if errorlevel 1 pause

