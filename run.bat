@echo off
rem Run FlowMoney with your real data.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python app.py
if errorlevel 1 pause
