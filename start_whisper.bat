@echo off
setlocal
chcp 65001 > nul
title Whisper Voice Assistant
cd /d "%~dp0"

echo ========================================================
echo   Whisper Voice Assistant
echo ========================================================

:: 1. Проверяем локальный .venv
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        echo [Инфо] Запуск из виртуального окружения .venv...
        ".venv\Scripts\python.exe" main.py %*
        if errorlevel 1 (
            echo.
            echo [Внимание] Приложение завершило работу с кодом %errorlevel%.
            pause
        )
        exit /b %errorlevel%
    )
    echo [Внимание] Текущий .venv поврежден или скопирован с другого ПК.
    echo [Инфо] Пересоздание виртуального окружения...
    rd /s /q ".venv" 2>nul
)

:: 2. Поиск Python на компьютере
set "SYS_PY="

:: Проверка команды python в системном PATH
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 set "SYS_PY=python"
)

:: Проверка стандартного лаунчера py
if not defined SYS_PY (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys" >nul 2>nul
        if not errorlevel 1 set "SYS_PY=py -3"
    )
)

:: Поиск в реестре Windows (HKCU)
if not defined SYS_PY (
    for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
        if exist "%%~B" (
            "%%~B" -c "import sys" >nul 2>nul
            if not errorlevel 1 if not defined SYS_PY set "SYS_PY=%%~B"
        )
    )
)

:: Поиск в реестре Windows (HKLM)
if not defined SYS_PY (
    for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
        if exist "%%~B" (
            "%%~B" -c "import sys" >nul 2>nul
            if not errorlevel 1 if not defined SYS_PY set "SYS_PY=%%~B"
        )
    )
)

:: Поиск по стандартным каталогам установки
if not defined SYS_PY (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%ProgramFiles%\Python312\python.exe"
        "%ProgramFiles%\Python311\python.exe"
        "%ProgramFiles%\Python310\python.exe"
        "C:\Program Files\Python312\python.exe"
        "C:\Program Files\Python311\python.exe"
        "C:\Program Files\Python310\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
    ) do (
        if exist %%D (
            %%D -c "import sys" >nul 2>nul
            if not errorlevel 1 if not defined SYS_PY set "SYS_PY=%%~D"
        )
    )
)

:: 3. Если Python не найден нигде - выводим подробную инструкцию
if not defined SYS_PY (
    echo.
    echo ========================================================
    echo  [ОШИБКА] Python не обнаружен на этом компьютере!
    echo ========================================================
    echo  Для работы Whisper Voice Assistant необходим Python 3.10, 3.11 или 3.12.
    echo.
    echo  Пожалуйста, установите Python с официального сайта:
    echo  https://www.python.org/downloads/
    echo.
    echo  При установке ОБЯЗАТЕЛЬНО включите галочку внизу:
    echo  [x] Add python.exe to PATH
    echo ========================================================
    echo.
    pause
    exit /b 1
)

:: 4. Запуск приложения (самоинициализация .venv встроена в main.py)
echo [Инфо] Запуск Whisper Voice Assistant через %SYS_PY%...
%SYS_PY% main.py %*
if errorlevel 1 (
    echo.
    echo [Внимание] Приложение завершило работу с кодом %errorlevel%.
    pause
)
exit /b %errorlevel%
