. "$PSScriptRoot/common.ps1"

$ErrorActionPreference = "Stop"

Print-Step "Failure detector test"

Print-Step "Stopping node2..."
docker compose -f docker-compose.generated.yml stop node2 | Out-Null

Print-Step "Waiting for node1 to mark node2 as SUSPECT or DEAD..."
$downDetected = Wait-ForPeerState `
    -observerUrl "http://localhost:8001" `
    -peerName "node2" `
    -expectedStates @("SUSPECT", "DEAD") `
    -timeoutSec 25 `
    -intervalSec 1

if (-not $downDetected) {
    Write-Error "[FAIL] node1 did not mark node2 as SUSPECT/DEAD within timeout"
    exit 1
}

Print-Step "Restarting node2..."
docker compose -f docker-compose.generated.yml start node2 | Out-Null

Print-Step "Waiting for node1 to mark node2 as ALIVE again..."
$aliveDetected = Wait-ForPeerState `
    -observerUrl "http://localhost:8001" `
    -peerName "node2" `
    -expectedStates @("ALIVE") `
    -timeoutSec 30 `
    -intervalSec 1

if (-not $aliveDetected) {
    Write-Error "[FAIL] node1 did not mark node2 as ALIVE again within timeout"
    exit 1
}

Print-Ok "Failure detector correctly observed node2 down and up again."
exit 0