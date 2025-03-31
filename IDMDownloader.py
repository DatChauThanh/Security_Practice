import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os
import threading
from queue import Queue
import time
from urllib.parse import unquote

class EnhancedDownloadManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Download Manager")
        self.file_size = 0
        self.start_time = 0
        self.downloaded = 0
        self.create_widgets()
        self.queue = Queue()
        self.update_ui()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # URL Input
        ttk.Label(main_frame, text="Download URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(main_frame, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=2)

        # Save Path
        ttk.Label(main_frame, text="Save Path:").grid(row=1, column=0, sticky="w")
        self.path_entry = ttk.Entry(main_frame, width=50)
        self.path_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(main_frame, text="Browse", command=self.browse_file).grid(row=1, column=2)

        # Download Info
        self.info_label = ttk.Label(main_frame, text="File size: - | Progress: 0% | ETA: -")
        self.info_label.grid(row=2, column=0, columnspan=3, pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=450, mode="determinate")
        self.progress.grid(row=3, column=0, columnspan=3, pady=5)

        # Control Buttons
        self.start_btn = ttk.Button(main_frame, text="Start Download", command=self.start_download)
        self.start_btn.grid(row=4, column=1, pady=10)

        # Log Console
        self.log_text = tk.Text(main_frame, height=12, width=70, state='disabled')
        self.log_text.grid(row=5, column=0, columnspan=3, pady=5)

    def browse_file(self):
        try:
            # Auto-detect filename from URL
            url = self.url_entry.get()
            filename = self.get_filename(url)
            file_path = filedialog.asksaveasfilename(
                initialfile=filename,
                title="Save File As"
            )
            if file_path:
                self.path_entry.delete(0, tk.END)
                self.path_entry.insert(0, file_path)
        except Exception as e:
            self.log(f"Error detecting filename: {str(e)}")

    def get_filename(self, url):
        # Try to get filename from headers
        try:
            resp = requests.head(url, allow_redirects=True)
            if "Content-Disposition" in resp.headers:
                content = resp.headers["Content-Disposition"]
                filename = unquote(content.split("filename=")[1].strip('\"'))
                return filename
        except:
            pass

        # Get filename from URL
        return os.path.basename(unquote(url.split("?")[0]))

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def update_ui(self):
        while not self.queue.empty():
            msg_type, *data = self.queue.get()
            
            if msg_type == "progress":
                self.downloaded += data[0]
                percent = (self.downloaded / self.file_size) * 100
                
                # Calculate ETA
                elapsed = time.time() - self.start_time
                speed = self.downloaded / elapsed if elapsed > 0 else 0
                eta = (self.file_size - self.downloaded) / speed if speed > 0 else 0
                
                # Update progress
                self.progress["value"] = percent
                self.info_label.config(text=(
                    f"File size: {self.format_size(self.file_size)} | "
                    f"Progress: {percent:.1f}% | "
                    f"Speed: {self.format_size(speed)}/s | "
                    f"ETA: {self.format_time(eta)}"
                ))
            
            elif msg_type == "log":
                self.log(data[0])
            
            elif msg_type == "complete":
                self.start_btn["state"] = "normal"
                self.log("[✓] Download completed successfully!")
                self.info_label.config(text="Download Completed!")
            
            elif msg_type == "error":
                self.start_btn["state"] = "normal"
                self.log(f"[×] Error: {data[0]}")

        self.root.after(100, self.update_ui)

    def start_download(self):
        url = self.url_entry.get()
        output_path = self.path_entry.get()
        num_parts = 8  # Có thể thay đổi thành tuỳ chọn

        if not url or not output_path:
            messagebox.showerror("Error", "Please enter URL and save path!")
            return

        try:
            # Get file info
            self.file_size = self.get_file_size(url)
            self.downloaded = 0
            self.start_time = time.time()
            
            self.start_btn["state"] = "disabled"
            self.log(f"Starting download ({self.format_size(self.file_size)})...")
            
            threading.Thread(
                target=self.download_manager,
                args=(url, num_parts, output_path),
                daemon=True
            ).start()
            
        except Exception as e:
            self.queue.put(("error", str(e)))

    def download_manager(self, url, num_parts, output_path):
        try:
            temp_folder = "temp_parts"
            os.makedirs(temp_folder, exist_ok=True)

            # Split file
            part_size = self.file_size // num_parts
            ranges = [(i * part_size, (i+1)*part_size-1 if i != num_parts-1 else self.file_size-1)
                     for i in range(num_parts)]

            # Start threads
            threads = []
            for i, (start, end) in enumerate(ranges):
                thread = threading.Thread(
                    target=self.download_part,
                    args=(url, start, end, i, temp_folder)
                )
                threads.append(thread)
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

            # Merge files
            self.queue.put(("log", "Merging files..."))
            with open(output_path, 'wb') as f:
                for i in range(num_parts):
                    part_path = os.path.join(temp_folder, f'part_{i}')
                    with open(part_path, 'rb') as pf:
                        f.write(pf.read())
                    os.remove(part_path)
            os.rmdir(temp_folder)
            
            self.queue.put(("complete",))

        except Exception as e:
            self.queue.put(("error", str(e)))

    def download_part(self, url, start, end, part_num, temp_folder):
        try:
            headers = {'Range': f'bytes={start}-{end}'}
            response = requests.get(url, headers=headers, stream=True)
            part_path = os.path.join(temp_folder, f'part_{part_num}')
            
            with open(part_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        self.queue.put(("progress", len(chunk)))
            
            self.queue.put(("log", f"Part {part_num + 1} completed"))

        except Exception as e:
            self.queue.put(("error", f"Part {part_num} failed: {str(e)}"))

    # Utilities
    def get_file_size(self, url):
        resp = requests.head(url, allow_redirects=True)
        if 'Content-Length' in resp.headers:
            return int(resp.headers['Content-Length'])
        raise Exception("Cannot get file size")

    @staticmethod
    def format_size(size):
        units = ['B', 'KB', 'MB', 'GB']
        index = 0
        while size >= 1024 and index < 3:
            size /= 1024
            index += 1
        return f"{size:.2f} {units[index]}"

    @staticmethod
    def format_time(seconds):
        if seconds < 0:
            return "--:--:--"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedDownloadManagerApp(root)
    root.mainloop()