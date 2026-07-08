@echo off
cd /d "C:\Users\zhouy\AppData\Roaming\reasonix\Investment Analysis"
set PYTHONPATH=C:\Users\zhouy\AppData\Roaming\reasonix\Investment Analysis\lib

echo [1/3] Generating dashboard JSON data...
python gen_data.py
if %errorlevel% neq 0 (
    echo ERROR: gen_data.py failed
    pause
    exit /b 1
)

echo [2/3] Building HTML dashboard...
python build_html.py
if %errorlevel% neq 0 (
    echo ERROR: build_html.py failed
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo Open dashboard.html in your browser:
echo   file:///C:/Users/zhouy/AppData/Roaming/reasonix/Investment Analysis/dashboard.html
echo.
pause
