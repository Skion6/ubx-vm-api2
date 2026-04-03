@echo off
setlocal EnableDelayedExpansion

REM Parse command line arguments
echo ==========================================
echo     Xcloud - Setup Script      
echo ==========================================

echo 1. Checking Dependencies...
where docker >nul 2>nul
if !errorlevel! neq 0 (
    echo ERROR: Docker is not installed or not in PATH.
    echo Please install Docker Desktop and try again.
    pause
    exit /b 1
)

echo 2. Running Configuration Script...
echo Additional setup options available: --max-global-vms (-g) and --dev-whitelist (-w)
echo Example: tools\setup.bat -g 20 -w "siteA,siteB" --non-interactive
python setup.py %*

echo 3. Building Docker Image...
docker build -t xcloud .
if !errorlevel! neq 0 (
    echo.
    echo ERROR: Docker build failed! Check the output above. IS DOCKER RUNNING?
    pause
    exit /b !errorlevel!
)

echo 4. Creating Python Virtual Environment...
if not exist "venv\" (
    python -m venv venv
)
call venv\Scripts\activate.bat

echo 5. Installing Python Requirements...
pip install -r requirements.txt

echo 6. Ensuring Caddy is installed (Windows)...
where caddy >nul 2>nul
if !errorlevel! neq 0 (
    where choco >nul 2>nul
    if !errorlevel! equ 0 (
        echo Installing Caddy via Chocolatey...
        choco install caddy -y
    ) else (
        echo Caddy not found and Chocolatey not available.
        echo Please install Caddy manually: https://caddyserver.com/docs/install
    )
) else (
    echo Caddy already installed
)

echo ==========================================
echo  Setup Complete! Starting API Server...   
echo  (Press CTRL+C to stop)                   
echo ==========================================

REM Start the uvicorn API server on port 8000
REM If SSL_CERTFILE and SSL_KEYFILE environment vars are set, run with TLS
if defined SSL_CERTFILE (
    if defined SSL_KEYFILE (
        echo Starting Uvicorn with TLS (SSL_CERTFILE and SSL_KEYFILE detected)
        python -m uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-certfile %SSL_CERTFILE% --ssl-keyfile %SSL_KEYFILE%
        goto :EOF
    )
)
python -m uvicorn main:app --host 0.0.0.0 --port 8000
