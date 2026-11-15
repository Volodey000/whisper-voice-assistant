@echo off
setlocal
chcp 65001 > nul
title Whisper Voice Assistant - Диагностика ПК
cd /d "%~dp0"

echo ========================================================
echo   Whisper Voice Assistant - Диагностика готовности ПК
echo ========================================================
echo.

:: 1. Поиск локального .venv или системного Python
set "RUN_PY="

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if not errorlevel 1 set "RUN_PY=.venv\Scripts\python.exe"
)

if not defined RUN_PY (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys" >nul 2>nul
        if not errorlevel 1 set "RUN_PY=python"
    )
)

if not defined RUN_PY (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys" >nul 2>nul
        if not errorlevel 1 set "RUN_PY=py -3"
    )
)

if not defined RUN_PY (
    for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
        if exist "%%~B" if not defined RUN_PY set "RUN_PY=%%~B"
    )
)

if not defined RUN_PY (
    for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
        if exist "%%~B" if not defined RUN_PY set "RUN_PY=%%~B"
    )
)

if not defined RUN_PY (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%ProgramFiles%\Python312\python.exe"
        "%ProgramFiles%\Python311\python.exe"
        "%ProgramFiles%\Python310\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
    ) do (
        if exist %%D if not defined RUN_PY set "RUN_PY=%%~D"
    )
)

if defined RUN_PY goto :found_python

echo [ОШИБКА] Интерпретатор Python не найден на этом компьютере!
echo ========================================================
echo Для работы Whisper Voice Assistant необходим Python 3.10, 3.11 или 3.12 (64-bit).
echo Пожалуйста, установите его с официального сайта:
echo https://www.python.org/downloads/
echo.
echo При установке обязательно включите галочку внизу:
echo [x] Add python.exe to PATH
echo ========================================================
echo.
pause
exit /b 1

:found_python
echo [Инфо] Запуск диагностики через: %RUN_PY%
echo.

%RUN_PY% check_environment.py

echo.
echo ========================================================
echo   Диагностика завершена.
echo ========================================================
echo.
pause
