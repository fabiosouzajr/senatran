# PowerShell script to activate the virtual environment
# Run this script from the project root directory

if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated!" -ForegroundColor Green
} else {
    Write-Host "Error: Virtual environment not found. Run setup.ps1 first." -ForegroundColor Red
}

