@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo  Detector de baches - instalacion y verificacion
echo ==============================================
echo Carpeta de trabajo: %cd%
echo.

rem Nota: dentro de bloques entre parentesis cmd se rompe con textos que llevan parentesis,
rem por eso este archivo usa saltos (goto) en lugar de bloques if ( ... ).

rem ---- 1) Python ----
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :sin_python
%PY% --version
if errorlevel 1 goto :python_roto

rem ---- 2) Repo + dataset, fijado al commit que se reviso ----
set "SHA=bd8238b0f87083a1cea658336307d15b54eb7500"
if exist "repo\dataset\images\test" goto :hay_dataset
echo Descargando repo + dataset, unos 640 MB, commit %SHA:~0,7% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/Bisman-Singh-Dev/YOLO-Pothole-Detection-Model/archive/%SHA%.zip' -OutFile 'repo.zip'; Expand-Archive -Path 'repo.zip' -DestinationPath 'repo_tmp' -Force; Move-Item -Path (Get-ChildItem 'repo_tmp').FullName -Destination 'repo'; Remove-Item 'repo.zip'; Remove-Item 'repo_tmp' -Recurse -Force"
:hay_dataset
if not exist "repo\dataset\images\test" goto :sin_dataset
echo Repo y dataset listos.

rem ---- 3) Entorno virtual + dependencias ----
if exist ".venv\Scripts\python.exe" goto :hay_venv
echo Creando entorno virtual...
%PY% -m venv .venv
if errorlevel 1 goto :sin_venv
:hay_venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install ultralytics
if errorlevel 1 goto :sin_ultralytics

rem ---- 4) Verificacion ----
echo.
echo === Verificando el modelo en val y test ===
".venv\Scripts\python.exe" evaluacion\verify.py
if errorlevel 1 echo [AVISO] verify.py termino con errores, revisa los mensajes de arriba.
echo.
echo === Revisando fugas entre train y test ===
".venv\Scripts\python.exe" evaluacion\fugas.py
if errorlevel 1 echo [AVISO] fugas.py termino con errores, revisa los mensajes de arriba.
echo.
echo Instalacion terminada.
echo   - Camara en vivo: abrir_camara.bat
echo   - Videos del celular: procesar_videos.bat
if /i "%~1"=="/auto" goto :fin
choice /c SN /m "Abrir la webcam ahora"
if errorlevel 2 goto :fin
".venv\Scripts\python.exe" app\webcam.py
:fin
pause
exit /b 0

:sin_python
echo [ERROR] No encontre Python. Instala Python 3.10 o superior desde https://www.python.org/downloads/
echo         marcando "Add Python to PATH" y vuelve a ejecutar este archivo.
goto :error
:python_roto
echo [ERROR] El comando de Python no funciona. Si es el acceso directo de la Microsoft Store,
echo         instala Python desde python.org.
goto :error
:sin_dataset
echo [ERROR] No se pudo descargar o descomprimir el dataset. Revisa la conexion a internet.
goto :error
:sin_venv
echo [ERROR] No se pudo crear el entorno virtual.
goto :error
:sin_ultralytics
echo [ERROR] Fallo la instalacion de ultralytics y PyTorch. Revisa la conexion a internet.
goto :error
:error
pause
exit /b 1
