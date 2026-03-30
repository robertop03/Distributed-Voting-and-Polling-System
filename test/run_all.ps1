$ErrorActionPreference = "Stop"

try {
    & "$PSScriptRoot\01_basic_replication.ps1"
    & "$PSScriptRoot\02_eventual_consistency.ps1"
    & "$PSScriptRoot\03_failure_detector.ps1"
    & "$PSScriptRoot\04_crash_recovery.ps1"

    Write-Host "`nAll tests completed." -ForegroundColor Green
}
catch {
    Write-Host "`n[FAIL] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}