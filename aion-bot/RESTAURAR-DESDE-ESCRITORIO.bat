@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f "delims=" %%D in ('powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"') do set "DESK=%%D"
set "SRC=%DESK%\json"
if not exist "%SRC%" (
  echo No encuentro la carpeta "%SRC%". Usa antes GUARDAR-EN-ESCRITORIO.bat.
  pause
  exit /b 1
)
echo Devolviendo tus datos desde %SRC%
echo.
for %%F in (config.json knowledge.json guide.json skills_learned.json monsters.json routes.json game_data.json update.json) do (
  if exist "%SRC%\%%F" (
    copy /Y "%SRC%\%%F" "%~dp0" >nul
    echo   restaurado: %%F
  )
)
echo.
echo Listo. Abre INICIAR.bat.
pause
