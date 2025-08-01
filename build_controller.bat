@echo off
echo Building Wallpaper Controller...
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name=wallpaper_controller controller.py
echo Controller build complete! Check dist/ folder
pause
