@echo off
setlocal
cd /d "%~dp0"
title Detector de baches - galeria
if not exist ".venv\Scripts\python.exe" goto :sin_entorno
echo Abriendo la galeria de imagenes de prueba...
".venv\Scripts\python.exe" -u app\galeria.py
if errorlevel 1 pause
exit /b 0
:sin_entorno
echo [ERROR] Falta el entorno. Ejecuta primero setup_y_correr.bat
pause
exit /b 1
