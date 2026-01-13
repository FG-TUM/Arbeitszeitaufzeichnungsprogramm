@echo off

setlocal

REM Get the project root directory (2 levels up from this script)
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."

REM Activate the virtual environment - use wildcards to find it
set "ACTIVATE_SCRIPT="
for /d %%i in ("%PROJECT_ROOT%\.venv*") do (
    if exist "%%i\Scripts\activate.bat" (
        set "ACTIVATE_SCRIPT=%%i\Scripts\activate.bat"
        goto :found
    )
)

:found
if not defined ACTIVATE_SCRIPT (
    echo Error: Could not find virtual environment activation script >&2
    exit /b 1
)

call "%ACTIVATE_SCRIPT%"

REM Run the Python script with all arguments passed to this script
python "%PROJECT_ROOT%\src\arbeitszeitaufzeichnungsprogramm.py" %*

REM Store the exit code
set "EXIT_CODE=%ERRORLEVEL%"

REM Deactivate the virtual environment
call deactivate

REM Exit with the same error code as the Python script
exit /b %EXIT_CODE%

