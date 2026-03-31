. "$PSScriptRoot/common.ps1"
$ErrorActionPreference = "Stop"
docker compose down -v
docker compose up -d --build

Wait-HttpReady 8001
Wait-HttpReady 8002
Wait-HttpReady 8003

Write-Host "Ensure isolated network exists"
docker network inspect ds_isolated *> $null
if ($LASTEXITCODE -ne 0) {
    docker network create ds_isolated | Out-Null
}

try {
    & "$PSScriptRoot\01_basic_replication.ps1"
    & "$PSScriptRoot\02_eventual_consistency.ps1"
    & "$PSScriptRoot\03_failure_detector.ps1"
    & "$PSScriptRoot\04_crash_recovery.ps1"
    & "$PSScriptRoot\05_idempotent_internal_update.ps1"
    & "$PSScriptRoot\06_concurrent_updates_convergence.ps1"
    & "$PSScriptRoot\07_network_partition_healing.ps1"

    Write-Host "`nAll tests completed." -ForegroundColor Green
}
catch {
    Write-Host "`n[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}