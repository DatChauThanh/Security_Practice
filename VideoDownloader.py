import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import os
import threading
import subprocess
import json
from datetime import timedelta

class VideoProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Processor Pro")
        self.root.geometry("720x400")
        
        self.setup_variables()
        self.create_widgets()
        self.setup_bindings()
    
    def setup_variables(self):
        self.save_path = ""
        self.process_mode = tk.StringVar(value="download")
        self.current_file = ""
        self.video_duration = 0
        self.processing = False

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Phần điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(control_frame, text="Tải video", variable=self.process_mode, 
                       value="download").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(control_frame, text="Nén video", variable=self.process_mode,
                       value="compress").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(control_frame, text="Giải nén", variable=self.process_mode,
                       value="decompress").pack(side=tk.LEFT, padx=10)
        
        # Phần URL/File
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.url_entry = ttk.Entry(input_frame, width=70)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        ttk.Button(input_frame, text="Chọn file", command=self.select_file).pack(side=tk.LEFT, padx=10)
        ttk.Button(input_frame, text="Chọn thư mục", command=self.select_directory).pack(side=tk.LEFT)
        
        # Hiển thị thông tin
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        self.path_label = ttk.Label(info_frame, text="Thư mục: Chưa chọn")
        self.path_label.pack(side=tk.LEFT)
        
        self.file_label = ttk.Label(info_frame, text="File: Chưa chọn")
        self.file_label.pack(side=tk.LEFT, padx=20)
        
        # Tiến trình
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(main_frame, text="0%")
        self.progress_label.pack()
        
        self.status_label = ttk.Label(main_frame, text="Sẵn sàng")
        self.status_label.pack(pady=10)
        
        # Nút điều khiển
        ttk.Button(main_frame, text="Bắt đầu", command=self.start_process).pack()

    def setup_bindings(self):
        self.process_mode.trace_add('write', self.mode_changed)
    
    def mode_changed(self, *args):
        mode = self.process_mode.get()
        if mode == "download":
            self.url_entry.config(state=tk.NORMAL)
        else:
            self.url_entry.delete(0, tk.END)
            self.url_entry.config(state=tk.DISABLED)

    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path = path
            self.path_label.config(text=f"Thư mục: {path}")
    
    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.current_file = file_path
            self.file_label.config(text=f"File: {os.path.basename(file_path)}")
            self.get_video_duration(file_path)

    def get_video_duration(self, file_path):
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            file_path
        ]
        
        try:
            output = subprocess.check_output(cmd).decode()
            data = json.loads(output)
            self.video_duration = float(data['format']['duration'])
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc thông tin video: {str(e)}")
            self.video_duration = 0

    def start_process(self):
        if self.processing:
            return
            
        mode = self.process_mode.get()
        if mode == "download":
            self.start_download()
        elif mode == "compress":
            self.start_compression()
        elif mode == "decompress":
            self.start_decompression()

    def start_download(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Lỗi", "Vui lòng nhập URL video")
            return
        if not self.save_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu")
            return
        
        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()

    def start_compression(self):
        if not self.current_file:
            messagebox.showerror("Lỗi", "Vui lòng chọn file cần nén")
            return
        
        output_file = f"{os.path.splitext(self.current_file)[0]}_compressed.mkv"
        threading.Thread(target=self.compress_video, args=(self.current_file, output_file), daemon=True).start()

    def start_decompression(self):
        if not self.current_file:
            messagebox.showerror("Lỗi", "Vui lòng chọn file cần giải nén")
            return
        
        output_file = self.current_file.replace("_compressed", "_restored")
        threading.Thread(target=self.decompress_video, args=(self.current_file, output_file), daemon=True).start()

    def download_video(self, url):
        self.processing = True
        try:
            ydl_opts = {
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.update_progress],
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                self.current_file = ydl.prepare_filename(info)
                self.file_label.config(text=f"File: {os.path.basename(self.current_file)}")
                self.show_status("Tải thành công!")
                
        except Exception as e:
            self.show_status(f"Lỗi: {str(e)}")
        finally:
            self.processing = False

    def compress_video(self, input_path, output_path):
        self.processing = True
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx265',
                '-x265-params', 'lossless=1',
                '-preset', 'fast',
                '-c:a', 'copy',
                output_path
            ]
            
            self.run_ffmpeg_process(cmd, "Nén")
            os.replace(output_path, input_path)
            self.show_status("Nén thành công!")
            
        except Exception as e:
            self.show_status(f"Lỗi nén: {str(e)}")
        finally:
            self.processing = False

    def decompress_video(self, input_path, output_path):
        self.processing = True
        try:
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'copy',
                '-c:a', 'copy',
                output_path
            ]
            
            self.run_ffmpeg_process(cmd, "Giải nén")
            self.show_status("Giải nén thành công!")
            
        except Exception as e:
            self.show_status(f"Lỗi giải nén: {str(e)}")
        finally:
            self.processing = False

    def run_ffmpeg_process(self, cmd, process_name):
        self.progress['value'] = 0
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
                
            if 'time=' in line:
                time_str = line.split('time=')[1].split()[0]
                current_time = self.time_to_seconds(time_str)
                percent = (current_time / self.video_duration) * 100
                self.update_progress_ui(percent, process_name)
                
            if process.poll() is not None:
                break

    def time_to_seconds(self, time_str):
        h, m, s = map(float, time_str.split(':'))
        return h * 3600 + m * 60 + s

    def update_progress(self, d):
        if d['status'] == 'downloading':
            if d.get('total_bytes'):
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                self.update_progress_ui(percent, "Tải")
                
    def update_progress_ui(self, percent, process_name):
        self.progress['value'] = percent
        self.progress_label.config(text=f"{process_name}: {percent:.1f}%")
        self.root.update_idletasks()

    def show_status(self, message):
        self.status_label.config(text=message)
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoProcessorApp(root)
    root.mainloop()