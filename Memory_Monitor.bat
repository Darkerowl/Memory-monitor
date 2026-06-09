@echo off
setlocal

REM Move to the folder where this BAT file is located.
REM This lets memory_monitor.py run correctly from any location.
cd /d "%~dp0"

set "SCRIPT=%~dp0memory_monitor.py"
set "PYTHON_EXE="
set "PYTHON_ARGS="

REM Make sure the Python script exists beside this BAT file.
if not exist "%SCRIPT%" (
    echo.
    echo [ERROR] Could not find memory_monitor.py.
    echo Make sure Memory_Monitor.bat and memory_monitor.py are in the same folder.
    echo.
    pause
    exit /b 1
)

REM Prefer a local virtual environment if one exists.
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    goto CHECK_PYTHON
)

REM Otherwise use normal Python from PATH.
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto CHECK_PYTHON
)

REM Fallback to Windows Python Launcher.
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
    goto CHECK_PYTHON
)

echo.
echo [ERROR] Python was not found.
echo Install Python and make sure it is added to PATH.
echo.
pause
exit /b 1

:CHECK_PYTHON

REM Check that psutil is installed for the Python being used.
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import psutil" >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Missing required Python package: psutil
    echo.
    echo Install it with:
    echo     "%PYTHON_EXE%" %PYTHON_ARGS% -m pip install psutil
    echo.
    pause
    exit /b 1
)

REM Start the memory monitor.
"%PYTHON_EXE%" %PYTHON_ARGS% "%SCRIPT%" %*

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] memory_monitor.py closed with an error.
    echo.
    pause
    exit /b %errorlevel%
)

endlocal