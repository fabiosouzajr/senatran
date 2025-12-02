# PowerShell activation script for Senatran automation virtual environment

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir ".venv"

if (-not (Test-Path $VenvDir)) {
    Write-Host "Virtual environment not found at $VenvDir"
    Write-Host "Creating virtual environment..."
    python -m venv $VenvDir
    Write-Host "Installing dependencies..."
    & "$VenvDir\Scripts\pip.exe" install -r "$ScriptDir\requirements.txt"
    & "$VenvDir\Scripts\playwright.exe" install chromium
    Write-Host "Virtual environment created and dependencies installed!"
}

Write-Host "Activating virtual environment..."
& "$VenvDir\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Virtual environment activated!"
Write-Host "Python: $(Get-Command python | Select-Object -ExpandProperty Source)"
Write-Host "To deactivate, run: deactivate"
Write-Host ""

