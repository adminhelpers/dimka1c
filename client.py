import os
import sys
import json
import time
import winreg
import ctypes
import shutil
import logging
import requests
import threading
from flask import Flask, request, jsonify, send_file
from PIL import Image
import tempfile
import base64
from io import BytesIO
import subprocess

# Настройка логирования (в скрытый файл)
logging.basicConfig(
    filename=os.path.join(os.path.expanduser("~"), ".wallpaper_client.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class WallpaperClient:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.ERROR)  # Отключаем лишние логи Flask
        self.setup_routes()
        self.config_file = os.path.join(os.path.expanduser("~"), ".wallpaper_config.json")
        self.load_config()
        
    def load_config(self):
        """Загрузка конфигурации"""
        default_config = {
            "github_repo": "adminhelpers/dimka1c",  # Замените на ваш репозиторий
            "current_version": "1.0.0",
            "server_port": 8888,
            "check_updates_interval": 3600  # 1 час
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Сохранение конфигурации"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
    
    def add_to_startup(self):
        """Добавление в автозагрузку Windows"""
        try:
            exe_path = os.path.abspath(sys.argv[0])
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "WallpaperClient", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            logging.info("Добавлено в автозагрузку")
            return True
        except Exception as e:
            logging.error(f"Ошибка добавления в автозагрузку: {e}")
            return False
    
    def check_if_in_startup(self):
        """Проверка, добавлен ли в автозагрузку"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(key, "WallpaperClient")
            winreg.CloseKey(key)
            return True
        except:
            return False
    
    def get_current_wallpaper(self):
        """Получение текущих обоев"""
        try:
            # Получаем путь к текущим обоям
            ubuf = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.SystemParametersInfoW(73, 512, ubuf, 0)
            wallpaper_path = ubuf.value
            
            if os.path.exists(wallpaper_path):
                # Конвертируем в base64 для передачи
                with open(wallpaper_path, 'rb') as f:
                    image_data = f.read()
                
                # Создаем превью (уменьшенную версию)
                img = Image.open(BytesIO(image_data))
                img.thumbnail((300, 200))
                
                buffer = BytesIO()
                img.save(buffer, format='JPEG')
                preview_data = base64.b64encode(buffer.getvalue()).decode()
                
                return {
                    'success': True,
                    'path': wallpaper_path,
                    'preview': preview_data
                }
            else:
                return {'success': False, 'error': 'Wallpaper file not found'}
        except Exception as e:
            logging.error(f"Ошибка получения обоев: {e}")
            return {'success': False, 'error': str(e)}
    
    def set_wallpaper(self, image_path):
        """Установка обоев"""
        try:
            # Конвертируем в правильный формат если нужно
            if not image_path.lower().endswith(('.bmp', '.jpg', '.jpeg')):
                img = Image.open(image_path)
                new_path = os.path.join(tempfile.gettempdir(), "wallpaper.jpg")
                img.save(new_path, 'JPEG')
                image_path = new_path
            
            # Устанавливаем обои
            SPI_SETDESKWALLPAPER = 20
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, image_path, 3
            )
            
            if result:
                logging.info(f"Обои установлены: {image_path}")
                return True
            else:
                logging.error("Не удалось установить обои")
                return False
                
        except Exception as e:
            logging.error(f"Ошибка установки обоев: {e}")
            return False
    
    def check_for_updates(self):
        """Проверка обновлений на GitHub"""
        try:
            repo = self.config['github_repo']
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data['tag_name'].lstrip('v')
                current_version = self.config['current_version']
                
                if latest_version != current_version:
                    logging.info(f"Найдено обновление: {latest_version}")
                    return self.download_and_update(release_data)
                else:
                    logging.info("Обновлений не найдено")
                    return False
            else:
                logging.error(f"Ошибка проверки обновлений: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"Ошибка проверки обновлений: {e}")
            return False
    
    def download_and_update(self, release_data):
        """Скачивание и установка обновления"""
        try:
            # Ищем exe файл в релизе
            exe_asset = None
            for asset in release_data['assets']:
                if asset['name'].endswith('.exe'):
                    exe_asset = asset
                    break
            
            if not exe_asset:
                logging.error("Exe файл не найден в релизе")
                return False
            
            # Скачиваем новую версию
            download_url = exe_asset['browser_download_url']
            response = requests.get(download_url, stream=True)
            
            if response.status_code == 200:
                current_exe = os.path.abspath(sys.argv[0])
                new_exe = current_exe + ".new"
                
                with open(new_exe, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Обновляем версию в конфиге
                self.config['current_version'] = release_data['tag_name'].lstrip('v')
                self.save_config()
                
                # Создаем bat файл для замены exe
                bat_content = f"""
@echo off
timeout /t 2 /nobreak >nul
move "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%0"
"""
                bat_path = os.path.join(tempfile.gettempdir(), "update.bat")
                with open(bat_path, 'w') as f:
                    f.write(bat_content)
                
                # Запускаем обновление
                subprocess.Popen(bat_path, shell=True)
                logging.info("Запущено обновление")
                sys.exit(0)
                
        except Exception as e:
            logging.error(f"Ошибка обновления: {e}")
            return False
    
    def setup_routes(self):
        """Настройка API маршрутов"""
        
        @self.app.route('/status', methods=['GET'])
        def status():
            return jsonify({'status': 'running', 'version': self.config['current_version']})
        
        @self.app.route('/wallpaper', methods=['GET'])
        def get_wallpaper():
            return jsonify(self.get_current_wallpaper())
        
        @self.app.route('/wallpaper', methods=['POST'])
        def set_wallpaper_route():
            try:
                if 'image' not in request.files:
                    return jsonify({'success': False, 'error': 'No image file'})
                
                file = request.files['image']
                if file.filename == '':
                    return jsonify({'success': False, 'error': 'No file selected'})
                
                # Сохраняем временно
                temp_path = os.path.join(tempfile.gettempdir(), f"wallpaper_{int(time.time())}.jpg")
                file.save(temp_path)
                
                # Устанавливаем обои
                success = self.set_wallpaper(temp_path)
                
                return jsonify({'success': success})
                
            except Exception as e:
                logging.error(f"Ошибка API установки обоев: {e}")
                return jsonify({'success': False, 'error': str(e)})
    
    def update_checker_thread(self):
        """Поток для периодической проверки обновлений"""
        while True:
            time.sleep(self.config['check_updates_interval'])
            self.check_for_updates()
    
    def run(self):
        """Основной метод запуска"""
        logging.info("Запуск WallpaperClient")
        
        # Добавляем в автозагрузку при первом запуске
        if not self.check_if_in_startup():
            self.add_to_startup()
        
        # Запускаем поток проверки обновлений
        update_thread = threading.Thread(target=self.update_checker_thread, daemon=True)
        update_thread.start()
        
        # Проверяем обновления при запуске
        self.check_for_updates()
        
        # Запускаем веб-сервер
        try:
            self.app.run(host='0.0.0.0', port=self.config['server_port'], debug=False)
        except Exception as e:
            logging.error(f"Ошибка запуска сервера: {e}")

if __name__ == "__main__":
    client = WallpaperClient()
    client.run()
