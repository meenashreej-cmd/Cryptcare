@echo off
title CryptCare Runner
echo ========================================================
echo               Starting CryptCare Network
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Check Python Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in venv\
    echo Please create it with: python -m venv venv
    pause
    exit /b 1
)

:: 2. Check Frontend node_modules
if not exist "cryptcare-ai-frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd cryptcare-ai-frontend
    call npm install
    cd ..
)

:: 3. Start Backend in separate window
echo [1/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "CryptCare Backend" cmd /k "title CryptCare Backend && .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: 4. Start Frontend in separate window
echo [2/3] Starting Vite Frontend on http://localhost:5173 ...
start "CryptCare Frontend" cmd /k "title CryptCare Frontend && cd cryptcare-ai-frontend && npm run dev"

:: 5. Open Browser
echo [3/3] Opening browser at http://localhost:5173 ...
timeout /t 3 >nul
start http://localhost:5173

echo.
echo ========================================================
echo   CryptCare is now running!
echo   - Frontend:  http://localhost:5173
echo   - Backend:   http://127.0.0.1:8000
echo   - API Docs:  http://127.0.0.1:8000/docs
echo.
echo   Close the opened command windows to stop the servers.
echo ========================================================
echo.
pause

