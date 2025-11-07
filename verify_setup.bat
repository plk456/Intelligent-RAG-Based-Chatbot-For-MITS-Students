@echo off
echo Verifying Docker and CI/CD Setup...

echo.
echo Checking required files:
if exist "Dockerfile" (
    echo [OK] Dockerfile found
) else (
    echo [MISSING] Dockerfile
)

if exist "docker-compose.yml" (
    echo [OK] docker-compose.yml found
) else (
    echo [MISSING] docker-compose.yml
)

if exist ".github\workflows\deploy.yml" (
    echo [OK] GitHub Actions workflow found
) else (
    echo [MISSING] GitHub Actions workflow
)

if exist "server.js" (
    echo [OK] server.js found
) else (
    echo [MISSING] server.js
)

if exist "package.json" (
    echo [OK] package.json found
) else (
    echo [MISSING] package.json
)

echo.
echo Setup verification complete!
echo If all files show [OK], your Docker and CI/CD setup is ready.
pause