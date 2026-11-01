# PowerShell script for managing Ollama for CryptCare
$ErrorActionPreference = "Continue"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "             Ollama Local AI Controller                 " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Check Ollama executable
$ollamaCmd = Get-Command "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaCmd) {
    Write-Host "[ERROR] 'ollama' executable was not found in PATH." -ForegroundColor Red
    Write-Host "Install it from https://ollama.com or check your installation." -ForegroundColor Yellow
    exit 1
}

# 2. Check if already listening
$isRunning = $false
try {
    $res = Invoke-RestMethod -Uri "http://localhost:11434/" -Method Get -TimeoutSec 2 -ErrorAction Stop
    if ($res -match "Ollama is running") {
        $isRunning = $true
        Write-Host "[OK] Ollama is active on http://localhost:11434" -ForegroundColor Green
    }
} catch {
    $isRunning = $false
}

# 3. Start if needed
if (-not $isRunning) {
    Write-Host "[INFO] Starting Ollama server..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Minimized
    
    $attempts = 0
    while ($attempts -lt 10) {
        Start-Sleep -Seconds 2
        try {
            $check = Invoke-RestMethod -Uri "http://localhost:11434/" -Method Get -TimeoutSec 1 -ErrorAction Stop
            if ($check -match "Ollama is running") {
                Write-Host "[OK] Ollama server initialized successfully!" -ForegroundColor Green
                $isRunning = $true
                break
            }
        } catch {}
        $attempts++
    }
}

Write-Host ""
Write-Host "Installed Models:" -ForegroundColor Cyan
ollama list

Write-Host ""
Write-Host "Choose an action:" -ForegroundColor Yellow
Write-Host " [1] Chat interactively with llama3.1 (Default)"
Write-Host " [2] Run clinical test prompt (Amoxicillin & Penicillin allergy)"
Write-Host " [3] Pull / update llama3.1 model"
Write-Host " [4] Exit (leave Ollama running in background)"
Write-Host ""
$choice = Read-Host "Select [1-4] (default: 1)"

switch ($choice) {
    "2" {
        Write-Host "`nRunning test prompt through llama3.1..." -ForegroundColor Cyan
        ollama run llama3.1 "Explain in 2 clinical sentences why Amoxicillin is contraindicated for a patient with a Penicillin allergy."
    }
    "3" {
        Write-Host "`nPulling llama3.1..." -ForegroundColor Cyan
        ollama run llama3.1 "/bye" | Out-Null
        ollama pull llama3.1
    }
    "4" {
        Write-Host "`nOllama is active on port 11434. Ready for CryptCare API requests." -ForegroundColor Green
    }
    Default {
        Write-Host "`nStarting interactive session with llama3.1 (Type /bye to exit)..." -ForegroundColor Cyan
        ollama run llama3.1
    }
}

