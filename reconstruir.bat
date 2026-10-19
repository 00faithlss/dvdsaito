@echo off
REM Reconstruye "DVD Saito.exe" a partir del codigo Python.
REM Usalo despues de editar cualquier archivo dentro de la carpeta saito.

cd /d "%~dp0"
echo Generando el ejecutable, esto tarda 1-2 minutos...
python -m PyInstaller --noconfirm --onefile --windowed --name "DVD Saito" ^
  --icon "saito\assets\saito.ico" ^
  --add-data "saito\assets\dvd.webp;saito\assets" ^
  --collect-all tkinterdnd2 ^
  --collect-all imageio_ffmpeg ^
  main.py

if exist "dist\DVD Saito.exe" (
    copy /Y "dist\DVD Saito.exe" "DVD Saito.exe" >nul
    echo.
    echo LISTO. Se genero "DVD Saito.exe".
) else (
    echo.
    echo ERROR: no se genero el ejecutable. Revisa los mensajes de arriba.
)
pause
