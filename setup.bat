@echo off
echo Setting up Twitter Analytics Environment...

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Installing Python...
    curl -o python-installer.exe https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
    echo Installing Python - Please follow the installation wizard...
    python-installer.exe InstallAllUsers=1 PrependPath=1
    del python-installer.exe
)

:: Create and activate virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

:: Install all required Python packages
echo Installing Python packages...
python -m pip install --upgrade pip
pip install flask==2.0.1
pip install aiohttp==3.8.1
pip install pillow==9.0.0
pip install pytz==2021.3
pip install playwright==1.28.0
pip install sqlite3==2.6.0
pip install d3==0.9.0

:: Install Playwright browsers
echo Installing Playwright browsers...
playwright install

:: Create project structure
echo Creating project structure...
mkdir screenshots 2>nul
mkdir screenshots\processed 2>nul
mkdir templates 2>nul

:: Initialize SQLite database
echo Initializing database...
python -c "import sqlite3; conn = sqlite3.connect('twitter_data.db'); conn.close()"

echo.
echo Setup completed successfully!
echo.
echo To start the application:
echo 1. Run 'venv\Scripts\activate' to activate the virtual environment
echo 2. Run 'python process_manager.py' to start the application
echo.
pause