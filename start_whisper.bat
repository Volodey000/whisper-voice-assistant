@echo off
chcp 65001 > nul
title Whisper Voice Assistant
cd /d "%~dp0"

echo ========================================================
echo   Whisper Voice Assistant: Запуск и самодиагностика
echo ========================================================

REM ---------------------------------------------------------
REM 1. Проверяем существующий локальный .venv
REM ---------------------------------------------------------
if not exist ".venv\Scripts\python.exe" goto find_python

".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo [Внимание] Локальный .venv скопирован с другого ПК и несовместим.
    echo [Инфо] Пересоздание виртуального окружения для этого устройства...
    rd /s /q ".venv" 2>nul
    goto find_python
)

set "PY_EXE=.venv\Scripts\python.exe"
goto check_env

REM ---------------------------------------------------------
REM 2. Поиск Python на компьютере
REM ---------------------------------------------------------
:find_python
echo [Инфо] Поиск установленного Python на компьютере...
set "SYS_PY="
set "USE_PY_LAUNCHER=0"

REM Проверка стандартного лаунчера py
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "USE_PY_LAUNCHER=1"
        goto make_venv
    )
)

REM Проверка команды python в системном PATH
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "SYS_PY=python"
        goto make_venv
    )
)

REM Поиск в реестре Windows (HKCU)
for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
    if exist "%%~B" (
        "%%~B" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "SYS_PY=%%~B"
            goto make_venv
        )
    )
)

REM Поиск в реестре Windows (HKLM)
for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
    if exist "%%~B" (
        "%%~B" -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            set "SYS_PY=%%~B"
            goto make_venv
        )
    )
)

REM Поиск по стандартным каталогам установки
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
        if not errorlevel 1 (
            set "SYS_PY=%%~D"
            goto make_venv
        )
    )
)

REM ---------------------------------------------------------
REM Если Python не найден нигде - останавливаемся с инструкцией!
REM ---------------------------------------------------------
echo.
echo ========================================================
echo  [ОШИБКА] Python не обнаружен на этом компьютере!
echo ========================================================
echo  Для работы Whisper Voice Assistant необходим Python 3.10, 3.11 или 3.12.
echo.
echo  Пожалуйста, выполните 2 простых шага:
echo  1. Скачайте Python с официального сайта:
echo     https://www.python.org/downloads/
echo  2. При установке ОБЯЗАТЕЛЬНО включите галочку внизу:
echo     [x] Add python.exe to PATH
echo.
echo  После завершения установки запустите start_whisper.bat снова.
echo ========================================================
echo.
pause
exit /b 1

REM ---------------------------------------------------------
REM 3. Создание локального .venv
REM ---------------------------------------------------------
:make_venv
if "%USE_PY_LAUNCHER%"=="1" (
    echo [Инфо] Найден системный Python: py launcher
    echo [Инфо] Создание виртуального окружения .venv на этом компьютере...
    py -3 -m venv .venv
    if not errorlevel 1 (
        set "PY_EXE=.venv\Scripts\python.exe"
    ) else (
        echo [Предупреждение] Не удалось создать .venv, работа продолжится через системный Python.
        for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "SYS_PY=%%I"
        set "PY_EXE=%SYS_PY%"
    )
    goto check_env
)

if not defined SYS_PY (
    echo [ОШИБКА] Python не определен.
    pause
    exit /b 1
)

echo [Инфо] Найден системный Python: %SYS_PY%
echo [Инфо] Создание виртуального окружения .venv на этом компьютере...
if "%SYS_PY%"=="python" (
    python -m venv .venv
) else (
    "%SYS_PY%" -m venv .venv
)

if not errorlevel 1 (
    set "PY_EXE=.venv\Scripts\python.exe"
) else (
    echo [Предупреждение] Не удалось создать .venv, работа продолжится через системный Python.
    set "PY_EXE=%SYS_PY%"
)

REM ---------------------------------------------------------
REM 4. Проверка и автоматическая доустановка библиотек
REM ---------------------------------------------------------
:check_env
if not defined PY_EXE (
    echo [ОШИБКА] Исполняемый файл Python не найден.
    pause
    exit /b 1
)

echo [Инфо] Проверка библиотек и компонентов...
if "%PY_EXE%"=="python" (
    python check_environment.py
) else (
    "%PY_EXE%" check_environment.py
)
if errorlevel 1 (
    echo.
    echo ========================================================
    echo  [ОШИБКА] Не удалось настроить компоненты окружения!
    echo ========================================================
    pause
    exit /b 1
)

REM ---------------------------------------------------------
REM 5. Запуск приложения Whisper Voice Assistant
REM ---------------------------------------------------------
echo [Инфо] Запуск Whisper Voice Assistant...
if "%PY_EXE%"=="python" (
    python main.py %*
) else (
    "%PY_EXE%" main.py %*
)
if errorlevel 1 (
    echo.
    echo ========================================================
    echo  [Внимание] Приложение завершило работу с ошибкой.
    echo ========================================================
    pause
)
