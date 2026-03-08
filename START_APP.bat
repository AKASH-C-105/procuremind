@echo off
title ProcureMind 2.0 — AI Procurement Co-Pilot
cd /d "%~dp0"
echo.
echo  ========================================
echo   ProcureMind 2.0 — Starting up...
echo  ========================================
echo.
pip install flask flask-cors numpy -q
echo.
echo  Starting server at http://localhost:5000
echo  Opening dashboard in browser...
echo.
start "" "http://localhost:5000"
python app.py
pause
