@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 start_server.py
  goto :eof
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python start_server.py
  goto :eof
)

start "" "%~dp0index.html"
