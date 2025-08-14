@echo off
title WhatsApp Agent - Docker Stop

echo.
echo =====================================================
echo       WhatsApp Agent - Docker Stop
echo =====================================================
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running
    pause
    exit /b 1
)

echo 🛑 Stopping WhatsApp Agent containers...
echo.

REM Stop containers
docker-compose down

if errorlevel 1 (
    echo.
    echo ❌ Failed to stop containers
    pause
    exit /b 1
)

echo.
echo ✅ All containers stopped successfully!
echo.
echo 💡 To start again, run: docker-start.bat
echo.

pause