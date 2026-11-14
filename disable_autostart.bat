@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo Whisper Voice Assistant: Autostart OFF...
".venv\Scripts\python.exe" autostart.py disable
pause