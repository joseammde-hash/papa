@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f "delims=" %%D in ('powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"') do set "DESK=%%D"
set "DEST=%DESK%\json"
mkdir "%DEST%" 2>nul
echo Copiando tus datos a %DEST%
echo.
for %%F in (config.json knowledge.json guide.json skills_learned.json monsters.json routes.json game_data.json update.json) do (
  if exist "%%F" (
    copy /Y "%%F" "%DEST%\" >nul
    echo   copiado: %%F
  )
)
echo.
echo Listo. Tus archivos estan en la carpeta "json" del Escritorio.
pause
