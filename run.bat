@echo off
setlocal enabledelayedexpansion

:: 1. cd to its own folder
cd /d "%~dp0"

:: 2. activate venv
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: 3. Check Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Ollama not running. Attempting to start...
    start "" /min ollama serve
    echo Waiting 15 seconds for Ollama to initialize...
    timeout /t 15 /nobreak >nul
)

:: 4. Run preflight
echo Running preflight checks...
python scripts\preflight.py
if errorlevel 1 (
    echo Preflight failed.
    pause
    exit /b 1
)

:: 5. Print local IP address
python scripts\get_ip.py

:: 6. Run streamlit
python -m streamlit run app.py --server.address 0.0.0.0 --server.headless true
