@echo off
rem Run FlowMoney with SAMPLE data in a separate folder. Your real data is not touched.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set "FLOWMONEY_DATA_DIR=%TEMP%\FlowMoneyDemo"
python scripts\seed_demo.py
if errorlevel 1 (pause & exit /b 1)
python app.py
if errorlevel 1 pause
