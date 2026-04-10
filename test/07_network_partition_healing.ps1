. "$PSScriptRoot/common.ps1"

$ErrorActionPreference = "Stop"

$isolatedNet = "ds_isolated"
$pollId = "test_partition"

function Get-Poll-InContainer($container, $poll) {
    $cmd = @"
import urllib.request
url = 'http://127.0.0.1:8003/poll/$poll'
with urllib.request.urlopen(url, timeout=3) as r:
    print(r.read().decode('utf-8'))
"@

    $json = docker exec $container python -c $cmd
    if (-not $json) {
        throw "Failed to read poll '$poll' from inside container $container"
    }

    return $json | ConvertFrom-Json
}

Print-Step "network partition + healing test"

$container = (docker compose -f docker-compose.generated.yml ps -q node3).Trim()

if (-not $container) {
    throw "Could not find container for node3 in docker-compose.generated.yml"
}

$inspectObject = docker inspect $container | ConvertFrom-Json
$mainNet = $inspectObject.NetworkSettings.Networks.PSObject.Properties.Name |
    Where-Object { $_ -ne $isolatedNet } |
    Select-Object -First 1

if (-not $mainNet) {
    throw "Could not determine main network for node3"
}

docker network inspect $isolatedNet *> $null
if ($LASTEXITCODE -ne 0) {
    docker network create ds_isolated | Out-Null
}

try {
    Print-Step "Main network: $mainNet"
    Print-Step "Isolated network: $isolatedNet"
    Print-Step "Container: $container"

    $postBody = @{ poll_id = $pollId; option = "A" } | ConvertTo-Json
    Invoke-RestMethod -Method POST "http://localhost:8001/vote" `
        -ContentType "application/json" `
        -Body $postBody `
        -TimeoutSec 3 | Out-Null

    Wait-UntilAllNodesPollCounts @(1, 2, 3) $pollId 1 0 20 | Out-Null

    docker network disconnect $mainNet $container | Out-Null
    docker network connect --alias node3 $isolatedNet $container | Out-Null

    Print-Step "node3 isolated from main cluster"

    $postBody1 = @{ poll_id = $pollId; option = "A" } | ConvertTo-Json
    $postBody2 = @{ poll_id = $pollId; option = "B" } | ConvertTo-Json

    Invoke-RestMethod -Method POST "http://localhost:8001/vote" `
        -ContentType "application/json" `
        -Body $postBody1 `
        -TimeoutSec 3 | Out-Null

    Invoke-RestMethod -Method POST "http://localhost:8002/vote" `
        -ContentType "application/json" `
        -Body $postBody2 `
        -TimeoutSec 3 | Out-Null

    Start-Sleep -Seconds 2

    $r1 = Invoke-RestMethod "http://localhost:8001/poll/$pollId" -TimeoutSec 3
    $r3 = Get-Poll-InContainer $container $pollId

    $c1_before = $r1.counts | ConvertTo-Json -Compress
    $c3_before = $r3.counts | ConvertTo-Json -Compress

    Print-Step "Before healing:"
    Print-Step "node1 counts = $c1_before"
    Print-Step "node3 counts = $c3_before"

    if ($c1_before -eq $c3_before) {
        throw "Expected node3 to be temporarily inconsistent during partition"
    }

    docker network disconnect $isolatedNet $container | Out-Null
    docker network connect --alias node3 $mainNet $container | Out-Null

    Print-Step "node3 reconnected to main cluster"

    Wait-HttpReadyDirect 3 30

    Wait-UntilAllNodesPollCounts @(1, 2, 3) $pollId 2 1 25 | Out-Null

    $r1_after = Invoke-RestMethod "http://localhost:8001/poll/$pollId" -TimeoutSec 3
    $r2_after = Invoke-RestMethod "http://localhost:8002/poll/$pollId" -TimeoutSec 3
    $r3_after = Invoke-RestMethod "http://localhost:8003/poll/$pollId" -TimeoutSec 3

    $c1 = $r1_after.counts | ConvertTo-Json -Compress
    $c2 = $r2_after.counts | ConvertTo-Json -Compress
    $c3 = $r3_after.counts | ConvertTo-Json -Compress

    Print-Step "After healing:"
    Print-Step "node1 counts = $c1"
    Print-Step "node2 counts = $c2"
    Print-Step "node3 counts = $c3"

    if ($c1 -ne $c2 -or $c2 -ne $c3) {
        throw "Replicas did not converge after healing"
    }

    Print-Ok "Temporary disconnection healed correctly"
}
finally {
    $inspectObject = docker inspect $container | ConvertFrom-Json
    $currentNetworks = @($inspectObject[0].NetworkSettings.Networks.PSObject.Properties.Name)

    $oldPref = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    if ($currentNetworks -contains $isolatedNet) {
        docker network disconnect $isolatedNet $container 2>$null | Out-Null
    }

    if (-not ($currentNetworks -contains $mainNet)) {
        docker network connect --alias node3 $mainNet $container 2>$null | Out-Null
    }

    $ErrorActionPreference = $oldPref

    Wait-HttpReadyDirect 3 45
}