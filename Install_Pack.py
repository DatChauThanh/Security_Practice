import tkinter as tk
import importlib.util
import sys
from tkinter import ttk, messagebox, filedialog
import requests
import json
import os
import subprocess
import zipfile
import threading
from pathlib import Path

class PackInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Renesas Pack Installer")
        
        # Variables
        self.mcu_type = tk.StringVar(value="2")
        self.install_type = tk.StringVar(value="2")
        self.pack_source = tk.StringVar(value="1")
        self.pack_url = tk.StringVar()
        self.selected_pack = tk.StringVar()
        self.mcu_config = {}
        self.search_var = tk.StringVar()
        self.original_pack_list = []
        self.current_progress = 0
        
        # UI Components
        self.create_widgets()
        self.setup_mcu_config()
        self.setup_paths()

    def setup_mcu_config(self):
        self.mcu_config = {
            "1": {
                "url": 'http://pbgitap01.rea.renesas.com:81/artifactory',
                "path": "fsp-ra",
                "prefix": "",
            },
            "2": {
                "url": 'http://global-infra-jp-main.dgn.renesas.com:8081/artifactory',
                "path": "rx-driver-package/fsp_rx",
                "prefix": "RX_",  
            },
            # Temporary support RX and RA, R-CAR + RZ may not work
            "3": {
                "url": 'http://global-infra-jp-main.dgn.renesas.com:8081/artifactory',
                "path": "r-car-driver-package/fsp-w1x",
                "prefix": "",
            },
            "4": {
                "url": 'http://global-infra-jp-main.dgn.renesas.com:8081/artifactory',
                "path": "rz-driver-package/",
                "prefix": "RZT_",  # Default RZT
            }
        }

    def setup_paths(self):
        self.home = Path.home()
        self.e2studio_ws = self.home / 'e2_studio' / 'workspace'
        self.e2studio = self.home / 'e2_studio' 
        self.tmp_dir = self.home / 'tmp'
        self.tmp_dir.mkdir(exist_ok=True)
        
        # Manual path for e2studio data directory
        self.e2studio_dir = self.home / '.eclipse' / 'com.renesas.platform_1435879475' 
        # Auto path for e2studio data directory
        # self.e2studio_dir = self.get_e2studio_data_dir("e2studio.exe", self.e2studio_ws , self.e2studio)
        self.e2studio_dir.mkdir(exist_ok=True)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # My name
        ttk.Label(main_frame, text="Make By Dat Chou").grid(row=0, column=1, sticky=tk.W)
        ttk.Label(main_frame, text="aka Dev Lỏ RX ").grid(row=1, column=1, sticky=tk.W)

        # MCU Selection
        ttk.Label(main_frame, text="Select MCU Type:").grid(row=0, column=0, sticky=tk.W)
        mcu_options = [
            ("RA FSP", "1"),
            ("RX FSP", "2"),
            ("RCAR FSP", "3"),
            ("RZ FSP", "4")
        ]
        for i, (text, val) in enumerate(mcu_options):
            ttk.Radiobutton(main_frame, text=text, variable=self.mcu_type, 
                           value=val).grid(row=i+1, column=0, sticky=tk.W)

        # Install Type
        ttk.Label(main_frame, text="Install Type:").grid(row=5, column=0, sticky=tk.W)
        ttk.Radiobutton(main_frame, text="Clean Install", variable=self.install_type, 
                        value="1").grid(row=6, column=0, sticky=tk.W)
        ttk.Radiobutton(main_frame, text="Add New Packs", variable=self.install_type,
                        value="2").grid(row=7, column=0, sticky=tk.W)

        # Pack Source
        ttk.Label(main_frame, text="Pack Source:").grid(row=8, column=0, sticky=tk.W)
        ttk.Radiobutton(main_frame, text="Custom URL", variable=self.pack_source,
                       value="1", command=self.toggle_url_entry).grid(row=9, column=0, sticky=tk.W)
        ttk.Radiobutton(main_frame, text="Artifactory", variable=self.pack_source,
                       value="2", command=self.toggle_artifactory).grid(row=10, column=0, sticky=tk.W)
        
        # URL Entry
        self.url_frame = ttk.Frame(main_frame)
        ttk.Label(self.url_frame, text="Pack URL:").grid(row=0, column=0)
        self.url_entry = ttk.Entry(self.url_frame, width=50, textvariable=self.pack_url)
        self.url_entry.grid(row=0, column=1)
        
        # Artifactory Browser
        self.artifactory_frame = ttk.Frame(main_frame)
        ttk.Label(self.artifactory_frame, text="Available Packs:").grid(row=0, column=0)
        self.pack_list = tk.Listbox(self.artifactory_frame, height=10, width=50)
        self.pack_list.grid(row=1, column=0)
        self.pack_list.bind('<<ListboxSelect>>', self.on_pack_select)

        # Progress components
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", 
                                      length=400, mode="determinate")
        self.status_label = ttk.Label(main_frame, text="Ready")
        
        # Grid progress components
        self.status_label.grid(row=14, column=0, columnspan=2, pady=5)
        self.progress.grid(row=15, column=0, columnspan=2, pady=10)

        # Action Buttons
        ttk.Button(main_frame, text="Install", command=self.start_installation).grid(row=12, column=0, pady=10)
        ttk.Button(main_frame, text="Exit", command=self.root.destroy).grid(row=12, column=1)

    def validate_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def check_directory_permissions(self):
        try:
            test_file = self.tmp_dir / "permission_test.txt"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception as e:
            messagebox.showerror("Permission Error", 
                f"Cannot write to directory: {self.tmp_dir}\n{str(e)}")
            return False

    def start_installation(self):
        if not self.validate_environment():
            return
        if not self.check_directory_permissions():
            return
            
        self.progress.grid(row=13, column=0, columnspan=2, pady=10)
        self.progress.start()
        
        threading.Thread(target=self.install_packs).start()

    def install_packs(self):
        try:
            self.kill_e2studio()
            self.update_progress(0, "Starting installation...")
            
            # Select MCU Family
            config = self.mcu_config[self.mcu_type.get()]
            
            if self.pack_source.get() == "2":
                selected_path = self.selected_pack.get()
                if not selected_path:
                    raise ValueError("No pack selected")
                
                parts = selected_path.split('/')
                if parts[0] == 'release':
                    version = parts[1]
                    url = f"{config['url']}/{config['path']}/release/{version}/packs/{config['prefix']}FSP_Packs_{version}.zip"
                    url2= url.replace("Packs", "Packs_INTERNAL")
                else:
                    branch = parts[1]
                    build_url = f"{config['url']}/api/storage/{config['path']}/manual/{branch}"
                    response = requests.get(build_url)
                    builds = json.loads(response.text)['children']
                    build_names = [item['uri'].strip('/') for item in builds]
                    latest_build = sorted(build_names, reverse=True)[0]
                    
                    packs_url = f"{config['url']}/api/storage/{config['path']}/manual/{branch}/{latest_build}/packs"
                    response = requests.get(packs_url)
                    pack_files = [item['uri'].strip('/') for item in json.loads(response.text)['children']]
                    pack_name = next((f for f in pack_files if f.startswith(config['prefix'])), None)
                    
                    if not pack_name:
                        raise ValueError("No valid pack found")
                        
                    url = f"{config['url']}/{config['path']}/manual/{branch}/{latest_build}/packs/{pack_name}"
                    url2= url.replace("_INTERNAL", "")
            else:
                url = self.pack_url.get()
                if not self.validate_url(url):
                    raise ValueError("Invalid URL format")
                

            # Download files
            self.update_progress(5, "Starting downloads...")
            
            zip_name = url.split('/')[-1]
            zip_name_2 = url.split('/')[-1] + "2"
            
            zip_path = self.tmp_dir / zip_name
            zip_path2 = self.tmp_dir / zip_name_2

             # Download main pack
            download_thread1 = threading.Thread(
                target=self.download_file, args=(url, zip_path))
            download_thread1.start()
            download_thread1.join()
            
            # Download internal pack
            self.update_progress(30, "Downloading internal packs...")
            download_thread2 = threading.Thread(
                target=self.download_file, args=(url2, zip_path2))
            download_thread2.start()
            download_thread2.join()
            
            # Check zip files
            self.update_progress(60, "Verifying packages...")
            if not zipfile.is_zipfile(zip_path):
                raise ValueError("Invalid zip internal file")
            if not zipfile.is_zipfile(zip_path2):
                raise ValueError("Invalid zip file")

            # Extract files
            self.update_progress(70, "Extracting main package...")
            self.install_zip(zip_path)
            self.update_progress(85, "Extracting internal package...")
            self.install_zip(zip_path2)

            # Clean up
            self.update_progress(95, "Cleaning up...")
            zip_path.unlink()
            zip_path2.unlink()
            
            self.update_progress(100, "Installation complete!")
            messagebox.showinfo("Success", "Installation completed!")
            
        except Exception as e:
            messagebox.showerror("Error", f"{str(e)}\n\nCheck logs for details")
        finally:
            self.progress['value'] = 0
            self.status_label.config(text="Ready")
    
    def toggle_url_entry(self):
        self.artifactory_frame.grid_forget()
        self.url_frame.grid(row=11, column=0, columnspan=2, pady=5)

    def toggle_artifactory(self):
        self.url_frame.grid_forget()
        self.artifactory_frame.grid(row=11, column=0, columnspan=2, pady=5)
        self.load_artifactory_packs()

    def load_artifactory_packs(self):
        try:
            config = self.mcu_config[self.mcu_type.get()]
            base_url = f"{config['url']}/api/storage/{config['path']}"
            
            # Take list manual and release
            manual_url = f"{base_url}/manual"
            release_url = f"{base_url}/release"
            
            packs = []
            
            # Take manual builds
            response = requests.get(manual_url)
            if response.status_code == 200:
                manual_data = json.loads(response.text)
                packs.extend([f"manual/{item['uri'].strip('/')}" for item in manual_data.get('children', [])])
            
            # Take release builds
            response = requests.get(release_url)
            if response.status_code == 200:
                release_data = json.loads(response.text)
                packs.extend([f"release/{item['uri'].strip('/')}" for item in release_data.get('children', [])])
            
            self.pack_list.delete(0, tk.END)
            for pack in packs:
                self.pack_list.insert(tk.END, pack)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load packs: {str(e)}")

    def on_pack_select(self, event):
        selection = self.pack_list.curselection()
        if selection:
            self.selected_pack.set(self.pack_list.get(selection[0]))

    def validate_environment(self):
        # Check dependencies and install if any
        if importlib.util.find_spec("requests") is None:
            print("The 'requests' library is missing. Installing it now...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        else:
            print("'requests' is already installed.")

        try:
            subprocess.run(['fzf', '--version'], check=True)
            subprocess.run(['jq', '--version'], check=True)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Missing dependency: {str(e)}")
            return False

    def start_installation(self):
        if not self.validate_environment():
            return
            
        self.progress.grid(row=13, column=0, columnspan=2, pady=10)
        self.progress.start()
        
        # Run thread to not block UI
        threading.Thread(target=self.install_packs).start()

    def kill_e2studio(self):
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'e2studio.exe'], check=True)
        except subprocess.CalledProcessError:
            pass

    def download_file(self, url, save_path):
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                self.update_progress(0, f"Downloading {url.split('/')[-1]}")
                
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = int((downloaded / total_size) * 25)
                            self.update_progress(
                                self.current_progress + progress,
                                f"Downloading {url.split('/')[-1]} ({downloaded/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB)"
                            )
                return True
        except Exception as e:
            raise RuntimeError(f"Download failed: {str(e)}")

    def install_zip(self, zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.e2studio_dir)
        except Exception as e:
            raise RuntimeError(f"Extraction failed: {str(e)}")

    def update_progress(self, value, message):
        self.current_progress = value
        self.progress['value'] = value
        self.status_label.config(text=message)
        self.root.update_idletasks()

    # def get_e2studio_data_dir(self, e2studio_app, workspace_dir, script_dir):
    #     tmp_dir = Path.home() / "tmp"

    #     log_file = tmp_dir / "e2studio.log"
    #     support_area_file = tmp_dir / "e2-support-area.log"

    #     # Run the e2studio command to retrieve the data directory path
    #     cmd = [
    #         e2studio_app,
    #         "--launcher.suppressErrors",
    #         "-nosplash",
    #         "-application", "org.eclipse.ease.runScript",
    #         "-data", workspace_dir,
    #         "-script", f"{script_dir}/scripts/get_support_area.py",
    #         str(support_area_file)
    #     ]

    #     with open(log_file, "w") as log:
    #         subprocess.run(cmd, stdout=log, stderr=log, check=True)

    #     # Read the data directory path from the log file
    #     if support_area_file.exists():
    #         return support_area_file.read_text().strip()
    #     else:
    #         raise RuntimeError("Failed to determine the e2 studio data directory.")    

if __name__ == "__main__":
    root = tk.Tk()
    app = PackInstallerApp(root)
    root.mainloop()