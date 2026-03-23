. "$PSScriptRoot/common.ps1"

$poll = "test_eventual"

Print-Step "Stop node3"
docker compose stop node3

Print-Step "Send votes while node3 is down"
Vote 8001 $poll "A"
Vote 8002 $poll "B"
Vote 8001 $poll "A"

Print-Step "Restart node3"
docker compose start node3

Print-Step "Wait for convergence on all nodes"
$snapshots = Wait-UntilAllNodesPollCounts @(8001, 8002, 8003) $poll 2 1 45

$snapshots.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{
        port = "$($_.Key)"
        response = $_.Value
    }
} | ConvertTo-Json -Depth 10

Print-Ok "Eventual consistency after rejoin works"