@echo off
cd /d "%~dp0app"
if exist "config\.deps_installed" goto run
echo Installing dependencies (first run only)...
pip install --quiet --disable-pip-version-check keyboard requests pillow mss customtkinter
if not exist "config" mkdir config
echo installed> "config\.deps_installed"
:run
start "" pythonw setup.py
exit
