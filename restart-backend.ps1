# Script to kill all backend processes and start a new one

Write-Host "=== Stopping Backend Processes ===" -ForegroundColor Yellow

# Find and kill all Python/uvicorn processes related to audexaai-backend
$backendProcesses = Get-WmiObject Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -or $_.Name -eq 'uvicorn.exe') -and 
    $_.CommandLine -like '*audexaai-backend*'
}

if ($backendProcesses) {
    Write-Host "Found $($backendProcesses.Count) backend process(es) to kill" -ForegroundColor Cyan
    foreach ($proc in $backendProcesses) {
        Write-Host "  Killing process $($proc.ProcessId): $($proc.CommandLine)" -ForegroundColor Gray
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "Backend processes stopped" -ForegroundColor Green
} else {
    Write-Host "No backend processes found" -ForegroundColor Gray
}

Write-Host "`n=== Starting Backend Server ===" -ForegroundColor Yellow

# Change to backend directory
$backendPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $backendPath

# Check if virtual environment exists
$venvPath = Join-Path $backendPath ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPath)) {
    Write-Host "ERROR: Virtual environment not found at $venvPath" -ForegroundColor Red
    Write-Host "Please create the virtual environment first" -ForegroundColor Red
    exit 1
}

# Start the backend server
Write-Host "Starting uvicorn server on port 8000..." -ForegroundColor Cyan
Start-Process -FilePath $venvPath -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $backendPath -WindowStyle Minimized

Start-Sleep -Seconds 3

# Verify it's running
$running = Get-WmiObject Win32_Process | Where-Object {
    ($_.Name -eq 'python.exe' -or $_.Name -eq 'uvicorn.exe') -and 
    $_.CommandLine -like '*audexaai-backend*' -and
    $_.CommandLine -like '*uvicorn*'
}

if ($running) {
    Write-Host "Backend server started successfully!" -ForegroundColor Green
    Write-Host "Server running on: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API docs available at: http://localhost:8000/docs" -ForegroundColor Cyan
} else {
    Write-Host "WARNING: Backend process may not have started. Check for errors." -ForegroundColor Yellow
}
