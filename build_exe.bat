@echo off
rem Rebuild dist\FlowMoney.exe from the current code.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m pip install --upgrade pyinstaller
pyinstaller FlowMoney.spec --noconfirm
if errorlevel 1 (echo. & echo BUILD FAILED) else (echo. & echo BUILD OK: dist\FlowMoney.exe)
pause
