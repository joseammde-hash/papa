@echo off
chcp 65001 >nul
echo Instalando dependencias del bot...
python -m pip install pyautogui pynput pillow
echo.
echo Listo. Ahora abre INICIAR.bat
pause
