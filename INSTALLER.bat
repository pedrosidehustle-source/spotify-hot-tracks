@echo off
chcp 65001 >nul
echo === Installation spotify_hot_tracks v1.2 (2026-10-09) ===
echo.
python --version
if errorlevel 1 (
    echo Python introuvable. Installe Python 3 depuis python.org en cochant "Add python.exe to PATH", puis relance ce fichier.
    pause
    exit /b 1
)
echo.
echo Installation de la librairie spotipy...
python -m pip install --upgrade spotipy
echo.
if not exist credentials.txt (
    copy credentials.example.txt credentials.txt >nul
    echo credentials.txt cree a partir du modele.
)
echo Installation terminee. Renseigne credentials.txt puis lance LANCER.bat
pause
