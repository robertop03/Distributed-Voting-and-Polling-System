. "$PSScriptRoot/common.ps1"
$ErrorActionPreference = "Stop"

function Ensure-ClusterRunning {
    param([int]$Nodes = 3)

    $projectRoot = Split-Path $PSScriptRoot -Parent
    $composeFile = Join-Path $projectRoot "docker-compose.generated.yml"
    $pythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

    Push-Location $projectRoot
    try {
        if (Test-Path $composeFile) {
            docker compose -f $composeFile down -v --remove-orphans | Out-Null
        }

        Remove-Item -Force "docker-compose.generated.yml" -ErrorAction SilentlyContinue
        Remove-Item -Force "nginx.conf" -ErrorAction SilentlyContinue

        & $pythonCmd "./run_cluster.py" $Nodes "--expose-nodes"
    } finally {
        Pop-Location
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