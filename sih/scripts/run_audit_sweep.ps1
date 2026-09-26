param(
    [string]$BaseUrl = 'http://127.0.0.1:8080/api/v1',
    [string[]]$Scenarios = @('A', 'B', 'C', 'D', 'E', 'F', 'G'),
    [int]$Episodes = 10,
    [int]$DurationSteps = 2000,
    [long]$Seed = 42,
    [string]$OutputDir = (Join-Path $PSScriptRoot '..\audit-results')
)

$ErrorActionPreference = 'Stop'
$policies = @('baseline', 'random', 'ctmc', 'index', 'bandit', 'q_learning', 'dqn', 'ppo')
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

foreach ($scenario in $Scenarios) {
    $name = "audit-sweep-$scenario"
    $items = (Invoke-RestMethod "$BaseUrl/experiments").data.items
    $existing = $items | Where-Object { $_.name -eq $name } | Select-Object -First 1
    if ($null -eq $existing) {
        $body = @{ name = $name; scenario = $scenario; policies = $policies; episodes = $Episodes; seed = $Seed } | ConvertTo-Json
        $existing = (Invoke-RestMethod "$BaseUrl/experiments" -Method Post -ContentType 'application/json' -Body $body).data
        Write-Output "Created $name $($existing.id)"
    }

    $id = $existing.id
    $status = (Invoke-RestMethod "$BaseUrl/experiments/$id").data.status
    if ($status -eq 'completed') {
        Write-Output "Already completed $name $id"
        $result = (Invoke-RestMethod "$BaseUrl/experiments/$id/results").data
        $result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $OutputDir "results_$scenario.json") -Encoding UTF8
        continue
    }
    if ($status -ne 'running') {
        $body = @{ durationSteps = $DurationSteps } | ConvertTo-Json
        Invoke-RestMethod "$BaseUrl/experiments/$id/run" -Method Post -ContentType 'application/json' -Body $body | Out-Null
        Write-Output "Started $name $id"
    }

    while ($true) {
        Start-Sleep -Seconds 20
        $detail = (Invoke-RestMethod "$BaseUrl/experiments/$id").data
        $progress = $detail.progress
        Write-Output ("{0} {1} {2}/{3}" -f $name, $detail.status, $progress.completed_runs, $progress.total_runs)
        if ($detail.status -eq 'completed') { break }
        if ($detail.status -in @('failed', 'cancelled')) {
            throw "$name ended with status $($detail.status)"
        }
    }
    $result = (Invoke-RestMethod "$BaseUrl/experiments/$id/results").data
    $result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $OutputDir "results_$scenario.json") -Encoding UTF8
}
