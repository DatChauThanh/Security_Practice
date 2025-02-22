import tkinter as tk
from tkinter import ttk, filedialog, messagebox, BooleanVar
import os
import subprocess
import threading
import time
from queue import Queue

class CryptoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dual-Layer Crypto")
        self.root.geometry("600x400")
        self.queue = Queue()
        self.setup_ui()
        # self.cleanup_var = BooleanVar(value=True)
        self.process_active = False
        self.current_stage = ""
        self.cancel_flag = False

    def setup_ui(self):
        # Encryption Section
        enc_frame = ttk.LabelFrame(self.root, text="Encryption")
        enc_frame.pack(pady=5, padx=10, fill="x")
        
        ttk.Button(enc_frame, text="Select Folder", 
                 command=self.select_encrypt_folder).grid(row=0, column=0, padx=5)
        self.enc_path_label = ttk.Label(enc_frame, text="No folder selected")
        self.enc_path_label.grid(row=0, column=1, sticky="w")
        
        ttk.Label(enc_frame, text="Password:").grid(row=1, column=0)
        self.encrypt_password = ttk.Entry(enc_frame, show="*", width=25)
        self.encrypt_password.grid(row=1, column=1)
        ttk.Button(enc_frame, text="Start Encryption", 
                 command=self.start_encryption).grid(row=2, column=0, columnspan=2)

        # Decryption Section
        dec_frame = ttk.LabelFrame(self.root, text="Decryption")
        dec_frame.pack(pady=5, padx=10, fill="x")
        
        ttk.Button(dec_frame, text="Select File", 
                 command=self.select_decrypt_file).grid(row=0, column=0, padx=5)
        self.dec_path_label = ttk.Label(dec_frame, text="No file selected")
        self.dec_path_label.grid(row=0, column=1, sticky="w")
        
        ttk.Label(dec_frame, text="Password:").grid(row=1, column=0)
        self.decrypt_password = ttk.Entry(dec_frame, show="*", width=25)
        self.decrypt_password.grid(row=1, column=1)
        ttk.Button(dec_frame, text="Start Decryption", 
                 command=self.start_decryption).grid(row=2, column=0, columnspan=2)

        # Progress Section
        progress_frame = ttk.LabelFrame(self.root, text="Progress")
        progress_frame.pack(pady=10, padx=10, fill="x")
        
        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", 
                                      length=400, mode="determinate")
        self.progress.pack(pady=5)
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack()
        
        # self.cleanup_check = ttk.Checkbutton(progress_frame, 
        #                                    text="Delete temporary files after completion",
        #                                    variable=self.cleanup_var)
        # self.cleanup_check.pack(pady=5)
        
        self.cancel_btn = ttk.Button(progress_frame, text="Cancel", 
                                   command=self.cancel_operation, state="disabled")
        self.cancel_btn.pack()

    def select_encrypt_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.enc_file_path = path
            self.enc_path_label.config(text=os.path.basename(path))

    def select_decrypt_file(self):
        path = filedialog.askopenfilename(filetypes=[("Encrypted Files", "*.enc.2")])
        if path:
            self.dec_file_path = path
            self.dec_path_label.config(text=os.path.basename(path))

    def update_progress(self, value=None, message=None):
        if value is not None:
            self.progress['value'] = value
        if message is not None:
            self.status_label.config(text=message)
        self.root.update_idletasks()

    def log_error(self, message):
        self.queue.put(("error", message))
        self.root.after(100, self.process_queue)

    def process_queue(self):
        while not self.queue.empty():
            msg_type, content = self.queue.get()
            if msg_type == "error":
                messagebox.showerror("Error", content)
            elif msg_type == "progress":
                self.update_progress(content[0], content[1])
        self.root.after(100, self.process_queue)

    def cancel_operation(self):
        self.cancel_flag = True
        self.status_label.config(text="Cancelling...")
        self.cancel_btn.config(state="disabled")

    def validate_openssl(self):
        try:
            subprocess.run(["openssl", "version"], check=True, 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_error("OpenSSL not found in PATH. Please install OpenSSL.")
            return False

    def encrypt(self):
        try:
            if not self.validate_openssl():
                return

            self.process_active = True
            self.cancel_btn.config(state="normal")
            folder_path = self.enc_file_path
            password = self.encrypt_password.get()
            output_file = f"{folder_path}.enc"
            final_output = f"{output_file}.2"

            # Stage 1: Compression
            self.queue.put(("progress", (0, "Compressing folder...")))
            tar_cmd = f'tar -czf - "{folder_path}"'
            compress = subprocess.Popen(tar_cmd, shell=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)

            # Stage 2: AES Encryption
            self.queue.put(("progress", (33, "AES Encryption (Layer 1)...")))
            aes_cmd = f'openssl enc -aes-256-cbc -salt -pbkdf2 -iter 10000 -pass pass:{password}'
            aes_process = subprocess.Popen(aes_cmd, stdin=compress.stdout,
                                         stdout=subprocess.PIPE, shell=True,
                                         stderr=subprocess.PIPE)

            # Stage 3: DES3 Encryption
            self.queue.put(("progress", (66, "DES3 Encryption (Layer 2)...")))
            with open(final_output, 'wb') as out_file:
                des3_cmd = f'openssl enc -des-ede3-cbc -salt -pbkdf2 -iter 11102 -pass pass:{password}'
                des3_process = subprocess.run(des3_cmd, stdin=aes_process.stdout,
                                            stdout=out_file, shell=True,
                                            stderr=subprocess.PIPE)

            if des3_process.returncode != 0:
                raise subprocess.CalledProcessError(des3_process.returncode, des3_cmd,
                                                  des3_process.stderr.decode())

            self.queue.put(("progress", (100, "Encryption complete!")))
            messagebox.showinfo("Success", f"File encrypted to: {final_output}")

        except subprocess.CalledProcessError as e:
            self.log_error(f"Encryption failed: {e.stderr.decode()}")
        except Exception as e:
            self.log_error(f"Unexpected error: {str(e)}")
        finally:
            self.process_active = False
            self.cancel_btn.config(state="disabled")
            if os.path.exists(output_file):
                os.remove(output_file)

    def decrypt(self):
        try:
            if not self.validate_openssl():
                return

            self.process_active = True
            self.cancel_btn.config(state="normal")
            enc_file = self.dec_file_path
            password = self.decrypt_password.get()
            base_name = os.path.basename(enc_file).rsplit('.', 2)[0]
            output_folder = os.path.join(os.path.dirname(enc_file), base_name)
            temp_file = os.path.join(os.path.dirname(enc_file), f"{base_name}.enc")
            tar_file = os.path.join(os.path.dirname(enc_file), f"{base_name}.tar.gz")

            # Stage 1: DES3 Decryption
            self.queue.put(("progress", (0, "DES3 Decryption (Layer 1)...")))
            des3_cmd = (f'openssl enc -d -des-ede3-cbc -pbkdf2 -iter 11102 '
                      f'-in "{enc_file}" -out "{temp_file}" -pass pass:{password}')
            des3_process = subprocess.run(des3_cmd, shell=True, stderr=subprocess.PIPE)
            if des3_process.returncode != 0:
                raise subprocess.CalledProcessError(des3_process.returncode, des3_cmd,
                                                  des3_process.stderr.decode())

            # Stage 2: AES Decryption
            self.queue.put(("progress", (33, "AES Decryption (Layer 2)...")))
            aes_cmd = (f'openssl enc -d -aes-256-cbc -pbkdf2 -iter 10000 '
                     f'-in "{temp_file}" -out "{tar_file}" -pass pass:{password}')
            aes_process = subprocess.run(aes_cmd, shell=True, stderr=subprocess.PIPE)
            if aes_process.returncode != 0:
                raise subprocess.CalledProcessError(aes_process.returncode, aes_cmd,
                                                  aes_process.stderr.decode())

            # Stage 3: Extraction
            self.queue.put(("progress", (66, "Extracting files...")))
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                
            tar_process = subprocess.run(f'tar -xzf "{tar_file}" -C "{output_folder}"',
                                       shell=True, stderr=subprocess.PIPE)
            if tar_process.returncode != 0:
                raise subprocess.CalledProcessError(tar_process.returncode, tar_process.args,
                                                  tar_process.stderr.decode())

            # Cleanup
            if self.cleanup_var.get():
                os.remove(temp_file)
                os.remove(tar_file)

            self.queue.put(("progress", (100, "Decryption complete!")))
            messagebox.showinfo("Success", f"Files extracted to: {output_folder}")

        except subprocess.CalledProcessError as e:
            self.log_error(f"Decryption failed: {e.stderr.decode()}")
        except Exception as e:
            self.log_error(f"Unexpected error: {str(e)}")
        finally:
            self.process_active = False
            self.cancel_btn.config(state="disabled")

    def start_encryption(self):
        if not hasattr(self, 'enc_file_path'):
            messagebox.showerror("Error", "Please select a folder to encrypt")
            return
        threading.Thread(target=self.encrypt, daemon=True).start()

    def start_decryption(self):
        if not hasattr(self, 'dec_file_path'):
            messagebox.showerror("Error", "Please select a file to decrypt")
            return
        threading.Thread(target=self.decrypt, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoApp(root)
    root.after(100, app.process_queue)
    root.mainloop()