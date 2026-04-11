. "$PSScriptRoot/common.ps1"

$poll = "test_recovery"
$ErrorActionPreference = "Stop"

try {
    Print-Step "Submit votes"

    Vote 1 $poll "A" | Out-Null
    Vote 2 $poll "B" | Out-Null
    Vote 1 $poll "A" | Out-Null

    Wait-UntilAllNodesPollCounts @(1, 2, 3) $poll 2 1 30 | Out-Null

    Print-Step "Stop node1 and node2"
    docker compose -f docker-compose.generated.yml stop node1 node2 | Out-Null

    Print-Step "Restart node3"
    docker compose -f docker-compose.generated.yml restart node3 | Out-Null

    Print-Step "Wait for node3 direct readiness after restart"
    Wait-HttpReadyDirect 3 45

    Print-Step "Query node3 (isolated)"
    $r = Get-Poll 3 $poll
    $r

    $a = Get-CountValue $r.counts "A"
    $b = Get-CountValue $r.counts "B"

    if ($a -eq 2 -and $b -eq 1) {
        Print-Ok "Local crash recovery works (no peers)"
    } else {
        throw "Recovery failed: node3 has A=$a B=$b instead of A=2 B=1"
    }
}
finally {
    Print-Step "Restore full cluster"
    docker compose -f docker-compose.generated.yml start node1 node2 | Out-Null

    Wait-HttpReadyDirect 1 45
    Wait-HttpReadyDirect 2 45
    Wait-HttpReadyDirect 3 45

    Print-Ok "Cluster restored after crash recovery test"
}