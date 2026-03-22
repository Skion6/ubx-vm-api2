@echo off
setlocal EnableDelayedExpansion

REM Parse command line arguments
echo ==========================================
echo     Xcloud - Setup Script      
echo ==========================================

echo 1. Checking Dependencies...
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH.
    echo Please install Docker Desktop and try again.
    pause
    exit /b 1
)

echo 2. Running Configuration Script...
python setup.py %*

echo 3. Building Docker Image...
docker build -t xcloud .
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Docker build failed! Check the output above. IS DOCKER RUNNING?
    pause
    exit /b %errorlevel%
)

echo 4. Creating Python Virtual Environment...
if not exist "venv\" (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo 5. Installing Python Requirements...
pip install -r requirements.txt

echo ==========================================
echo  Setup Complete! Starting API Server...   
echo  (Press CTRL+C to stop)                   
echo ==========================================

python -m uvicorn main:app --host 0.0.0.0 --port 8000
