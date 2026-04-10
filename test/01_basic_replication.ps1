. "$PSScriptRoot/common.ps1"

$poll = "test_basic"
$ErrorActionPreference = "Stop"

Print-Step "Submit votes"

Vote 1 $poll "A" | Out-Null
Vote 2 $poll "B" | Out-Null
Vote 1 $poll "A" | Out-Null

Print-Step "Wait for convergence on all nodes"
$snapshots = Wait-UntilAllNodesPollCounts @(1, 2, 3) $poll 2 1 30

Print-Step "Final responses"
$snapshots.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{
        node = "$($_.Key)"
        response = $_.Value
    }
} | ConvertTo-Json -Depth 10

$r1 = $snapshots[1]
$r2 = $snapshots[2]
$r3 = $snapshots[3]

$a1 = Get-CountValue $r1.counts "A"
$b1 = Get-CountValue $r1.counts "B"
$a2 = Get-CountValue $r2.counts "A"
$b2 = Get-CountValue $r2.counts "B"
$a3 = Get-CountValue $r3.counts "A"
$b3 = Get-CountValue $r3.counts "B"

if ($a1 -eq 2 -and $b1 -eq 1 `
 -and $a2 -eq 2 -and $b2 -eq 1 `
 -and $a3 -eq 2 -and $b3 -eq 1) {
    Print-Ok "Replication works"
} else {
    throw "Replication failed: node1(A=$a1,B=$b1), node2(A=$a2,B=$b2), node3(A=$a3,B=$b3)"
}