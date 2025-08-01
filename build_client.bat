@echo off
echo Building Wallpaper Client...
pip install -r client_requirements.txt
pyinstaller --onefile --noconsole --hidden-import=PIL._tkinter_finder --name=wallpaper_client client.py
echo Client build complete! Check dist/ folder
pause