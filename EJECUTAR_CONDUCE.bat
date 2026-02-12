@echo off
echo Iniciando Generador de Conduces...
call .venv\Scripts\python.exe pdfconduce.py
if %errorlevel% neq 0 (
    echo.
    echo OCURRIO UN ERROR. Por favor revisa el mensaje de arriba.
    echo Asegurate de haber instalado las dependencias con: pip install -r requirements.txt
    pause
)
