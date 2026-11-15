@echo off
setlocal
chcp 65001 > nul
title Whisper Voice Assistant
cd /d "%~dp0"

echo ========================================================
echo   Whisper Voice Assistant
echo ========================================================

set "VER_CHECK=import sys, struct; sys.exit(0 if (struct.calcsize('P') == 8 and sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 12) else 1)"

:: 1. Проверяем локальный .venv
if not exist ".venv\Scripts\python.exe" goto :find_python
".venv\Scripts\python.exe" -c "%VER_CHECK%" >nul 2>nul
if errorlevel 1 (
    echo [Внимание] Текущий .venv поврежден или использует несовместимую версию Python.
    echo [Инфо] Автоматическое пересоздание окружения...
    rd /s /q ".venv" 2>nul
    goto :find_python
)

echo [Инфо] Запуск из виртуального окружения .venv...
".venv\Scripts\python.exe" main.py %*
set "EXIT_CODE=%errorlevel%"
if %EXIT_CODE% neq 0 (
    echo.
    echo [Внимание] Приложение завершило работу с кодом %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%

:find_python
:: 2. Поиск совместимого Python (3.10, 3.11 или 3.12 64-bit) на компьютере
set "SYS_PY="

:: Проверка стандартного Windows лаунчера py на версии 3.11, 3.12, 3.10
where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -c "%VER_CHECK%" >nul 2>nul
    if not errorlevel 1 set "SYS_PY=py -3.11"
    if not defined SYS_PY (
        py -3.12 -c "%VER_CHECK%" >nul 2>nul
        if not errorlevel 1 set "SYS_PY=py -3.12"
    )
    if not defined SYS_PY (
        py -3.10 -c "%VER_CHECK%" >nul 2>nul
        if not errorlevel 1 set "SYS_PY=py -3.10"
    )
)

:: Проверка команды python в системном PATH
if not defined SYS_PY (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "%VER_CHECK%" >nul 2>nul
        if not errorlevel 1 set "SYS_PY=python"
    )
)

:: Поиск по стандартным каталогам установки
if not defined SYS_PY (
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
        if exist %%D if not defined SYS_PY (
            %%D -c "%VER_CHECK%" >nul 2>nul
            if not errorlevel 1 set "SYS_PY=%%~D"
        )
    )
)

:: Поиск в реестре Windows (HKCU)
if not defined SYS_PY (
    for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
        if exist "%%~B" if not defined SYS_PY (
            "%%~B" -c "%VER_CHECK%" >nul 2>nul
            if not errorlevel 1 set "SYS_PY=%%~B"
        )
    )
)

:: Поиск в реестре Windows (HKLM)
if not defined SYS_PY (
    for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
        if exist "%%~B" if not defined SYS_PY (
            "%%~B" -c "%VER_CHECK%" >nul 2>nul
            if not errorlevel 1 set "SYS_PY=%%~B"
        )
    )
)

:: 3. Если совместимый Python 3.10-3.12 (64-bit) не найден
if not defined SYS_PY (
    echo.
    echo ========================================================
    echo  [ОШИБКА] Совместимая версия Python не найдена!
    echo ========================================================
    echo  Для работы нейросетей Whisper и PyTorch требуется строго:
    echo  Python 3.10, 3.11 или 3.12 (64-bit).
    echo.
    echo  (Сверхновые версии вроде Python 3.13-3.15 или 32-bit версии
    echo   не поддерживаются библиотеками CTranslate2 и PyTorch).
    echo.
    echo  Пожалуйста, установите официальный Python 3.11.9 (64-bit):
    echo  https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
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
set "EXIT_CODE=%errorlevel%"
if %EXIT_CODE% neq 0 (
    echo.
    echo [Внимание] Приложение завершило работу с кодом %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
