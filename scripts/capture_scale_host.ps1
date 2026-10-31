param([Parameter(Mandatory=$true)][string]$Output,
      [Parameter(Mandatory=$true)][string]$StopFile)

$ErrorActionPreference = 'Stop'
$observerOutput = [IO.Path]::GetFullPath($Output)
$observerStop = [IO.Path]::GetFullPath($StopFile)
$allowedRoot = [IO.Path]::GetFullPath((Join-Path (Get-Location).Path 'generated')) + [IO.Path]::DirectorySeparatorChar
if (-not $observerOutput.StartsWith($allowedRoot) -or -not $observerStop.StartsWith($allowedRoot)) {
    throw 'La observación debe guardarse dentro de generated/'
}
if (Test-Path -LiteralPath $observerStop) { throw 'Usa un archivo de parada nuevo' }
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($observerOutput)) | Out-Null
$logical = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
$previousCpu = @{}
$elapsed = [Diagnostics.Stopwatch]::StartNew()
$previousAt = 0.0
do {
    $now = $elapsed.Elapsed.TotalSeconds
    $interval = $now - $previousAt
    $rows = @()
    foreach ($processRow in Get-Process) {
        if ($null -eq $processRow.CPU) { continue }
        $usage = $null
        if ($previousCpu.ContainsKey($processRow.Id) -and $interval -gt 0) {
            $usage = [Math]::Max(0, ($processRow.CPU - $previousCpu[$processRow.Id]) / $interval / $logical * 100)
        }
        $rows += [pscustomobject]@{pid=$processRow.Id;name=$processRow.ProcessName;
            cpu_percent_host=$usage;memory_mb=[Math]::Round($processRow.WorkingSet64 / 1MB, 1)}
        $previousCpu[$processRow.Id] = $processRow.CPU
    }
    $readers = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object { $_.CommandLine -like '*bench.proveedores*' } |
        Select-Object -ExpandProperty ProcessId)
    $sample = [pscustomobject]@{
        at=[DateTimeOffset]::UtcNow.ToString('o');logical_processors=$logical;
        reading_comparison_pids=$readers;
        host_shared=$true;
        processes=@($rows | Sort-Object cpu_percent_host -Descending | Select-Object -First 15)
    }
    [IO.File]::AppendAllText($observerOutput, ($sample | ConvertTo-Json -Depth 6 -Compress) + "`n")
    $previousAt = $now
    if (Test-Path -LiteralPath $observerStop) { break }
    Start-Sleep -Seconds 30
} while ($true)
