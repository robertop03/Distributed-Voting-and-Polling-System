. "$PSScriptRoot/common.ps1"

$poll = "test_eventual"
$ErrorActionPreference = "Stop"

try {
    Print-Step "Stop node3"
    docker compose -f docker-compose.generated.yml stop node3 | Out-Null

    Print-Step "Send votes while node3 is down"
    Vote 1 $poll "A" | Out-Null
    Vote 2 $poll "B" | Out-Null
    Vote 1 $poll "A" | Out-Null

    Print-Step "Restart node3"
    docker compose -f docker-compose.generated.yml start node3 | Out-Null
    Wait-HttpReadyDirect 3 45

    Print-Step "Wait for convergence on all nodes"
    $snapshots = Wait-UntilAllNodesPollCounts @(1, 2, 3) $poll 2 1 45

    $snapshots.GetEnumerator() | ForEach-Object {
        [PSCustomObject]@{
            node = "$($_.Key)"
            response = $_.Value
        }
    } | ConvertTo-Json -Depth 10

    Print-Ok "Eventual consistency after rejoin works"
}
finally {
    docker compose -f docker-compose.generated.yml start node3 | Out-Null
    Wait-HttpReadyDirect 3 45
}