param(
    [ValidateSet('chat', 'api', 'doctor', 'demo')]
    [string]$Mode = 'chat',
    [string]$UserId = 'leo'
)
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskLocalFile = Join-Path $taskRoot '.cain.local.json'
$taskLocal = $null
if (Test-Path -LiteralPath $taskLocalFile) {
    $taskLocal = Get-Content -LiteralPath $taskLocalFile -Raw | ConvertFrom-Json
}
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if ($taskLocal -and (Test-Path -LiteralPath $taskLocal.python)) {
    $taskPython = $taskLocal.python
}
if (-not (Test-Path -LiteralPath $taskPython)) {
    & python -m venv (Join-Path $taskRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' }
    & $taskPython -m pip install -e ($taskRoot + '[api]')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install Cain dependencies.' }
}
$taskOllama = $null
if ($taskLocal -and (Test-Path -LiteralPath $taskLocal.ollama_exe)) {
    $taskOllama = $taskLocal.ollama_exe
} elseif (Get-Command ollama -ErrorAction SilentlyContinue) {
    $taskOllama = (Get-Command ollama).Source
}
$env:PYTHONUTF8 = '1'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
if ($taskLocal -and $taskLocal.models_path) { $env:OLLAMA_MODELS = $taskLocal.models_path }
$taskReady = $false
try {
    $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 3
    $taskReady = $true
} catch { }
if (-not $taskReady) {
    if (-not $taskOllama) { throw 'Install Ollama first: https://ollama.com/download/windows' }
    $taskData = Join-Path $taskRoot 'data'
    $null = New-Item -ItemType Directory -Force -Path $taskData
    $null = Start-Process -FilePath $taskOllama -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskData 'ollama.stdout.log') -RedirectStandardError (Join-Path $taskData 'ollama.stderr.log')
    for ($taskAttempt = 0; $taskAttempt -lt 20; $taskAttempt++) {
        try {
            $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
            $taskReady = $true
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $taskReady) { throw 'Ollama did not start. Read data/ollama.stderr.log.' }
}
Push-Location $taskRoot
try {
    switch ($Mode) {
        'chat' { & $taskPython -X utf8 -m cain chat --user $UserId }
        'doctor' { & $taskPython -X utf8 -m cain doctor }
        'api' { & $taskPython -X utf8 -m uvicorn cain.api:create_app --factory --host 127.0.0.1 --port 8000 }
        'demo' { & $taskPython -X utf8 -m cain.evaluation --mode functional --provider ollama --output evaluation/results }
    }
    $taskExit = $LASTEXITCODE
} finally { Pop-Location }
exit $taskExit
