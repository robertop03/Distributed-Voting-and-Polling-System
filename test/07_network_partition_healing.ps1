. "$PSScriptRoot/common.ps1"

$poll = "test_partition"
$ErrorActionPreference = "Stop"

$mainNet = "progetto_ds_default"
$isolatedNet = "ds_isolated"
$container = "progetto_ds-node3"

Print-Step "Ensure isolated network exists"
docker network inspect $isolatedNet *> $null
if ($LASTEXITCODE -ne 0) {
    docker network create $isolatedNet | Out-Null
}

Print-Step "Isolate node3 from the main cluster network"
docker network disconnect $mainNet $container | Out-Null
docker network connect $isolatedNet $container | Out-Null

Print-Step "Send votes while node3 is partitioned"
Vote 8001 $poll "A" | Out-Null
Vote 8002 $poll "B" | Out-Null
Vote 8001 $poll "A" | Out-Null

Print-Step "Check node3 is stale during partition"
$r3_before = Get-Poll 8003 $poll
$r3_before | ConvertTo-Json -Depth 10

Print-Step "Heal partition: reconnect node3"
docker network disconnect $isolatedNet $container | Out-Null
docker network connect $mainNet $container | Out-Null

Print-Step "Wait for convergence after healing"
$snapshots = Wait-UntilAllNodesPollCounts @(8001, 8002, 8003) $poll 2 1 60

$snapshots.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{
        port = "$($_.Key)"
        response = $_.Value
    }
} | ConvertTo-Json -Depth 10

Print-Ok "Network partition healed and state converged"