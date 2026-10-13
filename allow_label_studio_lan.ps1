$ErrorActionPreference = 'Stop'

$ruleName = 'CampNet Label Studio LAN 8081'
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort 8081 -RemoteAddress LocalSubnet -Profile Public,Private
}
