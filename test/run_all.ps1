. "$PSScriptRoot/common.ps1"
$ErrorActionPreference = "Stop"

function Ensure-ClusterRunning {
    param([int]$Nodes = 3)

    $projectRoot = Split-Path $PSScriptRoot -Parent
    $composeFile = Join-Path $projectRoot "docker-compose.generated.yml"

    if (-not (Test-Path $composeFile)) {
        Push-Location $projectRoot
        try {
            $pythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
            & $pythonCmd "./run_cluster.py" $Nodes
        } finally {
            Pop-Location
        }
        return
    }

    $runningServices = @()
    try {
        $runningServices = @(docker compose -f $composeFile ps --services --status running)
    } catch {
        $runningServices = @()
    }

    $expectedMin = $Nodes + 1  # proxy + nodes

    if ($runningServices.Count -lt $expectedMin) {
        Push-Location $projectRoot
        try {
            docker compose -f $composeFile up -d --build | Out-Null
        } finally {
            Pop-Location
        }
    }
}

Ensure-ClusterRunning 3

Wait-HttpReadyDirect 1 45
Wait-HttpReadyDirect 2 45
Wait-HttpReadyDirect 3 45

Import-Env

Write-Host "Ensure isolated network exists"
$oldPref = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker network inspect ds_isolated 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker network create ds_isolated | Out-Null
}
$ErrorActionPreference = $oldPref

try {
    & "$PSScriptRoot\01_basic_replication.ps1"
    & "$PSScriptRoot\02_eventual_consistency.ps1"
    & "$PSScriptRoot\03_failure_detector.ps1"
    & "$PSScriptRoot\04_crash_recovery.ps1"
    & "$PSScriptRoot\05_idempotent_internal_update.ps1"
    & "$PSScriptRoot\06_concurrent_updates_convergence.ps1"
    & "$PSScriptRoot\07_network_partition_healing.ps1"

    Write-Host "`nAll tests completed." -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "`n[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
