. "$PSScriptRoot/common.ps1"

$ErrorActionPreference = "Stop"

try {
    Print-Step "Failure detector test"

    Print-Step "Stopping node2..."
    docker compose -f docker-compose.generated.yml stop node2 | Out-Null

    Print-Step "Waiting for node1 to mark node2 as SUSPECT or DEAD..."
    $downDetected = Wait-ForPeerState `
        -observerUrl (Get-DirectNodeUrl 1) `
        -peerName "node2" `
        -expectedStates @("SUSPECT", "DEAD") `
        -timeoutSec 25 `
        -intervalSec 1

    if (-not $downDetected) {
        throw "[FAIL] node1 did not mark node2 as SUSPECT/DEAD within timeout"
    }

    Print-Step "Restarting node2..."
    docker compose -f docker-compose.generated.yml start node2 | Out-Null
    Wait-HttpReadyDirect 2 45

    Print-Step "Waiting for node1 to mark node2 as ALIVE again..."
    $aliveDetected = Wait-ForPeerState `
        -observerUrl (Get-DirectNodeUrl 1) `
        -peerName "node2" `
        -expectedStates @("ALIVE") `
        -timeoutSec 30 `
        -intervalSec 1

    if (-not $aliveDetected) {
        throw "[FAIL] node1 did not mark node2 as ALIVE again within timeout"
    }

    Print-Ok "Failure detector correctly observed node2 down and up again."
}
finally {
    docker compose -f docker-compose.generated.yml start node2 | Out-Null
    Wait-HttpReadyDirect 2 45
}