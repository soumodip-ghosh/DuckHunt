@echo off
REM Launcher for Duck Hunt (Windows batch)
SETLOCAL
echo Installing dependencies (requirements.txt)...
python -m pip install -r "%~dp0requirements.txt"
echo Starting Duck Hunt...
python "%~dp0duck_hunt.py" %*
echo.
pause
ENDLOCAL
