@echo off
setlocal

set "RUNS_DIR=benchmarl_setup\runs"

if not exist "%RUNS_DIR%" (
    echo Runs folder not found: %RUNS_DIR%
    exit /b 1
)

echo This will permanently delete all contents inside:
echo   %RUNS_DIR%
echo.
set /p "CONFIRM=Type YES to continue: "

if /I not "%CONFIRM%"=="YES" (
    echo Cleanup canceled.
    exit /b 0
)

for %%I in ("%RUNS_DIR%") do set "ABS_RUNS=%%~fI"
if /I not "%ABS_RUNS:benchmarl_setup\runs=%"=="%ABS_RUNS%" (
    rem Path looks correct; continue.
) else (
    echo Safety check failed for path: %ABS_RUNS%
    exit /b 1
)

echo Deleting files...
del /q /f "%RUNS_DIR%\*" >nul 2>&1

echo Deleting subfolders...
for /d %%D in ("%RUNS_DIR%\*") do rd /s /q "%%~fD"

echo Cleanup completed for %RUNS_DIR%.
endlocal
