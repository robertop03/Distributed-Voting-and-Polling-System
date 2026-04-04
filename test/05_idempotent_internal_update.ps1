. "$PSScriptRoot/common.ps1"

$poll = "test_idempotent"
$ErrorActionPreference = "Stop"
$headers = @{}

if ($env:INTERNAL_TOKEN) {
    $headers["X-Internal-Token"] = $env:INTERNAL_TOKEN
}

Print-Step "Create one vote on node1"
$voteResp = Vote 8001 $poll "A"
$upd = $voteResp.update

Print-Step "Replay the same internal update twice on node2"
Invoke-RestMethod -Method POST "http://localhost:8002/internal/counter/update" `
    -ContentType "application/json" `
    -Headers $headers `
    -Body ($upd | ConvertTo-Json)

Invoke-RestMethod -Method POST "http://localhost:8002/internal/counter/update" `
    -ContentType "application/json" `
    -Headers $headers `
    -Body ($upd | ConvertTo-Json)

Print-Step "Wait for all nodes to converge to A=1, B=0"
$snapshots = Wait-UntilAllNodesPollCounts @(8001, 8002, 8003) $poll 1 0 30

$snapshots.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{
        port = "$($_.Key)"
        response = $_.Value
    }
} | ConvertTo-Json -Depth 10

Print-Ok "Duplicate internal update is idempotent"