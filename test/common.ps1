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

function Get-Status_With-URL($url) {
    return Invoke-RestMethod -Uri "$url/status" -Method Get
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

function Get-PeerState($statusObj, $peerName) {
    foreach ($p in $statusObj.peers) {
        if ($p.peer -like "*$peerName*") {
            return $p.state
        }
    }
    return $null
}

function Wait-ForPeerState($observerUrl, $peerName, $expectedStates, $timeoutSec = 20, $intervalSec = 1) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)

    while ((Get-Date) -lt $deadline) {
        try {
            $status = Get-Status_With-URL $observerUrl
            $state = Get-PeerState $status $peerName
            Write-Host "[INFO] Observed state for $peerName from $observerUrl => $state"

            if ($null -ne $state -and $expectedStates -contains $state) {
                return $true
            }
        } catch {
            Write-Host "[WARN] Failed to query $observerUrl/status : $_"
        }

        Start-Sleep -Seconds $intervalSec
    }

    return $false
}

function Post-InternalUpdate($port, $updateObj) {
    Invoke-RestMethod -Method POST "http://localhost:$port/internal/counter/update" `
        -ContentType "application/json" `
        -Body ($updateObj | ConvertTo-Json)
}

function Get-CountsAB($port, $poll) {
    $r = Get-Poll $port $poll
    return [PSCustomObject]@{
        A = Get-CountValue $r.counts "A"
        B = Get-CountValue $r.counts "B"
        Raw = $r
    }
}

function Wait-HttpReady($port, $timeoutSec = 30) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)

    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-RestMethod -Method GET "http://localhost:$port/status" -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Service on port $port did not become ready within $timeoutSec seconds"
}

function Import-Env {
    param(
        [string]$Path = ".env"
    )

    if (-not (Test-Path $Path)) {
        Write-Warning ".env file not found at $Path"
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()

        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        if ($line -notmatch "=") { return }

        $key, $value = $line -split "=", 2
        $key = $key.Trim()
        $value = $value.Trim()

        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}