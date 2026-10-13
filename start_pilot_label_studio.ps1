param([int]$Port = 8081)
$ErrorActionPreference = 'Stop'
$env:LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED = 'true'
$env:LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT = $PSScriptRoot
$env:LABEL_STUDIO_BASE_DATA_DIR = Join-Path $PSScriptRoot '.pilot-runtime\label-studio'
$taskScratch = Join-Path $env:LABEL_STUDIO_BASE_DATA_DIR 'tmp'
New-Item -ItemType Directory -Force -Path $taskScratch | Out-Null
$env:SQLITE_TMPDIR = $taskScratch
$env:TMP = $taskScratch
$env:TEMP = $taskScratch
$env:LABEL_STUDIO_HOST = "http://localhost:$Port"
$env:LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK = 'false'
$env:LABEL_STUDIO_SENTRY_DSN = ''
$env:LABEL_STUDIO_FRONTEND_SENTRY_DSN = ''
$env:LABEL_STUDIO_ANALYTICS_ENABLED = 'false'
& (Join-Path $PSScriptRoot '.venv\Scripts\label-studio.exe') start --port $Port --no-browser --host $env:LABEL_STUDIO_HOST --data-dir $env:LABEL_STUDIO_BASE_DATA_DIR
