@echo off
title Generador de Conduces WEB
echo ==========================================
echo      INICIANDO VERSION WEB (STREAMLIT)
echo ==========================================

:: Solución robusta de rutas
set VENV_PYTHON=.venv\Scripts\python.exe

if not exist "%VENV_PYTHON%" (
    echo [ERROR] No se detecto el entorno virtual en:
    echo "%VENV_PYTHON%"
    echo.
    echo Buscando opcion de respaldo...
    set VENV_PYTHON=python
)

echo.
echo 1. Verificando librerias...
"%VENV_PYTHON%" -m pip install streamlit

echo.
echo 2. Iniciando Aplicacion...
echo    (Se abrira una ventana en tu navegador web)
echo.
"%VENV_PYTHON%" -m streamlit run app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR CRITICO] La aplicacion se cerro inesperadamente.
    echo Posibles causas:
    echo - No tienes internet (necesario para la primera instalacion)
    echo - El archivo 'app.py' no existe
    pause
)
pause
