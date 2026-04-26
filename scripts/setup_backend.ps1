python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r backend\requirements.txt
if (-not (Test-Path backend\.env)) {
  Copy-Item backend\.env.example backend\.env
}

