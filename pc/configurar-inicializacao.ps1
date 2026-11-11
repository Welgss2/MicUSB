$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'micusb.py'
$pyw = (Get-Command 'pyw.exe' -ErrorAction SilentlyContinue).Source
if (-not $pyw) {
    $python = (Get-Command 'python.exe' -ErrorAction Stop).Source
    $pyw = Join-Path (Split-Path $python) 'pythonw.exe'
}
if (-not (Test-Path -LiteralPath $pyw)) {
    throw "Nao encontrei pythonw.exe. Reinstale o Python marcando Add to PATH."
}
$command = '"{0}" "{1}" --minimized' -f $pyw, $scriptPath
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
New-Item -Path $runKey -Force | Out-Null
New-ItemProperty -Path $runKey -Name 'MicUSB' -Value $command -PropertyType String -Force | Out-Null
Write-Host 'MicUSB configurado para iniciar em segundo plano com o Windows.'
