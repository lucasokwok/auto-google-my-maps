@echo off
setlocal

rem Mantenha a copia na raiz do repositorio ou ajuste PROJETO para o caminho da raiz.
set "PROJETO=%~dp0"
set "PERFIL_MYMAPS=%LOCALAPPDATA%\auto-google-my-maps\edge-profile"

cd /d "%PROJETO%" || exit /b 2
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente virtual ausente. Confira as instrucoes de instalacao no README. 1>&2
    exit /b 2
)

".venv\Scripts\python.exe" -m auto_googlemymaps atualizar --navegador edge --perfil-dir "%PERFIL_MYMAPS%"
exit /b %ERRORLEVEL%
