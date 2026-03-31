. "$PSScriptRoot/common.ps1"

$poll = "test_concurrent"
$ErrorActionPreference = "Stop"

Print-Step "Send concurrent votes from multiple nodes"

$jobs = @()
$jobs += Start-Job -ScriptBlock {
    Invoke-RestMethod -Method POST "http://localhost:8001/vote" `
        -ContentType "application/json" `
        -Body '{"poll_id":"test_concurrent","option":"A"}'
}
$jobs += Start-Job -ScriptBlock {
    Invoke-RestMethod -Method POST "http://localhost:8002/vote" `
        -ContentType "application/json" `
        -Body '{"poll_id":"test_concurrent","option":"A"}'
}
$jobs += Start-Job -ScriptBlock {
    Invoke-RestMethod -Method POST "http://localhost:8003/vote" `
        -ContentType "application/json" `
        -Body '{"poll_id":"test_concurrent","option":"B"}'
}
$jobs += Start-Job -ScriptBlock {
    Invoke-RestMethod -Method POST "http://localhost:8001/vote" `
        -ContentType "application/json" `
        -Body '{"poll_id":"test_concurrent","option":"A"}'
}
$jobs += Start-Job -ScriptBlock {
    Invoke-RestMethod -Method POST "http://localhost:8002/vote" `
        -ContentType "application/json" `
        -Body '{"poll_id":"test_concurrent","option":"B"}'
}

$jobs | Wait-Job | Receive-Job | Out-Null
$jobs | Remove-Job

Print-Step "Wait for convergence on all nodes"
$snapshots = Wait-UntilAllNodesPollCounts @(8001, 8002, 8003) $poll 3 2 45

$snapshots.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{
        port = "$($_.Key)"
        response = $_.Value
    }
} | ConvertTo-Json -Depth 10

Print-Ok "Concurrent updates converge correctly"