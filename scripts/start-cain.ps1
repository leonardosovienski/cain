param(
    [ValidateSet('chat', 'api', 'web', 'doctor', 'demo')]
    [string]$Mode = 'chat',
    [string]$UserId = 'leo',
    [switch]$NoBrowser,
    [ValidateRange(1024,65535)]
    [int]$Port = 8000
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
        'api' { & $taskPython -X utf8 -m uvicorn cain.api:create_app --factory --host 127.0.0.1 --port $Port }
        'web' {
            $taskUrl = 'http://127.0.0.1:' + $Port
            $taskWebReady = $false
            try {
                $taskHealth = Invoke-RestMethod ($taskUrl + '/health') -TimeoutSec 3
                if ($taskHealth.version -ne '0.3.0' -or $taskHealth.research_status -ne 'provisional') {
                    throw 'Another service is already using this port. Choose -Port with another number.'
                }
                $taskWebReady = $true
            } catch [System.Net.WebException] {
                # The service is not listening yet. The child reports a port conflict in its log.
            }
            if (-not $taskWebReady) {
                $taskData = Join-Path $taskRoot 'data'
                $null = New-Item -ItemType Directory -Force -Path $taskData
                $taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-X','utf8','-m','uvicorn','cain.api:create_app','--factory','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskData "web-$Port.stdout.log") -RedirectStandardError (Join-Path $taskData "web-$Port.stderr.log")
                $taskProcess.Id | Set-Content -LiteralPath (Join-Path $taskData "web-$Port.pid")
                for ($taskAttempt = 0; $taskAttempt -lt 30; $taskAttempt++) {
                    if ($taskProcess.HasExited) { throw "Cain did not start. Read data/web-$Port.stderr.log." }
                    try {
                        $taskHealth = Invoke-RestMethod ($taskUrl + '/health') -TimeoutSec 2
                        if ($taskHealth.version -eq '0.3.0' -and $taskHealth.research_status -eq 'provisional') {
                            $taskWebReady = $true
                            break
                        }
                    } catch { }
                    Start-Sleep -Milliseconds 500
                }
                if (-not $taskWebReady) { throw "Cain did not become ready. Read data/web-$Port.stderr.log." }
            }
            Write-Output "Cain is available at $taskUrl"
            if (-not $NoBrowser) { Start-Process $taskUrl }
        }
        'demo' { & $taskPython -X utf8 -m cain.evaluation --mode functional --provider ollama --output evaluation/results }
    }
    $taskExit = if ($Mode -eq 'web') { 0 } else { $LASTEXITCODE }
} finally { Pop-Location }
exit $taskExit
