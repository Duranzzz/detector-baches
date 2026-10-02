@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Primero ejecuta setup_y_correr.bat
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python webcam.py %*
pause
