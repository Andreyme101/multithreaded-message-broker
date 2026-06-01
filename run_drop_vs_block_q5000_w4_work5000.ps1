$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\andre\source\repos\diplom"

$BrokerExe   = Join-Path $ProjectRoot "build\Debug\broker.exe"
$ProducerExe = Join-Path $ProjectRoot "build\Debug\producer.exe"

if (!(Test-Path $BrokerExe)) {
    throw "Broker exe not found: $BrokerExe"
}

if (!(Test-Path $ProducerExe)) {
    throw "Producer exe not found: $ProducerExe"
}

$RunDir = Join-Path $ProjectRoot "results\drop_vs_block_q5000_w4_work5000"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$AllResultsCsv = Join-Path $RunDir "all_results_drop_vs_block_q5000_w4_work5000.csv"

if (Test-Path $AllResultsCsv) {
    Remove-Item $AllResultsCsv
}

$Port         = 9000
$W            = 4
$Q            = 5000
$Work         = 5000
$Batch        = 1
$BatchWaitUs  = 0
$DurationSec  = 20
$WarmupSec    = 3

$Modes   = @("drop", "block")
$Rates   = @(500000, 600000, 700000)
$Repeats = 5

Set-Location $ProjectRoot

Write-Host "SCRIPT VERSION: DROP VS BLOCK"
Write-Host "Run dir = $RunDir"
Write-Host "W       = $W"
Write-Host "Q       = $Q"
Write-Host "Work    = $Work"
Write-Host "Batch   = $Batch"
Write-Host "Modes   = $Modes"
Write-Host "Rates   = $Rates"
Write-Host "Repeats = $Repeats"

for ($mi = 0; $mi -lt $Modes.Count; $mi++) {
    $Mode = $Modes[$mi]

    for ($ri = 0; $ri -lt $Rates.Count; $ri++) {
        $Rate = $Rates[$ri]

        for ($rep = 1; $rep -le $Repeats; $rep++) {
            $ExpId = "${Mode}_rate_${Rate}_rep_${rep}"

            Write-Host ""
            Write-Host "========================================"
            Write-Host "START EXPERIMENT: $ExpId"
            Write-Host "========================================"

            $CsvAppend = "false"
            if (Test-Path $AllResultsCsv) {
                $CsvAppend = "true"
            }

            $BrokerOut   = Join-Path $RunDir ("broker_"   + $ExpId + "_out.log")
            $BrokerErr   = Join-Path $RunDir ("broker_"   + $ExpId + "_err.log")
            $ProducerOut = Join-Path $RunDir ("producer_" + $ExpId + "_out.log")
            $ProducerErr = Join-Path $RunDir ("producer_" + $ExpId + "_err.log")

            $BrokerArgs = @(
                "--port", $Port,
                "--w", $W,
                "--q", $Q,
                "--work", $Work,
                "--mode", $Mode,
                "--batch", $Batch,
                "--batch-wait-us", $BatchWaitUs,
                "--sec", $DurationSec,
                "--warmup-sec", $WarmupSec,
                "--csv", $AllResultsCsv,
                "--csv-append", $CsvAppend,
                "--exp-id", $ExpId,
                "--run-id", $ExpId,
                "--repeat-id", $rep,
                "--rate-hint", $Rate
            )

            $brokerProc = Start-Process `
                -FilePath $BrokerExe `
                -ArgumentList $BrokerArgs `
                -RedirectStandardOutput $BrokerOut `
                -RedirectStandardError $BrokerErr `
                -PassThru

            Start-Sleep -Seconds 2

            $ProducerArgs = @(
                "--host", "127.0.0.1",
                "--port", $Port,
                "--rate", $Rate,
                "--sec", $DurationSec
            )

            $producerProc = Start-Process `
                -FilePath $ProducerExe `
                -ArgumentList $ProducerArgs `
                -RedirectStandardOutput $ProducerOut `
                -RedirectStandardError $ProducerErr `
                -PassThru

            try {
                if (-not $producerProc.HasExited) {
                    $producerProc.WaitForExit()
                }
            } catch {
                Write-Host "Producer already finished: $($producerProc.Id)"
            }

            try {
                if (-not $brokerProc.HasExited) {
                    $brokerProc.WaitForExit()
                }
            } catch {
                Write-Host "Broker already finished: $($brokerProc.Id)"
            }

            Write-Host "DONE: $ExpId"
        }
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "ALL EXPERIMENTS FINISHED"
Write-Host "CSV: $AllResultsCsv"
Write-Host "========================================"   