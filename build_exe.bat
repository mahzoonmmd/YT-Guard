@echo off
REM Build a Windows .exe (run this ON WINDOWS, in this folder)
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt pyinstaller pillow
python make_icon.py
pyinstaller --noconfirm --windowed --name YTGuard --icon assets\icon.ico ^
  --add-data "assets;assets" --collect-all imageio_ffmpeg main.py
echo.
echo Done: dist\YTGuard\YTGuard.exe

