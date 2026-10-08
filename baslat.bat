@echo off
rem Grafik Analiz: ilk acilista sanal ortami kurar, sonra uygulamayi baslatir.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam kuruluyor...
    py -3.12 -m venv .venv || python -m venv .venv
    if errorlevel 1 (
        echo Python bulunamadi. https://www.python.org/downloads/ adresinden Python 3.12 kurun.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -m grafik_analiz uygulama
if errorlevel 1 pause
