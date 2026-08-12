@echo off
setlocal
cd /d "%~dp0.."
set "OUTPUT_DIR=output\GodiNavi"

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found. Install requirements first.
  pause
  exit /b 1
)

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
call ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath "%OUTPUT_DIR%" "packaging\GODINAVI.spec"
if errorlevel 1 goto :failed
call ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath "%OUTPUT_DIR%" "packaging\GODINAVI_UPDATER.spec"
if errorlevel 1 goto :failed

for /f %%H in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '%OUTPUT_DIR%\GodiNavi.exe').Hash.ToLower()"') do echo %%H  GodiNavi.exe>"%OUTPUT_DIR%\GodiNavi.exe.sha256"
if not exist "%OUTPUT_DIR%\GodiNavi.exe.sha256" goto :failed

for %%D in (maps mapdata ocr_models) do (
  if exist "%OUTPUT_DIR%\%%D" rmdir /s /q "%OUTPUT_DIR%\%%D"
  xcopy "%%D" "%OUTPUT_DIR%\%%D\" /e /i /y /q >nul
  if errorlevel 1 goto :failed
)

copy /y "LICENSE.txt" "%OUTPUT_DIR%\LICENSE.txt" >nul
copy /y "map-version.json" "%OUTPUT_DIR%\map-version.json" >nul
copy /y "licenses\ASSET_NOTICE.txt" "%OUTPUT_DIR%\ASSET_NOTICE.txt" >nul
copy /y "licenses\THIRD_PARTY_NOTICES.txt" "%OUTPUT_DIR%\THIRD_PARTY_NOTICES.txt" >nul

if exist "%OUTPUT_DIR%\third_party_licenses" rmdir /s /q "%OUTPUT_DIR%\third_party_licenses"
xcopy "licenses\third_party" "%OUTPUT_DIR%\third_party_licenses\" /e /i /y /q >nul
if errorlevel 1 goto :failed

echo GodiNavi build and distribution assembly completed: %OUTPUT_DIR%
exit /b 0

:failed
echo GodiNavi build failed.
pause
exit /b 1
