function Vote($port, $poll, $option) {
    Invoke-RestMethod -Method POST "http://localhost:$port/vote" `
        -ContentType "application/json" `
        -Body "{""poll_id"":""$poll"",""option"":""$option""}"
}

function Get-Poll($port, $poll) {
    Invoke-RestMethod "http://localhost:$port/poll/$poll"
}

function Get-Status($port) {
    Invoke-RestMethod "http://localhost:$port/status"
}

function Wait-Seconds($s) {
    Start-Sleep -Seconds $s
}

function Print-Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Print-Ok($msg) {
    Write-Host "[OK] $msg" -ForegroundColor Green
}

function Get-CountValue($counts, $key) {
    if ($null -eq $counts) {
        return 0
    }

    $prop = $counts.PSObject.Properties[$key]
    if ($null -eq $prop) {
        return 0
    }

    return [int]$prop.Value
}

function Wait-UntilPollCounts($port, $poll, $expectedA, $expectedB, $timeoutSec = 25) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    $last = $null

    while ((Get-Date) -lt $deadline) {
        try {
            $r = Get-Poll $port $poll
            $last = $r

            $a = Get-CountValue $r.counts "A"
            $b = Get-CountValue $r.counts "B"

            Write-Host "Waiting on port $port -> current counts: A=$a B=$b"

            if ($a -eq $expectedA -and $b -eq $expectedB) {
                return $r
            }
        }
        catch {
            Write-Host "Waiting on port $port -> node not reachable yet"
        }

        Start-Sleep -Seconds 1
    }

    if ($null -ne $last) {
        $lastJson = $last | ConvertTo-Json -Depth 10
        throw "Timeout waiting for poll '$poll' on port $port to reach A=$expectedA, B=$expectedB. Last response: $lastJson"
    }

    throw "Timeout waiting for poll '$poll' on port $port to reach A=$expectedA, B=$expectedB. No successful response received."
}

function Wait-UntilAllNodesPollCounts($ports, $poll, $expectedA, $expectedB, $timeoutSec = 40) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    $lastSnapshots = @{}

    while ((Get-Date) -lt $deadline) {
        $allOk = $true

        foreach ($port in $ports) {
            try {
                $r = Get-Poll $port $poll
                $lastSnapshots[$port] = $r

                $a = Get-CountValue $r.counts "A"
                $b = Get-CountValue $r.counts "B"

                Write-Host "Port $port -> A=$a B=$b"

                if ($a -ne $expectedA -or $b -ne $expectedB) {
                    $allOk = $false
                }
            }
            catch {
                Write-Host "Port $port -> not reachable yet"
                $allOk = $false
            }
        }

        if ($allOk) {
            return $lastSnapshots
        }

        Start-Sleep -Seconds 1
    }

    $snapshotsJson = $lastSnapshots | ConvertTo-Json -Depth 10
    throw "Timeout waiting for all nodes to reach A=$expectedA, B=$expectedB for poll '$poll'. Last snapshots: $snapshotsJson"
}