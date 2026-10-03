@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONNOUSERSITE=1
set "PY=%~dp0python\python.exe"
if not exist "%PY%" (
  echo.
  echo   没找到自带的 Python:python\python.exe
  echo   这个包要**完整解压**之后再运行,不要直接在压缩包里双击。
  echo.
  pause
  exit /b 1
)
"%PY%" "_tools\tui_live.py" %*
if errorlevel 1 pause
