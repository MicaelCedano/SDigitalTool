@echo off
echo Iniciando Conduce con IMEIs...
call .venv\Scripts\python.exe pdfconduce_imeis.py
if %errorlevel% neq 0 (
    echo.
    echo OCURRIO UN ERROR. Por favor revisa el mensaje de arriba.
    echo Asegurate de haber instalado las dependencias con: pip install -r requirements.txt
    pause
)
