@echo off
title Ollama Runner - CryptCare
echo ========================================================
echo               Ollama Local AI Controller
echo ========================================================
echo.

:: 1. Check if Ollama executable exists
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama command not found in PATH!
    echo Please ensure Ollama is installed from https://ollama.com
    pause
    exit /b 1
)

:: 2. Check if Ollama is already running
curl -s http://localhost:11434/ >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ollama server is already running on http://localhost:11434
    goto :menu
)

:: 3. Start Ollama server if not running
echo [INFO] Starting Ollama server in background...
start "Ollama Server" /min cmd /c "ollama serve"

echo Waiting for Ollama server to initialize...
:wait_loop
timeout /t 2 >nul
curl -s http://localhost:11434/ >nul 2>&1
if %errorlevel% neq 0 (
    goto :wait_loop
)
echo [OK] Ollama server is ready!

:menu
echo.
echo --------------------------------------------------------
echo Installed Models:
ollama list
echo --------------------------------------------------------
echo.
echo Select an option:
echo   [1] Open interactive chat with llama3.1
echo   [2] Test a clinical explanation prompt
echo   [3] Pull/Update llama3.1 model
echo   [4] Keep server running in background and exit
echo.
set /p opt="Enter choice [1-4] (default 1): "

if "%opt%"=="2" (
    echo.
    echo Testing prompt with llama3.1...
    ollama run llama3.1 "Explain in 2 clinical sentences why Amoxicillin is contraindicated for a patient with a Penicillin allergy."
    pause
) else if "%opt%"=="3" (
    echo.
    echo Pulling llama3.1...
    ollama pull llama3.1
    pause
) else if "%opt%"=="4" (
    echo.
    echo Ollama server is active on http://localhost:11434.
) else (
    echo.
    echo Starting chat with llama3.1 (Type /bye to exit)...
    ollama run llama3.1
)

exit /b 0

