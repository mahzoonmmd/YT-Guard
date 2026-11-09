@echo off
REM Build the Windows installer (run ON WINDOWS). Needs Inno Setup 6: https://jrsoftware.org/isdl.php
call build_exe.bat
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Inno Setup 6 not found. Install it, then compile installer\YTGuard.iss manually.
  pause & exit /b 1
)
%ISCC% installer\YTGuard.iss
echo.
echo Done: installer_output\YTGuard-Setup-1.0.0.exe
pause
