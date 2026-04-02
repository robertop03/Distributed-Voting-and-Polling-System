. "$PSScriptRoot/common.ps1"

$ErrorActionPreference = "Stop"

$isolatedNet = "ds_isolated"
$pollId = "test_partition"

function Get-Poll-InContainer($container, $poll) {
    $cmd = @"
import json
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

# Recupera l'ID reale del container node3 dal compose generato
$container = (docker compose -f docker-compose.generated.yml ps -q node3).Trim()

if (-not $container) {
    throw "Could not find container for node3 in docker-compose.generated.yml"
}

# Ricava dinamicamente la rete principale del container
$inspectObject = docker inspect $container | ConvertFrom-Json
$mainNet = $inspectObject.NetworkSettings.Networks.PSObject.Properties.Name |
    Where-Object { $_ -ne $isolatedNet } |
    Select-Object -First 1

if (-not $mainNet) {
    throw "Could not determine main network for node3"
}

# Crea la rete isolata se non esiste
docker network inspect $isolatedNet *> $null
if ($LASTEXITCODE -ne 0) {
    docker network create $isolatedNet | Out-Null
}

Print-Step "Main network: $mainNet"
Print-Step "Isolated network: $isolatedNet"
Print-Step "Container: $container"

# Stato iniziale: tutti i nodi allineati
$postBody = @{ poll_id = $pollId; option = "A" } | ConvertTo-Json
Invoke-RestMethod -Method POST "http://localhost:8001/vote" `
    -ContentType "application/json" `
    -Body $postBody `
    -TimeoutSec 3 | Out-Null

Wait-UntilAllNodesPollCounts @(8001, 8002, 8003) $pollId 1 0 20 | Out-Null

# Isola node3 dalla rete principale
docker network disconnect $mainNet $container | Out-Null
docker network connect $isolatedNet $container | Out-Null

Print-Step "node3 isolated from main cluster"

# Durante la partizione, i nodi 1 e 2 continuano a lavorare
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

# node3 dovrebbe essere disallineato durante la partizione
# node1 lo leggiamo dal host, node3 dall'interno del container
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

# Heal partition
docker network disconnect $isolatedNet $container | Out-Null
docker network connect $mainNet $container | Out-Null

Print-Step "node3 reconnected to main cluster"

# Attendi che la porta esposta torni raggiungibile dal host
Wait-HttpReady 8003 20

# Attendi anti-entropy / convergenza
Wait-UntilAllNodesPollCounts @(8001, 8002, 8003) $pollId 2 1 25 | Out-Null

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
    throw "Nodes did not converge after healing partition"
}

Print-Ok "PASS: partition created, divergence observed, and convergence restored after healing"