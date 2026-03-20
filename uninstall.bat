@echo off
setlocal

:: -------------------------------------------------------
:: Movenlink Uninstaller
:: -------------------------------------------------------

:: Check admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator.
    pause
    exit /b 1
)

set INSTALL_DIR=%ProgramFiles%\Movenlink

:: Remove exe and folder
if exist "%INSTALL_DIR%" (
    rmdir /S /Q "%INSTALL_DIR%"
    echo Removed: %INSTALL_DIR%
) else (
    echo movenlink is not installed, nothing to remove.
)

:: Remove from system PATH
for /f "tokens=*" %%i in ('powershell -Command ^
    "[System.Environment]::GetEnvironmentVariable('Path','Machine')"') do set CURRENT_PATH=%%i

:: Strip the install dir from PATH
set NEW_PATH=%CURRENT_PATH:%INSTALL_DIR%;=%
set NEW_PATH=%NEW_PATH:;%INSTALL_DIR%=%

reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" ^
    /v Path ^
    /t REG_EXPAND_SZ ^
    /d "%NEW_PATH%" ^
    /f >nul

echo Removed from system PATH.
echo.
echo Done! movenlink has been uninstalled.
pause