@echo off
title WhatsApp Agent - Docker Startup

echo.
echo =====================================================
echo       WhatsApp Agent - Docker Startup
echo =====================================================
echo.

REM Check if Docker is installed and running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop from https://docker.com
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Compose is not available
    echo Please ensure Docker Desktop is properly installed
    pause
    exit /b 1
)

echo ✅ Docker is available
echo.

REM Check if docker-compose.yml exists
if not exist "docker-compose.yml" (
    echo ERROR: docker-compose.yml not found
    echo Please ensure you're in the correct directory
    pause
    exit /b 1
)

echo 🚀 Starting WhatsApp Agent with Docker...
echo.
echo This will start:
echo   • WAHA Server (WhatsApp API) on port 4500
echo   • WhatsApp Agent Dashboard on port 8000
echo.

REM Build and start containers
echo 🔨 Building and starting containers...
docker-compose up -d --build

if errorlevel 1 (
    echo.
    echo ❌ Failed to start containers
    echo Check the error messages above
    pause
    exit /b 1
)

echo.
echo ✅ Containers started successfully!
echo.
echo 📱 Access your WhatsApp Agent at:
echo    👉 https://app.cuwapp.com
echo.
echo 🔧 WAHA Server API at:
echo    👉 http://localhost:4500
echo.
echo 📊 Container Status:
docker-compose ps

echo.
echo 💡 Useful commands:
echo    • View logs:     docker-compose logs -f
echo    • Stop:          docker-compose down
echo    • Restart:       docker-compose restart
echo    • Update:        docker-compose pull ^&^& docker-compose up -d
echo.

pause