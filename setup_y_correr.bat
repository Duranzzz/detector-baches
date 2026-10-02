@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo  Detector de baches - instalacion y verificacion
echo ==============================================
echo Carpeta de trabajo: %cd%
echo.

rem ---- 1) Python ----
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo [ERROR] No encontre Python. Instala Python 3.10 o superior (probado con 3.14) desde https://www.python.org/downloads/
  echo         marcando "Add Python to PATH" y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)
%PY% --version
if errorlevel 1 (
  echo [ERROR] El comando de Python no funciona. Si es el acceso directo de la Microsoft Store,
  echo         instala Python desde python.org.
  pause
  exit /b 1
)

rem ---- 2) Repo + dataset, fijado al commit que se reviso ----
set "SHA=bd8238b0f87083a1cea658336307d15b54eb7500"
if exist "repo\dataset\images\test" (
  echo Repo y dataset ya descargados, se omite la descarga.
) else (
  echo Descargando repo + dataset, unos 640 MB, commit %SHA:~0,7% ...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/Bisman-Singh-Dev/YOLO-Pothole-Detection-Model/archive/%SHA%.zip' -OutFile 'repo.zip'; Expand-Archive -Path 'repo.zip' -DestinationPath 'repo_tmp' -Force; Move-Item -Path (Get-ChildItem 'repo_tmp').FullName -Destination 'repo'; Remove-Item 'repo.zip'; Remove-Item 'repo_tmp' -Recurse -Force"
)
if not exist "repo\dataset\images\test" (
  echo [ERROR] No se pudo descargar o descomprimir el dataset.
  pause
  exit /b 1
)

rem ---- 3) Entorno virtual + dependencias ----
if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install ultralytics
if errorlevel 1 (
  echo [ERROR] Fallo la instalacion de ultralytics / torch.
  pause
  exit /b 1
)

rem ---- 4) Verificacion ----
echo.
echo === Verificando el modelo en val y test ===
python verify.py
if errorlevel 1 echo [AVISO] verify.py termino con errores, revisa los mensajes de arriba.
echo.
echo === Revisando fugas entre train y test ===
python fugas.py
if errorlevel 1 echo [AVISO] fugas.py termino con errores, revisa los mensajes de arriba.

echo.
choice /c SN /m "Abrir la webcam ahora"
if errorlevel 2 (
  echo Listo. Para usar la camara mas tarde ejecuta abrir_camara.bat
  pause
  exit /b 0
)
python webcam.py
pause
