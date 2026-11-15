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
where py >nul 2>nul || goto :skip_py
py -3.11 -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=py -3.11"
if defined SYS_PY goto :run_app
py -3.12 -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=py -3.12"
if defined SYS_PY goto :run_app
py -3.10 -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=py -3.10"
if defined SYS_PY goto :run_app

:skip_py
:: Проверка команды python в системном PATH
where python >nul 2>nul && python -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=python"
if defined SYS_PY goto :run_app

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
    if exist %%D if not defined SYS_PY (
        %%D -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=%%~D"
    )
)
if defined SYS_PY goto :run_app

:: Поиск в реестре Windows (HKCU)
for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
    if exist "%%~B" if not defined SYS_PY (
        "%%~B" -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=%%~B"
    )
)
if defined SYS_PY goto :run_app

:: Поиск в реестре Windows (HKLM)
for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
    if exist "%%~B" if not defined SYS_PY (
        "%%~B" -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=%%~B"
    )
)
if defined SYS_PY goto :run_app

:: 3. Если совместимый Python не найден — автоматическая загрузка и установка Python 3.11.9 x64
echo.
echo ========================================================
echo  [АВТОМАТИЧЕСКАЯ УСТАНОВКА PYTHON 3.11]
echo ========================================================
echo  Совместимый Python 3.10-3.12 64-bit не обнаружен.
echo  Для работы нейросетей Whisper и PyTorch требуется Python 3.11 64-bit.
echo.
echo  [1/2] Загрузка официального установщика Python 3.11.9 с python.org...
set "PY_INSTALLER=%TEMP%\python-3.11.9-amd64.exe"

if exist "%SystemRoot%\System32\curl.exe" (
    "%SystemRoot%\System32\curl.exe" -fSL --progress-bar -o "%TEMP%\python-3.11.9-amd64.exe" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
) else (
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', '%TEMP%\python-3.11.9-amd64.exe')"
)

if not exist "%TEMP%\python-3.11.9-amd64.exe" goto :install_failed

echo.
echo  [2/2] Тихая установка Python 3.11.9 без прав администратора...
powershell -NoProfile -Command "Start-Process -FilePath '%TEMP%\python-3.11.9-amd64.exe' -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1' -Wait"
del /f /q "%TEMP%\python-3.11.9-amd64.exe" 2>nul

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
)
if not defined SYS_PY (
    for /f "tokens=2*" %%A in ('reg query "HKCU\Software\Python\PythonCore\3.11\InstallPath" /ve 2^>nul ^| findstr /i "REG_SZ"') do (
        if exist "%%~B\python.exe" set "SYS_PY=%%~B\python.exe"
    )
)
if not defined SYS_PY (
    where py >nul 2>nul && py -3.11 -c "%VER_CHECK%" >nul 2>nul && set "SYS_PY=py -3.11"
)
if not defined SYS_PY (
    for /f "tokens=2*" %%A in ('reg query "HKLM\Software\Python\PythonCore\3.11\InstallPath" /ve 2^>nul ^| findstr /i "REG_SZ"') do (
        if exist "%%~B\python.exe" set "SYS_PY=%%~B\python.exe"
    )
)

if defined SYS_PY (
    echo.
    echo  [УСПЕХ] Python 3.11.9 64-bit успешно установлен!
    echo ========================================================
    echo.
    goto :run_app
)

:install_failed
echo.
echo ========================================================
echo  [ОШИБКА] Автоматическая установка не удалась!
echo ========================================================
echo  Пожалуйста, установите официальный Python 3.11.9 64-bit вручную:
echo  https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo.
echo  При установке ОБЯЗАТЕЛЬНО включите галочку внизу:
echo  [x] Add python.exe to PATH
echo ========================================================
echo.
pause
exit /b 1

:run_app
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
