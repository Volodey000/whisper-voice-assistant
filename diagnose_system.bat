@echo off
setlocal
chcp 65001 > nul
title Whisper Voice Assistant - Диагностика ПК
cd /d "%~dp0"

echo ========================================================
echo   Whisper Voice Assistant - Диагностика готовности ПК
echo ========================================================
echo.

set "VER_CHECK=import sys, struct; sys.exit(0 if (struct.calcsize('P') == 8 and sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 12) else 1)"

:: 1. Поиск локального .venv или совместимого Python (3.10 - 3.12 x64)
set "RUN_PY="

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=.venv\Scripts\python.exe"
)
if defined RUN_PY goto :found_python

:: Проверка стандартного Windows лаунчера py
where py >nul 2>nul || goto :skip_py
py -3.11 -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=py -3.11"
if defined RUN_PY goto :found_python
py -3.12 -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=py -3.12"
if defined RUN_PY goto :found_python
py -3.10 -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=py -3.10"
if defined RUN_PY goto :found_python

:skip_py
:: Проверка команды python в системном PATH
where python >nul 2>nul && python -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=python"
if defined RUN_PY goto :found_python

:: Поиск по стандартным каталогам установки
for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Python311\python.exe"
    "C:\Python312\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%D if not defined RUN_PY (
        %%D -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=%%~D"
    )
)
if defined RUN_PY goto :found_python

:: Поиск в реестре Windows (HKCU)
for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
    if exist "%%~B" if not defined RUN_PY (
        "%%~B" -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=%%~B"
    )
)
if defined RUN_PY goto :found_python

:: Поиск в реестре Windows (HKLM)
for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
    if exist "%%~B" if not defined RUN_PY (
        "%%~B" -c "%VER_CHECK%" >nul 2>nul && set "RUN_PY=%%~B"
    )
)
if defined RUN_PY goto :found_python

echo [ОШИБКА] Совместимый Python 3.10, 3.11 или 3.12 64-bit не найден!
echo ========================================================
echo Для работы Whisper Voice Assistant необходим Python 3.10, 3.11 или 3.12 64-bit.
echo Сверхновые версии Python 3.13-3.15 или 32-bit не поддерживаются библиотеками ИИ.
echo.
echo Решение:
echo 1. Просто запустите "start_whisper.bat" — он САМ автоматически
echo    скачает и установит официальный Python 3.11 64-bit в тихом режиме!
echo.
echo Или установите вручную с официального сайта:
echo https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo При ручной установке обязательно отметьте: [x] Add python.exe to PATH
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
