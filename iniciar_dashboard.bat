@echo off
title Political Sentinel ? Dashboard
echo ======================================================================
echo           POLITICAL SENTINEL ? DASHBOARD LEGISLATIVO
echo ======================================================================
echo.
echo Iniciando servidor web local en http://localhost:8000 ...
echo Presiona Ctrl+C para detener el servidor.
echo.

start "" "http://localhost:8000"
python -m http.server 8000 --directory "src\visualizador\dashboard"
