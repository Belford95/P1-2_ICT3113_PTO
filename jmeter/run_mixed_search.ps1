# run_mixed_search.ps1
# R2 mixed-load search test.
# Requires >=1000 tickets already stored.
# Does NOT clear the ticket store.

param(
  [Parameter(Mandatory)] [string]$SutHost,
  [int]$Port = 8000,
  [double]$RatePerMin = 2,
  [double]$SearchPerMin = 4,
  [int]$Minutes = 30,
  [int]$Runs = 3,
  [int]$CooldownSec = 60,
  [string]$JMeter = "jmeter"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$base = "http://${SutHost}:${Port}"

$model = (Invoke-RestMethod "$base/health").model
$modelSlug = ($model -replace '[^A-Za-z0-9.]+', '-')

$stats = Invoke-RestMethod "$base/stats"
if ($stats.total -lt 1000) {
    throw "R2 requires >=1000 stored tickets; found $($stats.total)"
}

$schedule = "rate($RatePerMin/min) random_arrivals($Minutes min) rate($RatePerMin/min)"
$searchSched = "rate($SearchPerMin/min) random_arrivals($Minutes min) rate($SearchPerMin/min)"
$config = "rate-$RatePerMin`_search-$SearchPerMin"

$outDir = Join-Path $repo "results\search\$modelSlug\$config"
New-Item -ItemType Directory -Force $outDir | Out-Null

for ($k = 1; $k -le $Runs; $k++) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $runId = "search__${modelSlug}__${config}__run${k}__${stamp}"
    $jtl = Join-Path $outDir "run$k.jtl"

    if (Test-Path $jtl) {
        throw "$jtl exists - refusing to overwrite a kept result"
    }

    Write-Host "[$runId] POST=$RatePerMin/min SEARCH=$SearchPerMin/min"

    $start = Get-Date

    & $JMeter -n `
        -t (Join-Path $repo "jmeter\triage.jmx") `
        -q (Join-Path $repo "jmeter\triage.properties") `
        "-Jhost=$SutHost" `
        "-Jport=$Port" `
        "-Jrun_id=$runId" `
        "-Jtickets=$(Join-Path $repo 'jmeter\data\tickets.tsv')" `
        "-Jsearch_terms=$(Join-Path $repo 'jmeter\data\search_terms.csv')" `
        "-Jschedule=$schedule" `
        "-Jsearch_schedule=$searchSched" `
        "-Jstats_schedule=pause(1 s)" `
        "-Jseed=$(3113 + $k)" `
        -l $jtl `
        -j (Join-Path $outDir "run$k.jmeter.log")

    if ($LASTEXITCODE -ne 0) {
        throw "jmeter exited with $LASTEXITCODE"
    }

    @{
        run_id = $runId
        kind = "search"
        model = $model
        config = $config
        run = $k
        sut = $base
        schedule = $schedule
        search_schedule = $searchSched
        started = $start.ToString("o")
        finished = (Get-Date).ToString("o")
        loadgen_host = $env:COMPUTERNAME
    } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $outDir "run$k.meta.json")

    if ($k -lt $Runs) {
        Write-Host "cooldown ${CooldownSec}s"
        Start-Sleep $CooldownSec
    }
}

Write-Host "done -> $outDir"