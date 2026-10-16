@echo off
setlocal
cd /d "%~dp0"
title Detector de baches
echo ==============================================
echo  Detector de baches - iniciando
echo ==============================================
echo La primera carga puede tardar varios segundos.
echo Los mensajes de abajo indican el paso actual.
echo.
if not exist ".venv\Scripts\python.exe" goto :sin_entorno
".venv\Scripts\python.exe" -u app\webcam.py %*
set "RESULTADO=%ERRORLEVEL%"
echo.
if not "%RESULTADO%"=="0" echo [ERROR] El detector termino con un error. Revisa el mensaje de arriba.
pause
exit /b %RESULTADO%

:sin_entorno
echo [ERROR] Falta el entorno. Ejecuta primero setup_y_correr.bat
pause
exit /b 1
