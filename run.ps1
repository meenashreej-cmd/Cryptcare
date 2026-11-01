# CryptCare One-Click Launcher for Windows PowerShell
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "             Starting CryptCare System                  " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Virtual Environment Check
if (-not (Test-Path "$RootDir\venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtual environment not found in '$RootDir\venv'." -ForegroundColor Red
    Write-Host "Please create it using: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# 2. Frontend node_modules check
if (-not (Test-Path "$RootDir\cryptcare-ai-frontend\node_modules")) {
    Write-Host "[INFO] Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location "$RootDir\cryptcare-ai-frontend"
    npm install
    Pop-Location
}

# 3. Check Ollama (Optional)
try {
    $ollamaCheck = Invoke-RestMethod -Uri "http://localhost:11434/" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
    if ($ollamaCheck -match "Ollama is running") {
        Write-Host "[OK] Ollama is active on http://localhost:11434" -ForegroundColor Green
    }
} catch {
    Write-Host "[NOTE] Ollama is not active (Local clinical AI explanations will use fallback)." -ForegroundColor DarkGray
}

# 4. Launch Backend
Write-Host "[1/3] Launching FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$RootDir'; Write-Host '=== CryptCare Backend (Port 8000) ===' -ForegroundColor Cyan; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

# 5. Launch Frontend
Write-Host "[2/3] Launching Vite Frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$RootDir\cryptcare-ai-frontend'; Write-Host '=== CryptCare Frontend (Port 5173) ===' -ForegroundColor Cyan; npm run dev"

# 6. Open Browser
Write-Host "[3/3] Opening browser..." -ForegroundColor Green
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   CryptCare is running successfully!" -ForegroundColor Green
Write-Host "   * Web App:   http://localhost:5173" -ForegroundColor White
Write-Host "   * Backend:   http://127.0.0.1:8000" -ForegroundColor White
Write-Host "   * API Docs:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan

