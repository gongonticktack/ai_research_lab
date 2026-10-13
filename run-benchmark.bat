@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run-sam3d-wsl.ps1"
echo.
echo Benchmark finished. Missing model/data returns exit code 2.
pause
