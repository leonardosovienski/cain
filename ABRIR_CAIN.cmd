@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-cain.ps1" -Mode web
if errorlevel 1 pause
