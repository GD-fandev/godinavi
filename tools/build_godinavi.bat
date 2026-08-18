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
call ".venv\Scripts\python.exe" "tools\verify_public_release.py"
if errorlevel 1 goto :failed
call ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath "%OUTPUT_DIR%" "packaging\GODINAVI.spec"
if errorlevel 1 goto :failed
call ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath "%OUTPUT_DIR%" "packaging\GODINAVI_UPDATER.spec"
if errorlevel 1 goto :failed

if exist "%OUTPUT_DIR%\GodiNavi.exe.sha256" del /q "%OUTPUT_DIR%\GodiNavi.exe.sha256"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -Command "$stream=[IO.File]::OpenRead('%OUTPUT_DIR%\GodiNavi.exe'); try{$bytes=[Security.Cryptography.SHA256]::Create().ComputeHash($stream)}finally{$stream.Dispose()}; $hash=([BitConverter]::ToString($bytes)).Replace('-','').ToLower(); [IO.File]::WriteAllText('%OUTPUT_DIR%\GodiNavi.exe.sha256', $hash + '  GodiNavi.exe' + [Environment]::NewLine, [Text.Encoding]::ASCII); if($hash.Length -ne 64){exit 1}"
if errorlevel 1 goto :failed
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
