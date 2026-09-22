<#
Runs one configuration (one model x one arrival rate) three times, open-loop.
Run on the LOAD GENERATOR machine, from the repo root:

  .\jmeter\run_load.ps1 -SutHost 192.168.1.50 -RatePerMin 4 -Minutes 10
  .\jmeter\run_load.ps1 -SutHost 192.168.1.50 -RatePerMin 4 -Minutes 10 -SearchPerMin 30 -StatsPerMin 2   # mixed load
  .\jmeter\run_load.ps1 -SutHost 192.168.1.50 -Kind stress -Schedule "rate(2/min) random_arrivals(5 min) rate(2/min) rate(4/min) random_arrivals(5 min) rate(4/min)" -Runs 1

Each run: empties the store (service starts empty), runs JMeter, writes
results/<kind>/<model>/<config>/run<k>.jtl and run<k>.meta.json, then cools down.
The model under test is read from GET /health so the folder name cannot be wrong.
#>
param(
  [Parameter(Mandatory)] [string]$SutHost,
  [int]$Port = 8000,
  [double]$RatePerMin = 0,
  [int]$Minutes = 10,
  [double]$SearchPerMin = 0,
  [double]$StatsPerMin = 0,
  [int]$Runs = 3,
  [string]$Kind = "load",
  [string]$Schedule = "",
  [int]$CooldownSec = 60,
  [string]$JMeter = "jmeter"
)
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
$base = "http://${SutHost}:${Port}"
$model = (Invoke-RestMethod "$base/health").model
$modelSlug = ($model -replace '[^A-Za-z0-9.]+', '-')

if (-not $Schedule) {
  if ($RatePerMin -le 0) { throw "give -RatePerMin or -Schedule" }
  $Schedule = "rate($RatePerMin/min) random_arrivals($Minutes min) rate($RatePerMin/min)"
  $config = "rate-$RatePerMin"
} else { $config = "custom-" + (Get-Date -Format "yyyyMMdd-HHmm") }
if ($SearchPerMin -gt 0) { $config += "_search-$SearchPerMin" }
$searchSched = if ($SearchPerMin -gt 0) { "rate($SearchPerMin/min) random_arrivals($Minutes min) rate($SearchPerMin/min)" } else { "pause(1 s)" }
$statsSched  = if ($StatsPerMin  -gt 0) { "rate($StatsPerMin/min) random_arrivals($Minutes min) rate($StatsPerMin/min)" } else { "pause(1 s)" }

$outDir = Join-Path $repo "results\$Kind\$modelSlug\$config"
New-Item -ItemType Directory -Force $outDir | Out-Null

for ($k = 1; $k -le $Runs; $k++) {
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $runId = "${Kind}__${modelSlug}__${config}__run${k}__${stamp}"
  $jtl = Join-Path $outDir "run$k.jtl"
  if (Test-Path $jtl) { throw "$jtl exists - refusing to overwrite a kept result" }

  Invoke-RestMethod -Method Delete "$base/tickets" -Headers @{ "X-Run-Id" = "${runId}__reset" } | Out-Null
  Write-Host "[$runId] schedule: $Schedule"
  $start = Get-Date
  & $JMeter -n -t (Join-Path $repo "jmeter\triage.jmx") -q (Join-Path $repo "jmeter\triage.properties") `
      "-Jhost=$SutHost" "-Jport=$Port" "-Jrun_id=$runId" `
      "-Jtickets=$(Join-Path $repo 'jmeter\data\tickets.tsv')" "-Jsearch_terms=$(Join-Path $repo 'jmeter\data\search_terms.csv')" `
      "-Jschedule=$Schedule" "-Jsearch_schedule=$searchSched" "-Jstats_schedule=$statsSched" "-Jseed=$(3113 + $k)" `
      -l $jtl -j (Join-Path $outDir "run$k.jmeter.log")
  if ($LASTEXITCODE -ne 0) { throw "jmeter exited with $LASTEXITCODE" }

  @{ run_id = $runId; kind = $Kind; model = $model; config = $config; run = $k; sut = $base
     schedule = $Schedule; search_schedule = $searchSched; stats_schedule = $statsSched
     started = $start.ToString("o"); finished = (Get-Date).ToString("o")
     loadgen_host = $env:COMPUTERNAME } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $outDir "run$k.meta.json")
  if ($k -lt $Runs) { Write-Host "cooldown ${CooldownSec}s"; Start-Sleep $CooldownSec }
}
Write-Host "done -> $outDir"
