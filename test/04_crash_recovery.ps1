. "$PSScriptRoot/common.ps1"

$poll = "test_recovery"

Print-Step "Submit votes"

Vote 8001 $poll "A"
Vote 8002 $poll "B"
Vote 8001 $poll "A"

Wait-Seconds 5

Print-Step "Ensure node3 has data"
$r = Get-Poll 8003 $poll
$r

Print-Step "Stop node1 and node2"
docker compose stop node1 node2

Print-Step "Restart node3"
docker compose restart node3

Wait-Seconds 4

Print-Step "Query node3 (isolated)"

$r = Get-Poll 8003 $poll
$r

if ($r.counts.A -eq 2 -and $r.counts.B -eq 1) {
    Print-Ok "Local crash recovery works (no peers)"
} else {
    throw "Recovery failed"
}

Print-Step "Restart cluster"
docker compose start node1 node2