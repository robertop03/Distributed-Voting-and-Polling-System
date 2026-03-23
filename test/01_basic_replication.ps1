. "$PSScriptRoot/common.ps1"

$poll = "test_basic"

Print-Step "Submit votes"

Vote 8001 $poll "A"
Vote 8002 $poll "B"
Vote 8001 $poll "A"

Wait-Seconds 5

Print-Step "Check convergence"

$r1 = Get-Poll 8001 $poll
$r2 = Get-Poll 8002 $poll
$r3 = Get-Poll 8003 $poll

$r1
$r2
$r3

if ($r1.counts.A -eq 2 -and $r1.counts.B -eq 1 `
 -and $r2.counts.A -eq 2 -and $r2.counts.B -eq 1 `
 -and $r3.counts.A -eq 2 -and $r3.counts.B -eq 1) {
    Print-Ok "Replication works"
} else {
    throw "Replication failed"
}