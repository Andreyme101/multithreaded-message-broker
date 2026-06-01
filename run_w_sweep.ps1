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

$AllResultsCsv = Join-Path $ProjectRoot "all_results_w_sweep.csv"

if (Test-Path $AllResultsCsv) {
    Remove-Item $AllResultsCsv
}

$Port         = 9000
$Q            = 5000
$Work         = 5000
$Mode         = "drop"
$Batch        = 1
$BatchWaitUs  = 0
$DurationSec  = 10
$WarmupSec    = 2

$Workers = @(1, 2, 4, 8)
$Rates   = @(100000, 150000)
$Repeats = 3

Set-Location $ProjectRoot

Write-Host "SCRIPT VERSION: W SWEEP"
Write-Host "Workers = $Workers"
Write-Host "Rates   = $Rates"
Write-Host "Repeats = $Repeats"

for ($ri = 0; $ri -lt $Rates.Count; $ri++) {
    $Rate = $Rates[$ri]

    for ($wi = 0; $wi -lt $Workers.Count; $wi++) {
        $W = $Workers[$wi]

        for ($rep = 1; $rep -le $Repeats; $rep++) {
            $ExpId = "w_${W}_rate_${Rate}_rep_${rep}"

            Write-Host ""
            Write-Host "========================================"
            Write-Host "START EXPERIMENT: $ExpId"
            Write-Host "========================================"

            $CsvAppend = "false"
            if (Test-Path $AllResultsCsv) {
                $CsvAppend = "true"
            }

            $BrokerOut   = Join-Path $ProjectRoot ("broker_"   + $ExpId + "_out.log")
            $BrokerErr   = Join-Path $ProjectRoot ("broker_"   + $ExpId + "_err.log")
            $ProducerOut = Join-Path $ProjectRoot ("producer_" + $ExpId + "_out.log")
            $ProducerErr = Join-Path $ProjectRoot ("producer_" + $ExpId + "_err.log")

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