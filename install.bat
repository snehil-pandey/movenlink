@echo off
setlocal

:: -------------------------------------------------------
:: Movenlink Installer
:: Installs movenlink.exe to Program Files and adds to PATH
:: Registers PowerShell tab completion
:: Must be run as Administrator
:: -------------------------------------------------------

:: Check admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator.
    echo Right-click install.bat and select "Run as administrator"
    pause
    exit /b 1
)

:: Check exe exists
if not exist dist\movenlink.exe (
    echo ERROR: dist\movenlink.exe not found.
    echo Run build.bat first to compile the exe.
    pause
    exit /b 1
)

:: Define install location
set INSTALL_DIR=%ProgramFiles%\Movenlink

:: Create install directory
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

:: Copy exe
copy /Y dist\movenlink.exe "%INSTALL_DIR%\movenlink.exe" >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy movenlink.exe to %INSTALL_DIR%
    pause
    exit /b 1
)

echo Installed to: %INSTALL_DIR%\movenlink.exe

:: Add to system PATH if not already there
echo %PATH% | find /i "%INSTALL_DIR%" >nul
if %errorlevel% neq 0 (
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" ^
        /v Path ^
        /t REG_EXPAND_SZ ^
        /d "%PATH%;%INSTALL_DIR%" ^
        /f >nul

    if %errorlevel% neq 0 (
        echo ERROR: Failed to add to PATH.
        pause
        exit /b 1
    )

    echo Added to system PATH.
) else (
    echo Already in system PATH, skipping.
)

:: Broadcast PATH change so new terminals pick it up without reboot
powershell -Command ^
  "[System.Environment]::SetEnvironmentVariable('Path', [System.Environment]::GetEnvironmentVariable('Path','Machine'), 'Machine')" ^
  >nul 2>&1

:: Register PowerShell tab completion via the exe itself
echo Registering PowerShell tab completion...
"%INSTALL_DIR%\movenlink.exe" __install_completion__

echo.
echo Done! Open a new PowerShell window and run:
echo   movenlink move    "C:\source\folder" "D:\destination"
echo   movenlink reverse "D:\destination\folder"
echo.
echo Tab completion is active in PowerShell. Press Tab after typing a path.
echo.
pause