@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\pythonw.exe" (
  echo Python environment not found. Install requirements first.
  pause
  exit /b 1
)

start "GodiNavi" ".venv\Scripts\pythonw.exe" "source\godinavi_launcher.py"
exit /b 0
