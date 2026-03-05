@echo off
REM Build Atelier desktop application to EXE
echo Building Atelier...

REM Install dependencies if needed
py -m pip install -q -r requirements.txt

REM Create data directory for runtime (DB will be created there)
if not exist "dist\data" mkdir "dist\data"

py -m PyInstaller --clean build.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build complete! EXE: dist\Atelier.exe
    echo Run: dist\Atelier.exe
) else (
    echo Build failed!
    exit /b 1
)
