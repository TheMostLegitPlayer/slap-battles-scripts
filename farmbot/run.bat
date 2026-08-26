@echo off
cd /d "%~dp0"
pip install --quiet --disable-pip-version-check numpy mss pynput
title Slap Battles Farmbot
python farmbot.py
pause
