@echo off
chcp 65001 >nul
cd /d "%~dp0"
python spotify_hot_tracks.py
