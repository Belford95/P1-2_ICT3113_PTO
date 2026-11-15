<#
Assignment 2 open-loop speed run on the separate JMeter laptop.
Run ONE run at a time so Belford can restart Ollama and warm up the current
configuration before EACH run. Never run this until he confirms readiness.

From repository root (example ONLY; replace host and measured S):
  .\jmeter\run_a2_speed.ps1 -SutHost 192.168.1.50 -Config qwen -RunNumber 1 -SSeconds 4.18
  .\jmeter\run_a2_speed.ps1 -SutHost 192.168.1.50 -Config cascade1 -RunNumber 1 -SSeconds 4.18

S = median of three different typical ticket timings through POST /tickets
under the top-model-only configuration, after service warm-up. Keep this S,
rate and duration constant for EVERY model and cascade configuration.

This runner DOES NOT restart Ollama, warm up models, or switch cascade settings;
Belford must do those on the service host before EACH invocation.
It DOES NOT delete tickets or edit A1 files/results.
#>
param(
  [Parameter(Mandatory = $true)] [string]$SutHost,
  [int]$Port = 8000,
  [Parameter(Mandatory = $true)]
  [ValidateSet('qwen','cascade1','cascade2')] [string]$Config,
  [Parameter(Mandatory = $true)] [ValidateRange(1,3)] [int]$RunNumber,
  [Parameter(Mandatory = $true)] [ValidateRange(0.1,600)] [double]$SSeconds,
  [string]$JMeter = 'jmeter',
  [switch]$ConfirmedWarmup
)
$ErrorActionPreference = 'Stop'
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$repo = Split-Path $PSScriptRoot -Parent
$base = "http://${SutHost}:${Port}"
$tsv = Join-Path $PSScriptRoot 'data\a2_workload.tsv'
$jmx = Join-Path $PSScriptRoot 'triage_a2.jmx'
if (!(Test-Path $tsv) -or !(Test-Path $jmx)) { throw 'Missing A2 workload.tsv or triage_a2.jmx.' }
if (!$ConfirmedWarmup) {
  throw 'Belford must restart Ollama, send 3 service warm-ups, verify model(s) at context 2048, and confirm the correct config/setting. Re-run with -ConfirmedWarmup ONLY after this is done.'
}

# Assignment 2: 1 arrival / (2*S seconds); min 5 minutes, otherwise S minutes.
$rate = 30.0 / $SSeconds
$minutes = [Math]::Max(5.0, $SSeconds)
$timeoutSec = [Math]::Max(300, [Math]::Ceiling(10 * $SSeconds))
$pauseSec = $timeoutSec + 60
$rateText = $rate.ToString('0.######', $culture)
$minutesText = $minutes.ToString('0.######', $culture)
$schedule = "rate($rateText/min) random_arrivals($minutesText min) pause($pauseSec s)"
$timeoutMs = 1000 * $timeoutSec

# 80 tickets are enough only if the run will not exhaust them: random arrivals
# can exceed the mean; never silently cycle back to an already-seen prompt.
$ticketCount = @((Get-Content $tsv)).Count
$expected = $rate * $minutes
if ($expected -ge $ticketCount) {
  throw "Expected $([Math]::Round($expected,1)) arrivals but only $ticketCount distinct tickets. Expand A2 workload before running."
}
if ($expected -gt 0.80 * $ticketCount) {
  Write-Warning "Expected $([Math]::Round($expected,1)) arrivals from only $ticketCount unique tickets. Random arrivals may exhaust the feed; expand workload to reduce that risk. A2 JMX refuses to recycle."
}

# Config must be selected independently by Belford, not inferred from /health.
$health = Invoke-RestMethod "$base/health"
if ($health.status -ne 'ok') { throw "Service /health not OK: $($health | ConvertTo-Json -Compress)" }
if ($Config -eq 'qwen' -and $health.model -notmatch 'qwen') {
  Write-Warning "Health model is '$($health.model)'; verify service is in top-model-alone mode, not cascade mode."
}

$outDir = Join-Path $repo "results\a2\speed\$Config"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$jtl = Join-Path $outDir "run$RunNumber.jtl"
$metaFile = Join-Path $outDir "run$RunNumber.meta.json"
$logFile = Join-Path $outDir "run$RunNumber.jmeter.log"
foreach ($file in @($jtl, $metaFile, $logFile)) {
  if (Test-Path $file) { throw "Will not overwrite existing evidence: $file" }
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runId = "a2__speed__${Config}__run${RunNumber}__${stamp}"
$before = (Invoke-RestMethod "$base/stats").total
Write-Host "Run: $runId"
Write-Host "rate=$rateText/min, duration=$minutesText min, timeout=$timeoutSec sec, drain=$pauseSec sec, expected arrivals=$([Math]::Round($expected,1))"
Write-Host "stats before = $before; no /tickets reset will be performed"
$start = Get-Date
& $JMeter -n -t $jmx -q (Join-Path $PSScriptRoot 'triage.properties') `
  "-Jhost=$SutHost" "-Jport=$Port" "-Jrun_id=$runId" `
  "-Jtickets=$tsv" "-Jsearch_terms=$(Join-Path $PSScriptRoot 'data\search_terms.csv')" `
  "-Jschedule=$schedule" '-Jsearch_schedule=pause(1 s)' '-Jstats_schedule=pause(1 s)' `
  "-Jtimeout_ms=$timeoutMs" "-Jseed=$(3113 + $RunNumber)" `
  -l $jtl -j $logFile
$exitCode = $LASTEXITCODE
$end = Get-Date
$after = (Invoke-RestMethod "$base/stats").total
$record = [ordered]@{
  run_id = $runId; kind = 'a2_speed'; config = $Config; run = $RunNumber
  sut = $base; health_model = $health.model; S_seconds = $SSeconds
  rate_per_min = $rate; minutes = $minutes; timeout_ms = $timeoutMs
  drain_pause_sec = $pauseSec; expected_arrivals = $expected; distinct_tickets = $ticketCount
  schedule = $schedule; search_schedule = 'pause(1 s)'; stats_schedule = 'pause(1 s)'
  stats_before = $before; stats_after = $after; service_completed = ($after - $before)
  jmeter_exit_code = $exitCode; started = $start.ToString('o'); finished = $end.ToString('o')
  loadgen_host = $env:COMPUTERNAME
  note = 'Belford confirms restart, 3 warm-ups, context 2048 and selected config before invocation; see service logs for evidence.'
}
$record | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 $metaFile
if ($exitCode -ne 0) { throw "JMeter exited $exitCode. Saved metadata/logs; inspect $logFile" }
Write-Host "Done -> $outDir; service completed delta: $($after - $before)"
Write-Host 'Next: preserve service.jsonl for this run and reconcile JTL counts before interpreting results.'
