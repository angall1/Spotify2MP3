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
from datetime import timedelta
from mutagen.easyid3 import EasyID3
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

def resource_path(relative_path):
	if hasattr(sys, '_MEIPASS'):
		return os.path.join(sys._MEIPASS, relative_path)
	return os.path.join(os.path.abspath("."), relative_path)

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
        x,y,_cx,cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += cy + self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg="yellow", relief="solid", bd=1).pack()
    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None

class Spotify2MP3GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify2MP3")
        self.root.geometry("600x500")
        self.root.minsize(520, 400)
        self.csv_path = None
        self.output_folder = None
        self.last_output_dir = None
        self.config = load_config()

        self.setup_ui()
        if _tkdnd_imported:
            try:
                root.drop_target_register(DND_FILES)
                root.dnd_bind('<<Drop>>', self.handle_drop)
                global DND_AVAILABLE; DND_AVAILABLE = True
            except:
                DND_AVAILABLE = False
        if not DND_AVAILABLE:
            Tooltip(self.drop_frame, "Drag & drop not available\nInstall tkinterdnd2 to enable.")

    def setup_ui(self):
        instr = tk.Label(self.root, text="Download CSV via Exportify: https://exportify.net/", fg="blue", cursor="hand2")
        instr.pack(fill="x", padx=20)
        instr.bind('<Button-1>', lambda e: webbrowser.open("https://exportify.net/"))

        tk.Label(self.root, text="1) Drag & drop your Spotify CSV or click below:", anchor="w").pack(fill="x", padx=20)
        self.drop_frame = tk.Frame(self.root, bg="#e0e0e0", height=180)
        self.drop_frame.pack(pady=5, padx=20, fill="x")
        self.drop_label = tk.Label(self.drop_frame, text="CSV file: None", bg="#e0e0e0")
        self.drop_label.pack(expand=True, fill="both")
        self.drop_label.bind('<Button-1>', self.browse_csv)
        Tooltip(self.drop_frame, "Drop your Exportify CSV here.\nOr click to browse.")

        tk.Label(self.root, text="2) Select an output folder:", anchor="w").pack(fill="x", padx=20)
        self.folder_button = tk.Button(self.root, text="Choose Output Folder", command=self.select_output_folder)
        self.folder_button.pack(pady=5)
        self.output_label = tk.Label(self.root, text="Output folder: Not selected", anchor="w")
        self.output_label.pack(fill="x", padx=20)
        Tooltip(self.folder_button, "Where MP3s and playlist will be saved.")

        tk.Label(self.root, text="3) Convert CSV to MP3:", anchor="w").pack(fill="x", padx=20)
        self.convert_button = tk.Button(self.root, text="Convert Playlist", command=self.start_conversion, state=tk.DISABLED)
        self.convert_button.pack(pady=5)
        Tooltip(self.convert_button, "Start conversion and tagging process.")

        self.clear_button = tk.Button(self.root, text="Clear", command=self.clear_selection, state=tk.DISABLED)
        self.clear_button.pack(pady=5)
        Tooltip(self.clear_button, "Clear current CSV and reset progress.")

        self.m3u_var = tk.BooleanVar(value=True)
        self.m3u_check = tk.Checkbutton(self.root, text="Generate M3U playlist", variable=self.m3u_var)
        self.m3u_check.pack(pady=5)
        Tooltip(self.m3u_check, "Toggle creation of the playlist file.")

        self.quality_var = tk.BooleanVar(value=True)
        self.quality_check = tk.Checkbutton(self.root, text="High quality (VBR0, best audio)", variable=self.quality_var)
        self.quality_check.pack(pady=5)
        Tooltip(self.quality_check, "Enable for highest MP3 quality (larger files).")

        self.settings_button = tk.Button(self.root, text="Settings", command=self.open_settings)
        self.settings_button.pack(pady=5)
        Tooltip(self.settings_button, "Configure search variants and duration filters.")

        tk.Label(self.root, text="4) Open output folder:", anchor="w").pack(fill="x", padx=20)
        self.open_folder_button = tk.Button(self.root, text="Open Output Folder", command=self.open_output_folder)
        self.open_folder_button.pack(pady=5)
        Tooltip(self.open_folder_button, "Open the folder where MP3s are saved.")

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=500, mode="determinate")
        self.progress.pack(pady=10)
        self.status_label = tk.Label(self.root, text="Status: Waiting...", anchor="w")
        self.status_label.pack(fill="x", padx=20)

    def open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        tk.Label(dlg, text="Search Variants (comma-separated):").pack(anchor="w", padx=10, pady=5)
        var_entry = tk.Entry(dlg, width=50)
        var_entry.insert(0, ",".join(self.config['variants']))
        var_entry.pack(padx=10)
        tk.Label(dlg, text="Min Duration (sec):").pack(anchor="w", padx=10, pady=5)
        min_entry = tk.Entry(dlg, width=10)
        min_entry.insert(0, str(self.config['duration_min']))
        min_entry.pack(padx=10)
        tk.Label(dlg, text="Max Duration (sec):").pack(anchor="w", padx=10, pady=5)
        max_entry = tk.Entry(dlg, width=10)
        max_entry.insert(0, str(self.config['duration_max']))
        max_entry.pack(padx=10)
        def save():
            self.config['variants'] = [v.strip() for v in var_entry.get().split(',')]
            self.config['duration_min'] = int(min_entry.get())
            self.config['duration_max'] = int(max_entry.get())
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
            dlg.destroy()
        tk.Button(dlg, text="Save", command=save).pack(pady=10)

    def update_convert_button_state(self):
        state = tk.NORMAL if self.csv_path and self.csv_path.lower().endswith('.csv') and self.output_folder else tk.DISABLED
        self.convert_button.config(state=state)
        self.clear_button.config(state=tk.NORMAL if self.csv_path else tk.DISABLED)

    def clear_selection(self):
        self.csv_path = None
        self.drop_label.config(text="CSV file: None")
        self.progress['value'] = 0
        self.status_label.config(text="Status: Waiting...")
        self.update_convert_button_state()

    def browse_csv(self, event):
        path = filedialog.askopenfilename(filetypes=[('CSV files','*.csv')])
        if path:
            self.csv_path = path
            self.drop_label.config(text=f"CSV file: {os.path.basename(path)}")
            self.status_label.config(text="CSV loaded.")
            self.update_convert_button_state()

    def select_output_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.output_folder = path
            self.output_label.config(text=f"Output folder: {path}")
            self.update_convert_button_state()

    def open_output_folder(self):
        target = self.last_output_dir or self.output_folder
        if target and os.path.isdir(target):
            os.startfile(target)
        else:
            messagebox.showerror("Error", "No valid folder to open.")

    def start_conversion(self):
        if not (self.csv_path and self.output_folder):
            messagebox.showerror("Error", "Select CSV and output folder.")
            return
        self.convert_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.root.config(cursor='watch')
        threading.Thread(target=self.convert_playlist, daemon=True).start()

    def handle_drop(self, event):
        path = event.data.strip('{}')
        if path.lower().endswith('.csv'):
            self.csv_path = path
            self.drop_label.config(text=f"CSV file: {os.path.basename(path)}")
            self.status_label.config(text="CSV loaded.")
            self.update_convert_button_state()

    def convert_playlist(self):
        start_time = time.time()
        self.status_label.config(text="Starting conversion...")
        playlist_name = os.path.splitext(os.path.basename(self.csv_path))[0]
        output_dir = os.path.join(self.output_folder, playlist_name)
        os.makedirs(output_dir, exist_ok=True)
        self.last_output_dir = output_dir
        downloaded = []

        cfg = self.config
        ffmpeg_path = resource_path("ffmpeg")
        ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg.exe")
        if not os.path.isfile(ffmpeg_exe):
            messagebox.showerror("Missing FFmpeg","ffmpeg.exe not found.")
            return

        log_path = os.path.join(output_dir,'error.log')
        rows = list(csv.DictReader(open(self.csv_path,newline='',encoding='utf-8')))
        total = len(rows)
        self.progress['maximum'] = total
        for i,row in enumerate(rows,1):
            title = row.get('Track Name') or row.get('Track name') or'Unknown'
            artist= row.get('Artist Name(s)') or row.get('Artist name') or'Unknown'
            album = row.get('Album Name') or row.get('Album') or playlist_name
            safe_title = re.sub(r"[^\w\s]",'',title)
            safe_artist= re.sub(r"[^\w\s]",'',artist)
            new_files=[]
            for variant in cfg['variants']:
                q = f"{safe_title} {safe_artist} {variant}".strip()
                self.status_label.config(text=f"[{i}/{total}] Searching: {q}")
                yt_dlp_exe = resource_path("yt-dlp.exe")
                cmd = [yt_dlp_exe, f'--ffmpeg-location={ffmpeg_path}']
                if self.quality_var.get():
                    cmd += ['-f','bestaudio[ext=m4a]/bestaudio','--extract-audio','--audio-format','mp3','--audio-quality','0']
                else:
                    cmd += ['--extract-audio','--audio-format','mp3']
                cmd += ['--output', os.path.join(output_dir,'%(title)s.%(ext)s'), '--no-playlist', f'ytsearch1:{q}']
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = subprocess.CREATE_NO_WINDOW

                result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
                if result.returncode != 0:
                    with open(log_path,'a') as log: log.write(result.stderr)
                new_files=[fn for fn in os.listdir(output_dir) if fn.lower().endswith('.mp3') and fn not in downloaded]
                if new_files: break
            if not new_files:
                continue

            elapsed = time.time()-start_time
            eta = timedelta(seconds=int((elapsed/i)*(total-i)))
            self.progress['value'] = i
            self.status_label.config(text=f"Downloaded {i}/{total}, ETA: {eta}")
            self.root.update_idletasks()
            for fn in new_files:
                path = os.path.join(output_dir,fn)
                try:
                    audio=EasyID3(path)
                except:
                    audio=EasyID3()
                audio.update({'artist':artist,'title':title,'album':album,'tracknumber':str(i)})
                audio.save(path)
                downloaded.append(fn)

        if self.m3u_var.get():
            m3u_filename = playlist_name.replace('_',' ')
            m3u_path = os.path.join(output_dir,f"{m3u_filename}.m3u")
            with open(m3u_path,'w', encoding='utf-8') as m3u:
                for fn in downloaded:
                    raw = os.path.join(output_dir, fn)
                    m3u.write(str(PureWindowsPath(raw)) + "\r\n")

        self.progress['value'] = self.progress['maximum']
        self.root.config(cursor='')
        self.convert_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.NORMAL)
        self.status_label.config(text=f"✅ Completed in {timedelta(seconds=int(time.time()-start_time))}")
        self.root.bell()

if __name__ == '__main__':
    if _tkdnd_imported:
        try:
            root = TkinterDnD.Tk()
            DND_AVAILABLE = True
        except Exception:
            root = tk.Tk()
            DND_AVAILABLE = False
    else:
        root = tk.Tk()
        DND_AVAILABLE = False
    app = Spotify2MP3GUI(root)
    root.mainloop()
