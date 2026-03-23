. "$PSScriptRoot/common.ps1"

Print-Step "Stop node2"
docker compose stop node2

Wait-Seconds 5

Print-Step "Check status from node1"
Invoke-RestMethod http://localhost:8001/status

Print-Step "Restart node2"
docker compose start node2

Wait-Seconds 5

Print-Step "Check recovery"
Invoke-RestMethod http://localhost:8001/status

Print-Ok "Failure detector tested"