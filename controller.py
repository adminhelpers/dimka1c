import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
from PIL import Image, ImageTk
import base64
from io import BytesIO
import threading
import json
import os

class WallpaperController:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Wallpaper Controller")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        self.client_host = tk.StringVar(value="192.168.1.100")  # IP клиента
        self.client_port = tk.StringVar(value="8888")
        
        self.current_image = None
        self.setup_ui()
        self.load_settings()
    
    def load_settings(self):
        """Загрузка настроек"""
        settings_file = "controller_settings.json"
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.client_host.set(settings.get('host', '192.168.1.100'))
                    self.client_port.set(settings.get('port', '8888'))
            except:
                pass
    
    def save_settings(self):
        """Сохранение настроек"""
        settings = {
            'host': self.client_host.get(),
            'port': self.client_port.get()
        }
        with open("controller_settings.json", 'w') as f:
            json.dump(settings, f)
    
    def setup_ui(self):
        """Создание интерфейса"""
        # Фрейм настроек подключения
        connection_frame = ttk.LabelFrame(self.root, text="Подключение к клиенту", padding=10)
        connection_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(connection_frame, text="IP адрес:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        ttk.Entry(connection_frame, textvariable=self.client_host, width=20).grid(row=0, column=1, padx=5)
        
        ttk.Label(connection_frame, text="Порт:").grid(row=0, column=2, sticky='w', padx=(10, 5))
        ttk.Entry(connection_frame, textvariable=self.client_port, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Button(connection_frame, text="Подключиться", command=self.connect_to_client).grid(row=0, column=4, padx=10)
        

        # Добавляем кнопку для загрузки IP из GitHub
        ttk.Button(connection_frame, text="Загрузить IP из GitHub", 
                command=self.load_ip_from_github).grid(row=0, column=5, padx=10)
                
        # Статус подключения
        self.status_label = ttk.Label(connection_frame, text="Не подключен", foreground="red")
        self.status_label.grid(row=1, column=0, columnspan=5, pady=(10, 0))
        
        # Фрейм текущих обоев
        current_frame = ttk.LabelFrame(self.root, text="Текущие обои", padding=10)
        current_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Холст для изображения
        self.image_canvas = tk.Canvas(current_frame, bg='white', height=200)
        self.image_canvas.pack(fill='both', expand=True, pady=(0, 10))
        
        # Кнопки управления
        buttons_frame = ttk.Frame(current_frame)
        buttons_frame.pack(fill='x')
        
        ttk.Button(buttons_frame, text="Обновить превью", command=self.refresh_current_wallpaper).pack(side='left', padx=(0, 10))
        ttk.Button(buttons_frame, text="Выбрать новые обои", command=self.select_new_wallpaper).pack(side='left')
        
        # Фрейм логов
        logs_frame = ttk.LabelFrame(self.root, text="Лог", padding=10)
        logs_frame.pack(fill='x', padx=10, pady=5)
        
        self.log_text = tk.Text(logs_frame, height=6, wrap='word')
        log_scrollbar = ttk.Scrollbar(logs_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
        
        # Начальная проверка подключения
        self.root.after(1000, self.connect_to_client)
    
    def log_message(self, message):
        """Добавление сообщения в лог"""
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.root.update_idletasks()
    
    def get_client_url(self):
        """Получение URL клиента"""
        return f"http://{self.client_host.get()}:{self.client_port.get()}"
    
    def connect_to_client(self):
        """Подключение к клиенту"""
        def connect():
            try:
                url = f"{self.get_client_url()}/status"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    self.status_label.config(text=f"Подключен (версия: {data.get('version', 'неизвестно')})", foreground="green")
                    self.log_message("Успешно подключен к клиенту")
                    self.save_settings()
                    
                    # Автоматически загружаем текущие обои
                    self.refresh_current_wallpaper()
                else:
                    self.status_label.config(text="Ошибка подключения", foreground="red")
                    self.log_message(f"Ошибка подключения: HTTP {response.status_code}")
            except Exception as e:
                self.status_label.config(text="Не подключен", foreground="red")
                self.log_message(f"Ошибка подключения: {str(e)}")
        
        # Запускаем в отдельном потоке
        threading.Thread(target=connect, daemon=True).start()
    
    def refresh_current_wallpaper(self):
        """Обновление превью текущих обоев"""
        def refresh():
            try:
                url = f"{self.get_client_url()}/wallpaper"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        # Декодируем base64 изображение
                        image_data = base64.b64decode(data['preview'])
                        image = Image.open(BytesIO(image_data))
                        
                        # Подгоняем размер под холст
                        canvas_width = self.image_canvas.winfo_width()
                        canvas_height = self.image_canvas.winfo_height()
                        
                        if canvas_width > 1 and canvas_height > 1:  # Холст инициализирован
                            image.thumbnail((canvas_width - 20, canvas_height - 20))
                        
                        # Конвертируем для Tkinter
                        self.current_image = ImageTk.PhotoImage(image)
                        
                        # Отображаем на холсте
                        self.image_canvas.delete("all")
                        canvas_width = self.image_canvas.winfo_width()
                        canvas_height = self.image_canvas.winfo_height()
                        x = canvas_width // 2
                        y = canvas_height // 2
                        self.image_canvas.create_image(x, y, image=self.current_image)
                        
                        self.log_message(f"Загружены текущие обои: {data.get('path', 'неизвестно')}")
                    else:
                        self.log_message(f"Ошибка получения обоев: {data.get('error', 'неизвестно')}")
                else:
                    self.log_message(f"Ошибка HTTP: {response.status_code}")
            except Exception as e:
                self.log_message(f"Ошибка обновления превью: {str(e)}")
        
        threading.Thread(target=refresh, daemon=True).start()
    
    def select_new_wallpaper(self):
        """Выбор и установка новых обоев"""
        file_path = filedialog.askopenfilename(
            title="Выберите изображение для обоев",
            filetypes=[
                ("Изображения", "*.jpg *.jpeg *.png *.bmp *.gif"),
                ("Все файлы", "*.*")
            ]
        )
        
        if file_path:
            self.upload_wallpaper(file_path)

    def load_ip_from_github(self):
        """Загрузка IP адреса из GitHub репозитория"""
        def load():
            try:
                # Здесь можно указать путь к репозиторию или сделать настройку
                github_repo = "username/repo"  # Замените на ваш репозиторий
                
                url = f"https://api.github.com/repos/{github_repo}/contents/client_info.json"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    # Декодируем содержимое файла
                    content = base64.b64decode(data['content']).decode()
                    client_info = json.loads(content)
                    
                    # Обновляем поля в интерфейсе
                    self.client_host.set(client_info['ip_address'])
                    self.client_port.set(str(client_info['port']))
                    
                    self.log_message(f"IP загружен из GitHub: {client_info['ip_address']}:{client_info['port']}")
                    self.log_message(f"Компьютер: {client_info['computer_name']}, обновлен: {client_info['last_update']}")
                    
                    # Автоматически подключаемся
                    self.connect_to_client()
                    
                else:
                    self.log_message(f"Не удалось загрузить IP из GitHub: HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_message(f"Ошибка загрузки IP из GitHub: {str(e)}")
        
        threading.Thread(target=load, daemon=True).start()

    
    def upload_wallpaper(self, file_path):
        """Загрузка нового изображения на клиент"""
        def upload():
            try:
                self.log_message(f"Загрузка изображения: {os.path.basename(file_path)}")
                
                url = f"{self.get_client_url()}/wallpaper"
                
                with open(file_path, 'rb') as f:
                    files = {'image': f}
                    response = requests.post(url, files=files, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        self.log_message("Обои успешно установлены!")
                        messagebox.showinfo("Успех", "Обои успешно установлены на удаленном компьютере!")
                        
                        # Обновляем превью через 2 секунды
                        self.root.after(2000, self.refresh_current_wallpaper)
                    else:
                        error_msg = data.get('error', 'неизвестная ошибка')
                        self.log_message(f"Ошибка установки обоев: {error_msg}")
                        messagebox.showerror("Ошибка", f"Не удалось установить обои: {error_msg}")
                else:
                    self.log_message(f"Ошибка HTTP: {response.status_code}")
                    messagebox.showerror("Ошибка", f"Ошибка сервера: HTTP {response.status_code}")
                    
            except Exception as e:
                error_msg = f"Ошибка загрузки: {str(e)}"
                self.log_message(error_msg)
                messagebox.showerror("Ошибка", error_msg)
        
        threading.Thread(target=upload, daemon=True).start()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    controller = WallpaperController()
    controller.run()
