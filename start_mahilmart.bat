@echo off
setlocal

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found. Please install Python 3.11+ and add it to PATH.
  pause
  exit /b 1
)

cd /d "%~dp0"
set DJANGO_SETTINGS_MODULE=MahilMartPOS.settings

echo Starting MahilMart POS...
start "" http://127.0.0.1:0608/
python manage.py runserver 0.0.0.0:0608
