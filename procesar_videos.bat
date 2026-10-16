@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto :sin_venv
echo Detector de baches - procesar videos del celular
echo Arrastra videos sobre este archivo, o copialos en la carpeta videos y haz doble clic.
echo.
".venv\Scripts\python.exe" app\procesar_videos.py %*
echo.
if exist "videos\anotados" start "" "videos\anotados"
pause
exit /b 0
:sin_venv
echo [ERROR] Falta el entorno. Ejecuta primero setup_y_correr.bat
pause
exit /b 1
