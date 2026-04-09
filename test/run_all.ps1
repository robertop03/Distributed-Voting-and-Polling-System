. "$PSScriptRoot/common.ps1"
$ErrorActionPreference = "Stop"

Wait-HttpReady 8001
Wait-HttpReady 8002
Wait-HttpReady 8003

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