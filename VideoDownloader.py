import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import os
import threading
import time

class SimpleVideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Downloader")
        self.root.geometry("500x300")
        
        # Khởi tạo biến
        self.save_path = ""
        self.downloading = False
        
        # Tạo giao diện
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Phần nhập URL
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="URL trang web:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, width=40)
        self.url_entry.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Phần chọn thư mục
        dir_frame = ttk.Frame(main_frame)
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(dir_frame, text="Chọn thư mục", command=self.select_directory).pack(side=tk.LEFT)
        self.path_label = ttk.Label(dir_frame, text="Chưa chọn thư mục")
        self.path_label.pack(side=tk.LEFT, padx=5)
        
        # Thanh tiến trình
        self.progress = ttk.Progressbar(main_frame, orient='horizontal', mode='determinate')
        self.progress.pack(fill=tk.X, pady=10)
        
        # Thông tin trạng thái
        self.status_label = ttk.Label(main_frame, text="Sẵn sàng")
        self.status_label.pack()
        
        # Nút điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=10)
        
        self.download_btn = ttk.Button(control_frame, text="Bắt đầu tải", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Hủy", command=self.cancel_download).pack(side=tk.LEFT)
    
    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path = path
            self.path_label.config(text=path)
    
    def start_download(self):
        if self.downloading:
            return
            
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Lỗi", "Vui lòng nhập URL trang web")
            return
        if not self.save_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu")
            return
            
        self.downloading = True
        self.download_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()
    
    def download_video(self, url):
        try:
            ydl_opts = {
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.update_progress],
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'concurrent_fragment_downloads': 10,
                'retries': 10,
                'noprogress': True,
                'quiet': True,
            }
            
            start_time = time.time()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
            download_time = time.time() - start_time
            file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
            
            self.show_status(f"Hoàn thành! Thời gian: {download_time:.1f}s - Dung lượng: {file_size:.1f}MB")
            
        except Exception as e:
            self.show_status(f"Lỗi: {str(e)}")
        finally:
            self.downloading = False
            self.download_btn.config(state=tk.NORMAL)
            self.progress['value'] = 0
    
    def update_progress(self, d):
        if d['status'] == 'downloading':
            if d.get('total_bytes'):
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.progress['value'] = percent
                speed = d.get('speed', 0)
                self.status_label.config(text=f"Đang tải: {self.format_speed(speed)}")
    
    def format_speed(self, speed):
        if speed is None:
            return "Đang tính..."
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        for unit in units:
            if speed < 1024:
                return f"{speed:.1f} {unit}"
            speed /= 1024
        return f"{speed:.1f} GB/s"
    
    def cancel_download(self):
        if self.downloading:
            self.downloading = False
            self.show_status("Đã hủy tải!")
    
    def show_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleVideoDownloader(root)
    root.mainloop()