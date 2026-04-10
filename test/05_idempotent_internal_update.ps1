. "$PSScriptRoot/common.ps1"

$poll = "test_idempotent"
$ErrorActionPreference = "Stop"
$headers = @{}

if ($env:INTERNAL_TOKEN) {
    $headers["X-Internal-Token"] = $env:INTERNAL_TOKEN
}

Wait-HttpReadyDirect 1 45
Wait-HttpReadyDirect 2 45
Wait-HttpReadyDirect 3 45

Print-Step "Create one vote on node1"
$voteResp = Vote 1 $poll "A"
$upd = $voteResp.update

Print-Step "Replay the same internal update twice on node2"
Post-InternalUpdate 8002 $upd $headers | Out-Null
Post-InternalUpdate 8002 $upd $headers | Out-Null

Print-Step "Wait for all nodes to converge to A=1, B=0"
$snapshots = Wait-UntilAllNodesPollCounts @(1, 2, 3) $poll 1 0 30

$snapshots.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{
        node = "$($_.Key)"
        response = $_.Value
    }
} | ConvertTo-Json -Depth 10

Print-Ok "Duplicate internal update is idempotent"