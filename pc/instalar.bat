@echo off
py -m pip install --upgrade pymobiledevice3 sounddevice deepfilter-stream numpy pystray pillow
if errorlevel 1 (
  echo Falha ao instalar dependencias. Confira se o Python foi instalado e esta no PATH.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0configurar-inicializacao.ps1"
pause
