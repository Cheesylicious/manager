@echo off
cd /d "%~dp0"

:: Check Admin
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run
) else (
    echo Fordere Admin-Rechte an...
    :: -NoProfile verhindert den Fehler mit deinem Profil
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:run
cls
echo ---------------------------------------
echo D2R Multi-Instance Unlocker
echo ---------------------------------------
python d2r_unlocker.py
echo.
echo ---------------------------------------
pause