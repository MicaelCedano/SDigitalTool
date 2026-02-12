@echo off
echo Iniciando Recibo de Garantia...
call .venv\Scripts\python.exe recibo_garantia.py
if %errorlevel% neq 0 (
    echo.
    echo OCURRIO UN ERROR. Por favor revisa el mensaje de arriba.
    echo Asegurate de haber instalado las dependencias con: pip install -r requirements.txt
    pause
)
