import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import subprocess
import csv
import re
import json
import time
import sys
import zipfile
from datetime import timedelta
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4, MP4Tags
from tkinter import ttk
# Optional drag & drop support import
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _tkdnd_imported = True
except ImportError:
    _tkdnd_imported = False
# Will determine DND availability at runtime
DND_AVAILABLE = False
from pathlib import PureWindowsPath
import webbrowser
import platform

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)

CONFIG_FILE = resource_path('config.json')

def load_config():
    default = {
        'variants': ['Official Audio', ''],
        'duration_min': 60,
        'duration_max': 600
    }
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                return {**default, **cfg}
        except:
            return default
    return default

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind('<Enter>', self.show)
        widget.bind('<Leave>', self.hide)
    def show(self, _):
        if self.tip or not self.text:
            return
        x,y,_cx,cy = self.widget.bbox('insert')
        x += self.widget.winfo_rootx() + 25
        y += cy + self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f'+{x}+{y}')
        tk.Label(self.tip, text=self.text, bg='yellow', relief='solid', bd=1).pack()
    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None

class Spotify2MP3GUI:
    def __init__(self, root):
        self.root = root
        self.root.title('Spotify2MP3')
        self.root.geometry('600x600')
        self.root.minsize(520, 500)
        self.csv_path = None
        self.output_folder = None
        self.last_output_dir = None
        
        # Set initial directory to Downloads folder
        if platform.system() == "Windows":
            self.last_directory = os.path.join(os.path.expanduser("~"), "Downloads")
        else:
            self.last_directory = os.path.expanduser("~/Downloads")
            
        self.config = load_config()

        self.setup_ui()
        if sys.platform == 'darwin':
            icon_path = resource_path('icon.icns')  # macOS icon
        else:
            icon_path = resource_path('icon.ico')   # Windows icon
        try:
            if sys.platform == 'darwin':
                # macOS specific icon handling
                img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, img)
            else:
                self.root.iconbitmap(icon_path)     # Windows-friendly .ico
        except Exception as e:
            print(f"Warning: Could not load icon: {e}")
            # No fallback needed - app will run without icon
        if _tkdnd_imported:
            try:
                root.drop_target_register(DND_FILES)
                root.dnd_bind('<<Drop>>', self.handle_drop)
                global DND_AVAILABLE; DND_AVAILABLE = True
            except:
                DND_AVAILABLE = False
        if not DND_AVAILABLE:
            Tooltip(self.drop_frame, 'Drag & drop not available\nInstall tkinterdnd2 to enable.')

    def setup_ui(self):
        instr = tk.Label(self.root, text='Download CSV via Exportify: https://exportify.net/', fg='blue', cursor='hand2')
        instr.pack(fill='x', padx=20)
        instr.bind('<Button-1>', lambda e: webbrowser.open('https://exportify.net/'))

        # CSV Input
        tk.Label(self.root, text='1) CSV File:', anchor='w').pack(fill='x', padx=20)
        self.drop_frame = tk.Frame(self.root, bg='#e0e0e0', height=180)
        self.drop_frame.pack(pady=5, padx=20, fill='x')
        self.drop_label = tk.Label(self.drop_frame, text='CSV file: None', bg='#e0e0e0')
        self.drop_label.pack(expand=True, fill='both')
        self.drop_label.bind('<Button-1>', self.browse_csv)
        Tooltip(self.drop_frame, 'Drop your Exportify CSV here or click to browse.')

        # Output folder
        tk.Label(self.root, text='2) Output Folder:', anchor='w').pack(fill='x', padx=20)
        self.folder_button = tk.Button(self.root, text='Choose Output Folder', command=self.select_output_folder)
        self.folder_button.pack(pady=5)
        self.output_label = tk.Label(self.root, text='Output folder: Not selected', anchor='w')
        self.output_label.pack(fill='x', padx=20)
        Tooltip(self.folder_button, 'Where files will be saved.')

        # Conversion options
        tk.Label(self.root, text='3) Conversion Options:', anchor='w').pack(fill='x', padx=20)
        self.mp3_var = tk.BooleanVar(value=False)
        self.mp3_check = tk.Checkbutton(self.root, text='Transcode to MP3 (for MP3-only players)', variable=self.mp3_var)
        self.mp3_check.pack(pady=2)
        Tooltip(self.mp3_check, 'Enable to re-encode into MP3. Default is M4A remux.')
        self.quality_var = tk.BooleanVar(value=True)
        self.quality_check = tk.Checkbutton(self.root, text='High quality (VBR0)', variable=self.quality_var)
        self.quality_check.pack(pady=2)
        Tooltip(self.quality_check, 'Only applies when transcoding to MP3.')
        self.m3u_var = tk.BooleanVar(value=True)
        self.m3u_check = tk.Checkbutton(self.root, text='Generate M3U playlist', variable=self.m3u_var)
        self.m3u_check.pack(pady=2)
        Tooltip(self.m3u_check, 'Create a .m3u playlist file.')
        self.thumb_var = tk.BooleanVar(value=False)
        self.thumb_check = tk.Checkbutton(self.root, text='Embed thumbnails as cover art', variable=self.thumb_var)
        self.thumb_check.pack(pady=2)
        Tooltip(self.thumb_check, 'Fetch and embed video thumbnails into the audio file.')

        # Spotify album art option
        self.spotify_art_var = tk.BooleanVar(value=False)
        self.spotify_art_check = tk.Checkbutton(self.root, text='Get album art from Spotify (Requires Chrome)', variable=self.spotify_art_var)
        self.spotify_art_check.pack(pady=2)
        Tooltip(self.spotify_art_check, 'Download album art from Spotify using spotifycover.art')
        
        # Spotify link input
        self.spotify_link_frame = tk.Frame(self.root)
        self.spotify_link_frame.pack(fill='x', padx=20)
        self.spotify_link_label = tk.Label(self.spotify_link_frame, text='Spotify Link:')
        self.spotify_link_label.pack(side='left')
        self.spotify_link_entry = tk.Entry(self.spotify_link_frame)
        self.spotify_link_entry.pack(side='left', fill='x', expand=True, padx=(5,0))
        self.spotify_link_entry.insert(0, 'https://open.spotify.com/playlist/')
        self.spotify_link_entry.config(state='normal')
        Tooltip(self.spotify_link_entry, 'Enter Spotify playlist/album link')

        self.convert_button = tk.Button(self.root, text='Convert Playlist', command=self.start_conversion, state=tk.DISABLED)
        self.convert_button.pack(pady=10)
        self.clear_button = tk.Button(self.root, text='Clear', command=self.clear_selection, state=tk.DISABLED)
        self.clear_button.pack()

        # Actions
        tk.Label(self.root, text='4) Actions:', anchor='w').pack(fill='x', padx=20, pady=(10,0))
        self.open_folder_button = tk.Button(self.root, text='Open Output Folder', command=self.open_output_folder)
        self.open_folder_button.pack(pady=5)
        Tooltip(self.open_folder_button, 'Open folder with converted files.')

        # Progress
        self.progress = ttk.Progressbar(self.root, orient='horizontal', length=500, mode='determinate')
        self.progress.pack(pady=10)
        self.status_label = tk.Label(self.root, text='Status: Waiting...', anchor='w')
        self.status_label.pack(fill='x', padx=20)

    def open_settings(self):
        # ... existing settings code ...
        pass

    def update_convert_button_state(self):
        ok = self.csv_path and os.path.isfile(self.csv_path) and self.csv_path.lower().endswith('.csv') and self.output_folder
        self.convert_button.config(state=tk.NORMAL if ok else tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL if self.csv_path else tk.DISABLED)

    def clear_selection(self):
        self.csv_path = None
        self.drop_label.config(text='CSV file: None')
        self.progress['value'] = 0
        self.status_label.config(text='Status: Waiting...')
        self.update_convert_button_state()

    def browse_csv(self, event=None):
        path = filedialog.askopenfilename(
            initialdir=self.last_directory,
            filetypes=[('CSV files','*.csv')]
        )
        if path:
            self.csv_path = path
            self.last_directory = os.path.dirname(path)  # Update last directory
            self.drop_label.config(text=f'CSV file: {os.path.basename(path)}')
            self.status_label.config(text='CSV loaded.')
            self.update_convert_button_state()

    def select_output_folder(self):
        path = filedialog.askdirectory(initialdir=self.last_directory)
        if path:
            self.output_folder = path
            self.last_directory = path  # Update last directory
            self.output_label.config(text=f'Output folder: {path}')
            self.status_label.config(text='Output folder selected.')
            self.update_convert_button_state()

    def open_output_folder(self):
        target = self.last_output_dir or self.output_folder
        if target and os.path.isdir(target):
            os.startfile(target)
        else:
            messagebox.showerror('Error', 'No valid folder to open.')

    def start_conversion(self):
        if not (self.csv_path and self.output_folder):
            messagebox.showerror('Error', 'Select CSV and output folder.')
            return
        self.convert_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.root.config(cursor='watch')
        threading.Thread(target=self.convert_playlist, daemon=True).start()

    def handle_drop(self, event):
        path = event.data.strip('{}')
        if path.lower().endswith('.csv'):
            self.csv_path = path
            self.drop_label.config(text=f'CSV file: {os.path.basename(path)}')
            self.status_label.config(text='CSV loaded via drag.')
            self.update_convert_button_state()

    def get_file_timestamps(self, file_path):
        return {
            'created': os.path.getctime(file_path),
            'modified': os.path.getmtime(file_path)
        }

    def set_file_timestamps(self, file_path, timestamps):
        os.utime(file_path, (timestamps['modified'], timestamps['modified']))
        # Note: Creation time can't be directly set on Unix systems, but we preserve it where possible

    def embed_artwork(self, audio_file, jpg_file):
        print(f"\nEmbedding artwork for: {audio_file}")
        print(f"Using artwork: {jpg_file}")
        
        # Save original timestamps
        timestamps = self.get_file_timestamps(audio_file)
        
        # Create temp file in the same directory as the audio file
        audio_dir = os.path.dirname(audio_file)
        audio_filename = os.path.basename(audio_file)
        temp_output = os.path.join(audio_dir, f"temp_{audio_filename}")
        
        cmd = [
            'ffmpeg', '-i', audio_file,
            '-i', jpg_file,
            '-map', '0:a',
            '-map', '1:v',
            '-c:a', 'copy',
            '-c:v', 'mjpeg',
            '-disposition:v:0', 'attached_pic',
            temp_output
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            os.replace(temp_output, audio_file)
            # Restore original timestamps
            self.set_file_timestamps(audio_file, timestamps)
            print(f"Successfully embedded artwork for {audio_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {audio_file}: {e.stderr.decode()}")
            if os.path.exists(temp_output):
                os.remove(temp_output)

    def get_modified_time(self, file_path):
        return os.path.getmtime(file_path)

    def clean_filename_for_artwork(self, filename):
        # Remove file extension
        filename = os.path.splitext(filename)[0]
        return filename

    def get_jpg_number(self, filename):
        # Extract the number prefix from jpg files (e.g., "1_" or "42_")
        match = re.match(r'^(\d+)_', filename)
        return int(match.group(1)) if match else float('inf')

    def rename_album_art(self, output_dir):
        # Get all audio files (MP3 and M4A) and JPG files
        audio_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.mp3', '.m4a'))]
        jpg_files = [f for f in os.listdir(output_dir) if f.endswith('.jpg')]
        
        # Sort audio files by modification time
        audio_files.sort(key=lambda x: self.get_modified_time(os.path.join(output_dir, x)))
        
        # Sort JPG files by their number prefix
        jpg_files.sort(key=self.get_jpg_number)
        
        # Make sure we have the same number of files
        if len(audio_files) != len(jpg_files):
            print(f"Warning: Number of files doesn't match! Audio files: {len(audio_files)}, JPG: {len(jpg_files)}")
            print("Will process as many files as possible.")
        
        # Process files in pairs
        for i, (audio_file, jpg_file) in enumerate(zip(audio_files, jpg_files)):
            print(f"\nProcessing pair {i + 1}:")
            print(f"Audio file: {audio_file}")
            print(f"Current JPG: {jpg_file}")
            
            # Generate new jpg filename based on audio filename
            new_jpg_name = self.clean_filename_for_artwork(audio_file) + '.jpg'
            print(f"New JPG name: {new_jpg_name}")
            
            try:
                os.rename(
                    os.path.join(output_dir, jpg_file),
                    os.path.join(output_dir, new_jpg_name)
                )
                print(f"Successfully renamed {jpg_file} to {new_jpg_name}")
            except Exception as e:
                print(f"Error renaming file: {e}")

    def embed_all_artwork(self, output_dir):
        # Get all audio files (both M4A and MP3)
        audio_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.m4a', '.mp3'))]
        for audio_file in audio_files:
            jpg_file = os.path.splitext(audio_file)[0] + '.jpg'
            jpg_path = os.path.join(output_dir, jpg_file)
            if os.path.exists(jpg_path):
                self.embed_artwork(os.path.join(output_dir, audio_file), jpg_path)
            else:
                print(f"No matching artwork found for {audio_file} (expected {jpg_file})")

    def convert_playlist(self):
        start_time = time.time()
        self.status_label.config(text='Starting conversion...')
        playlist_name = os.path.splitext(os.path.basename(self.csv_path))[0]
        output_dir = os.path.join(self.output_folder, playlist_name)
        os.makedirs(output_dir, exist_ok=True)
        self.last_output_dir = output_dir
        downloaded = []

        # Handle Spotify album art if enabled
        if self.spotify_art_var.get():
            try:
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                import tempfile
                import shutil
            
                spotify_link = self.spotify_link_entry.get()
                if not spotify_link or spotify_link == 'https://www.spotifycover.art':
                    messagebox.showerror('Error', 'Please enter a valid Spotify link')
                    return
                
                # Create a temporary directory for album art
                temp_dir = tempfile.mkdtemp()
                
                # Setup Chrome options
                chrome_options = webdriver.ChromeOptions()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                
                chrome_paths = [
                        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS
                        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',   # Windows
                        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'  # Windows (x86)
                ]
                    
                chrome_found = False
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_options.binary_location = path
                        chrome_found = True
                        break
                    
                    if not chrome_found:
                        messagebox.showerror('Error', 'Google Chrome not found. Please install Chrome browser to use this feature.')
                        return
                
                # Initialize the Chrome driver
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Navigate to spotifycover.art
                driver.get('https://www.spotifycover.art')
                
                # Wait for the input box to be present
                input_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea#linkInput'))
                )
                
                # Clear the input box and enter the Spotify link
                input_box.send_keys(spotify_link)
                input_box.send_keys(Keys.RETURN)
                
                # Wait for the download button to be present and click it
                download_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#downloadAllBtn"))
                )
                download_button.click()
                
                # Wait for the download to complete (you might need to adjust this based on the website's behavior)
                time.sleep(10)
                driver.quit()
                
                # Find and move zip file from downloads to output directory
                if platform.system() == "Windows":
                    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                else:
                    downloads_dir = os.path.expanduser("~/Downloads")
                    
                for file in os.listdir(downloads_dir):
                    if file.endswith('.zip'):
                        zip_path = os.path.join(downloads_dir, file)
                        new_zip_path = os.path.join(output_dir, file)
                        shutil.move(zip_path, new_zip_path)
                        
                        # Extract zip file
                        with zipfile.ZipFile(new_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(output_dir)
                        os.remove(new_zip_path)
                
                # Move extracted jpg files to output directory        
                for file in os.listdir(output_dir):
                    if file.endswith('.jpg'):
                        # Files are already in output_dir, no need to move
                        pass
            except Exception as e:
                messagebox.showerror('Error', f'Failed to download Spotify album art: {str(e)}')
                return

        cfg = self.config
        if platform.system() == "Darwin":  # macOS
            ffmpeg_path = resource_path("ffmpeg")
            ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg")
            yt_dlp_path = resource_path("yt-dlp")
            yt_dlp_exe = os.path.join(yt_dlp_path, "yt-dlp")
        else:
            ffmpeg_path = resource_path("ffmpeg")
            ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")
            yt_dlp_path = resource_path("yt-dlp")
            yt_dlp_exe = os.path.join(yt_dlp_path, "yt-dlp.exe" if platform.system() == "Windows" else "yt-dlp")

        if not os.path.isfile(ffmpeg_exe):
            messagebox.showerror("Missing FFmpeg","ffmpeg not found. Please install FFmpeg and ensure it's in your PATH.")
            return

        if not os.path.isfile(yt_dlp_exe):
            messagebox.showerror("Missing yt-dlp","yt-dlp not found. Please install yt-dlp and ensure it's in your PATH.")
            return

        log_path = os.path.join(output_dir, 'error.log')
        rows = list(csv.DictReader(open(self.csv_path, newline='', encoding='utf-8')))
        total = len(rows)
        self.progress['maximum'] = total

        for i, row in enumerate(rows, 1):
            title = row.get('Track Name') or row.get('Track name') or 'Unknown'
            artist = row.get('Artist Name(s)') or row.get('Artist name') or 'Unknown'
            album = row.get('Album Name') or row.get('Album') or playlist_name
            safe_title = re.sub(r"[^\w\s]", '', title)
            safe_artist = re.sub(r"[^\w\s]", '', artist)

            new_files = []
            for variant in cfg['variants']:
                q = f"{safe_title} {safe_artist} {variant}".strip()
                self.status_label.config(text=f"[{i}/{total}] Searching: {q}")
                yt_dlp = yt_dlp_exe
                cmd = [yt_dlp, f'--ffmpeg-location={ffmpeg_path}', '-f', 'bestaudio[ext=m4a]/bestaudio']
                # Thumbnail embedding
                if self.thumb_var.get():
                    cmd += ['--embed-thumbnail', '--add-metadata']
                if self.mp3_var.get():
                    cmd += ['--extract-audio', '--audio-format', 'mp3']
                    if self.quality_var.get():
                        cmd += ['--audio-quality', '0']
                else:
                    cmd += ['--remux-video', 'm4a']
                cmd += ['--output', os.path.join(output_dir, '%(title)s.%(ext)s'), '--no-playlist', f'ytsearch1:{q}']
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

                result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
                if result.returncode != 0:
                    with open(log_path, 'a') as log:
                        log.write(result.stderr)
                new_files = [fn for fn in os.listdir(output_dir)
                             if fn.lower().endswith(('.mp3', '.m4a')) and fn not in downloaded]
                if new_files:
                    break

            if not new_files:
                continue

            elapsed = time.time() - start_time
            eta = timedelta(seconds=int((elapsed / i) * (total - i)))
            self.progress['value'] = i
            self.status_label.config(text=f"Downloaded {i}/{total}, ETA: {eta}")
            self.root.update_idletasks()

            for fn in new_files:
                fpath = os.path.join(output_dir, fn)
                if fn.lower().endswith('.m4a') and not self.mp3_var.get():
                    audio = MP4(fpath)
                    tags = audio.tags or MP4Tags()
                    tags['\xa9nam'] = [title]
                    tags['\xa9ART'] = [artist]
                    tags['\xa9alb'] = [album]
                    audio.save()
                else:
                    try:
                        audio = EasyID3(fpath)
                    except:
                        audio = EasyID3()
                        audio.load()
                    audio.update({'artist': artist, 'title': title, 'album': album, 'tracknumber': str(i)})
                    audio.save()
                downloaded.append(fn)

        if self.m3u_var.get():
            m3u_filename = playlist_name.replace('_', ' ')
            m3u_path = os.path.join(output_dir, f"{m3u_filename}.m3u")
            with open(m3u_path, 'w', encoding='utf-8') as m3u:
                for fn in downloaded:
                    raw = os.path.join(output_dir, fn)
                    m3u.write(str(PureWindowsPath(raw)) + '\r\n')

        # Handle album art if Spotify album art was enabled
        if self.spotify_art_var.get():
            self.status_label.config(text='Renaming album art files...')
            self.rename_album_art(output_dir)
            
            self.status_label.config(text='Embedding album art...')
            self.embed_all_artwork(output_dir)

        self.progress['value'] = self.progress['maximum']
        self.root.config(cursor='')
        self.convert_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.NORMAL)
        self.status_label.config(text=f"✅ Completed in {timedelta(seconds=int(time.time() - start_time))}")
        self.root.bell()



if __name__ == '__main__':
    if _tkdnd_imported:
        try:
            root = TkinterDnD.Tk()
            DND_AVAILABLE = True
        except:
            root = tk.Tk()
            DND_AVAILABLE = False
    else:
        root = tk.Tk()
        DND_AVAILABLE = False
    app = Spotify2MP3GUI(root)
    root.mainloop()
