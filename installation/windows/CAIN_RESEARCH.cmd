@echo off
setlocal
set "PYTHONUTF8=1"
pushd "%~dp0projeto"
"%~dp0.venv\Scripts\python.exe" -m cain research --policy "%~dp0config\research-policy.json" --db "%~dp0dados\research.db" %*
set "CAIN_RESULT=%errorlevel%"
popd
exit /b %CAIN_RESULT%
