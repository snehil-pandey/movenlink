@echo off
echo Building movenlink.exe...

pip install pyinstaller >nul 2>&1

pyinstaller --onefile --name movenlink --manifest movenlink.manifest main.py

if exist dist\movenlink.exe (
    echo Build successful.
) else (
    echo Build FAILED.
    pause
    exit /b 1
)