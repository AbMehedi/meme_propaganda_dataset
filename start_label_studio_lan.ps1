param(
    [string]$LanAddress
)

if (-not $LanAddress) {
    $LanAddress = Get-NetIPAddress -InterfaceAlias 'Wi-Fi' -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object { $_.IPAddress -notmatch '^(127|169\.254)\.' } |
        Select-Object -First 1 -ExpandProperty IPAddress
}
if (-not $LanAddress) {
    throw 'No Wi-Fi LAN IPv4 address was found. Pass -LanAddress with the host computer IPv4 address.'
}

$env:LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED = 'true'
$env:LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT = $PSScriptRoot
$env:LABEL_STUDIO_HOST = "http://${LanAddress}:8081"

Write-Host "Label Studio LAN address: $env:LABEL_STUDIO_HOST"
& (Join-Path $PSScriptRoot '.venv\Scripts\label-studio.exe') start --port 8081 --no-browser --host $env:LABEL_STUDIO_HOST
