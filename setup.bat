@echo off
echo ==========================================
echo     VM API - Setup Script      
echo ==========================================

echo 1. Checking Dependencies...
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not in PATH.
    echo Please install Docker Desktop and try again.
    pause
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: python is not installed or not in PATH.
    pause
    exit /b 1
)

echo 2. Building Docker Image...
docker build -t gamingoncodespaces .

echo 3. Creating Python Virtual Environment...
if not exist "venv\" (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo 4. Installing Python Requirements...
pip install -r requirements.txt

echo ==========================================
echo  Setup Complete! Starting API Server...   
echo  (Press CTRL+C to stop)                   
echo ==========================================

python -m uvicorn main:app --host 0.0.0.0 --port 8000
