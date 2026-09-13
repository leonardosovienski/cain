@echo off
setlocal
set "PYTHONUTF8=1"
set "CAIN_RESEARCH_POLICY=%~dp0config\research-policy.json"
set "CAIN_RESEARCH_DB=%~dp0dados\research.db"
set "CAIN_DB=%~dp0dados\workspace.db"
pushd "%~dp0projeto"
"%~dp0.venv\Scripts\python.exe" -m cain %*
set "CAIN_RESULT=%errorlevel%"
popd
exit /b %CAIN_RESULT%
