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

DEFAULT_DROP_BG = '#e0e0e0'
LOADED_DROP_BG  = '#c0ffc0'

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)

CONFIG_FILE = resource_path('config.json')

def load_config():
    default = {
        "variants": [],
        "duration_min": 30,
        "duration_max": 600,
        "transcode_mp3": "false",
        "generate_m3u": "true",
        "exclude_instrumentals": "false"
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
        self.root.geometry('540x650')
        self.root.minsize(300, 500)
        self.csv_path = None
        self.output_folder = None
        self.last_output_dir = None
        self.deep_search_var = tk.BooleanVar(value=True)
        
        # Set initial directory to Downloads folder
        if platform.system() == "Windows":
            self.last_directory = os.path.join(os.path.expanduser("~"), "Downloads")
        else:
            self.last_directory = os.path.expanduser("~/Downloads")
            
        self.config = load_config()
        self.exclude_instr_var = tk.BooleanVar(value=self.config.get("exclude_instrumentals", False))

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
        instr = tk.Label(self.root, text='Download Spotify CSV via Exportify: https://exportify.net/', fg='blue', cursor='hand2',font=("Arial", 12))
        Tooltip(instr, 'Use this link for downloading Spotify playlists.')
        instr.pack(fill='x', padx=20)
        instr.bind('<Button-1>', lambda e: webbrowser.open('https://exportify.net/'))
        instr2 = tk.Label(self.root, text='Download other CSVs (Apple Music, Youtube Music, etc) \n via TuneMyMusic: https://tunemymusic.com/transfer/', fg='blue', cursor='hand2',font=("Arial", 12))
        Tooltip(instr2, 'Use this link for downloading from any other platform or for Spotify albums')
        instr2.pack(fill='x', padx=20)
        instr2.bind('<Button-1>', lambda e: webbrowser.open('https://www.tunemymusic.com/transfer/apple-music-to-file'))

        # CSV Input
        tk.Label(self.root, text='1) Drag and drop CSV File:', anchor='w').pack(fill='x', padx=20)
        tk.Label(self.root, text='The playlist name will be the same as the CSV filename.', anchor='w').pack(fill='x', padx=20)
        self.drop_frame = tk.Frame(self.root, bg='#e0e0e0', height=60, width= 400)
        self.drop_frame.pack(pady=5, padx=20, expand=False)
        self.drop_frame.pack_propagate(False)  
        self.drop_label = tk.Label(self.drop_frame, text='CSV file: None', bg='#e0e0e0', font=("Arial", 12), wraplength=380, justify='center')
        self.drop_label.pack(expand=True, fill='both')
        self.drop_label.bind('<Button-1>', self.browse_csv)
        Tooltip(self.drop_label, 'Drop your playlist CSV here or click to browse.')


        #CSV clear
        self.clear_button = tk.Button(self.root, text='Clear CSV', command=self.clear_selection, state=tk.DISABLED)
        self.clear_button.pack()
        
        # Output folder
        tk.Label(self.root, text='2) Output Folder:', anchor='w').pack(fill='x', padx=20)
        tk.Label(self.root, text='This will be the folder the playlist files will be outputted into.', anchor='w').pack(fill='x', padx=20)
        self.folder_button = tk.Button(self.root, text='Choose Output Folder', command=self.select_output_folder, font=('Arial', 12))
        self.folder_button.pack(pady=5)
        self.output_label = tk.Label(self.root, text='Output folder: Not selected', anchor='w',)
        self.output_label.pack(fill='x', padx=20)
        Tooltip(self.folder_button, 'Where files will be saved.')
        

        # Conversion options
    

        tk.Label(self.root, text='3) Conversion Options:', anchor='w').pack(fill='x', padx=20)
        self.mp3_var = tk.BooleanVar(value=False)
        self.mp3_check = tk.Checkbutton(self.root, text='Transcode to MP3 (for MP3-only players)', variable=self.mp3_var)
        self.mp3_check.pack(pady=2)
        #Deep search
        self.deep_search_check = tk.Checkbutton(self.root,text="Deep Search",variable=self.deep_search_var )
        self.deep_search_check.pack(fill='x', padx=20)
        Tooltip(
            self.deep_search_check,
            "When ON: does a slower, JSON‐based 3-result search+scoring for max accuracy. Takes approx. 20s per song.\n"
            "When OFF: does a fast single-result search (good for popular tracks). Takes approx. 3s per song")
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
        self.thumb_check = tk.Checkbutton(self.root, text='Embed thumbnails as cover art', variable=self.thumb_var, command=self.update_artwork_options)
        self.thumb_check.pack(pady=2)
        Tooltip(self.thumb_check, 'Fetch and embed video thumbnails into the audio file.')

        # Spotify album art option
        self.spotify_art_var = tk.BooleanVar(value=False)
        self.spotify_art_check = tk.Checkbutton(self.root, text='Get and embed album art from Spotify link (Requires Chrome or Firefox)', variable=self.spotify_art_var, command=self.update_artwork_options)
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
        self.spotify_link_frame.pack_forget()
        self.spotify_link_entry.config(state='normal')
        self.spotify_art_var.trace_add('write', self.toggle_spotify_link)
        Tooltip(self.spotify_link_entry, 'Enter Spotify playlist/album link')



        # Settings button
        self.settings_button = tk.Button(
            self.root,
            text="Settings",
            command=self.open_settings
        )
        self.settings_button.pack(pady=5)


        self.convert_button = tk.Button(self.root, text='Convert Playlist', command=self.start_conversion, state=tk.DISABLED, font=('Arial', 14) )
        self.convert_button.pack(pady=10)


        # Actions
        tk.Label(self.root, text='4) Actions:', anchor='w').pack(fill='x', padx=20, pady=(10,0))
    

        # Progress
        self.status_label = tk.Label(self.root, text='Status: Waiting...', anchor='w', font=('Arial', 12))
        self.status_label.pack(fill='x', padx=20)
        self.progress = ttk.Progressbar(self.root, orient='horizontal', length=500, mode='determinate')
        self.progress.pack(pady=10)

        #output folder
        self.open_folder_button = tk.Button(self.root, text='Open Output Folder', command=self.open_output_folder)
        self.open_folder_button.pack(pady=5)
        Tooltip(self.open_folder_button, 'Open folder with converted files.')

        #hide useless buttons
        self.mp3_check.pack_forget()
        self.quality_check.pack_forget()
        self.m3u_check.pack_forget()

    def toggle_spotify_link(self, *args):
        if self.spotify_art_var.get():
            self.spotify_link_frame.pack(
                fill='x',
                padx=20,
                pady=(0, 10),
                after=self.spotify_art_check
            )
        else:
            self.spotify_link_frame.pack_forget()

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.grab_set()  # modal

        # Variants
        tk.Label(win, text="Variants (comma-separated):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        variants_str = tk.StringVar(value=",".join(self.config.get("variants", [])))
        variants_entry = tk.Entry(win, textvariable=variants_str, width=40)
        variants_entry.grid(row=0, column=1, padx=10, pady=5)

        # Min duration
        tk.Label(win, text="Min Duration (s):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        min_var = tk.IntVar(value=self.config.get("duration_min", 60))
        tk.Entry(win, textvariable=min_var).grid(row=1, column=1, padx=10, pady=5)

        # Max duration
        tk.Label(win, text="Max Duration (s):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        max_var = tk.IntVar(value=self.config.get("duration_max", 600))
        tk.Entry(win, textvariable=max_var).grid(row=2, column=1, padx=10, pady=5)

        # Transcode & M3U options
        tk.Label(win, text="Output options:").grid(row=3, column=0, sticky="w", padx=10, pady=(15,5))
        mp3_cb = tk.Checkbutton(win, text="Transcode to MP3 (VBR0)", variable=self.mp3_var)
        mp3_cb.grid(row=3, column=1, sticky="w", padx=10)
        m3u_cb = tk.Checkbutton(win, text="Generate M3U playlist", variable=self.m3u_var)
        m3u_cb.grid(row=4, column=1, sticky="w", padx=10, pady=(0,10))

        tk.Label(win, text="Filter results:").grid(row=5, column=0, sticky="w", padx=10, pady=(10,5))
        instr_cb = tk.Checkbutton(
            win,
            text="Exclude instrumental versions",
            variable=self.exclude_instr_var
        )
        instr_cb.grid(row=5, column=1, sticky="w", padx=10)

        # Buttons frame
        btn_frame = tk.Frame(win)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)


        def save():
            try:
                variants = [v.strip() for v in variants_str.get().split(",") if v.strip()]
                cfg = {
                    "variants": variants,
                    "duration_min": int(min_var.get()),
                    "duration_max": int(max_var.get()),
                    "transcode_mp3": self.mp3_var.get(),
                    "generate_m3u": self.m3u_var.get(),
                    "exclude_instrumentals": self.exclude_instr_var.get()
                }
                with open(CONFIG_FILE, "w") as f:
                    json.dump(cfg, f, indent=4)
                self.config = load_config()
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings:\n{e}")

        # Save/Cancel buttons
        tk.Button(btn_frame, text="Save",   command=save).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side="left", padx=5)


    def update_convert_button_state(self):
        ok = self.csv_path and os.path.isfile(self.csv_path) and self.csv_path.lower().endswith('.csv') and self.output_folder
        self.convert_button.config(state=tk.NORMAL if ok else tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL if self.csv_path else tk.DISABLED)

    def clear_selection(self):
        self.csv_path = None
        self.drop_label.config(text='CSV file: None')
        self.status_label.config(text='Status: Waiting...')
        # ← reset:
        self.drop_frame.config(bg=DEFAULT_DROP_BG)
        self.drop_label.config(bg=DEFAULT_DROP_BG)
        self.progress['value'] = 0
        self.update_convert_button_state()
    
    def browse_csv(self, event=None):
        path = filedialog.askopenfilename(
            initialdir=self.last_directory,
            filetypes=[('CSV files','*.csv')]
        )
        if path:
            self.csv_path = path
            self.last_directory = os.path.dirname(path)
            self.drop_label.config(text=f'CSV file: {os.path.basename(path)}')
            self.status_label.config(text='CSV loaded.')
            # ← highlight:
            self.drop_frame.config(bg=LOADED_DROP_BG)
            self.drop_label.config(bg=LOADED_DROP_BG)
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
            if platform.system() == "Windows":
                os.startfile(target)
            else:
                subprocess.run(['open', target])
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
            self.drop_frame.config(bg=LOADED_DROP_BG)
            self.drop_label.config(bg=LOADED_DROP_BG)
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
        
        # Get the correct ffmpeg path
        if platform.system() == "Darwin":  # macOS
            ffmpeg_path = resource_path("ffmpeg")
            ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg")
        else:
            ffmpeg_path = resource_path("ffmpeg")
            ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")
        cmd = [
            ffmpeg_exe, '-i', audio_file,
            '-i', jpg_file,
            '-map', '0:a',
            '-map', '1:v',
            '-c:a', 'copy',
            '-c:v', 'mjpeg',
            '-disposition:v:0', 'attached_pic',
            temp_output
        ]
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            subprocess.run(cmd, check=True, capture_output=True, creationflags=creationflags)
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

    def rename_album_art(self, output_dir, not_found_songs=None):
        if not_found_songs is None:
            not_found_songs = []
            
        # Create a set of failed song track numbers for faster lookup
        failed_track_numbers = {song['Track Number'] for song in not_found_songs}
        
        # Get all audio files (MP3 and M4A) and JPG files
        audio_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.mp3', '.m4a'))]
        jpg_files = [f for f in os.listdir(output_dir) if f.endswith('.jpg')]
        
        # Sort audio files by creation time (date added)
        audio_files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
        
        # Sort JPG files by their number prefix
        jpg_files.sort(key=self.get_jpg_number)
        
        # Make sure we have the same number of files
        if len(audio_files) != len(jpg_files):
            print(f"Warning: Number of files doesn't match! Audio files: {len(audio_files)}, JPG: {len(jpg_files)}")
            print("Will process as many files as possible.")
        
        # Process files in pairs
        i = 0
        while i < len(audio_files) and i < len(jpg_files):
            audio_file = audio_files[i]
            jpg_file = jpg_files[i]
            
            # Get the track number from the JPG filename
            jpg_number = self.get_jpg_number(jpg_file)
            
            # Skip if this track number was in the failed songs list
            if jpg_number in failed_track_numbers:
                # Remove only the JPG file from the list
                jpg_files.pop(i)
                continue
                
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
            
            i += 1

    def embed_all_artwork(self, output_dir, not_found_songs=None):
        """Embed artwork for all audio files, skipping songs that weren't found"""
        if not_found_songs is None:
            not_found_songs = []
            
        print("\n=== Starting metadata and artwork embedding process ===")
        print(f"Number of not found songs: {len(not_found_songs)}")
        if not_found_songs:
            print("Not found songs:")
            for song in not_found_songs:
                print(f"  Track {song['Track Number']}: {song['Track Name']} by {song['Artist Name(s)']}")
            
        # Create a set of failed song track numbers for faster lookup
        failed_track_numbers = {song['Track Number'] for song in not_found_songs}
        print(f"Failed track numbers: {failed_track_numbers}")
        
        # Read CSV file once and store in memory
        csv_data = []
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                # Filter out failed tracks from CSV data
                csv_data = [row for i, row in enumerate(reader, 1) if i not in failed_track_numbers]
                print(f"\nLoaded {len(csv_data)} entries from CSV file (excluding failed tracks)")
                print("First few CSV entries:")
                for i, row in enumerate(csv_data[:3]):
                    print(f"Entry {i+1}:")
                    print(f"  Title: {row.get('Track Name') or row.get('Track name')}")
                    print(f"  Artist: {row.get('Artist Name(s)') or row.get('Artist name')}")
                    print(f"  Album: {row.get('Album Name') or row.get('Album')}")
        except Exception as e:
            print(f"Error reading CSV file: {str(e)}")
            return
        
        # Get all audio files (both M4A and MP3) and JPG files
        audio_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.m4a', '.mp3'))]
        jpg_files = [f for f in os.listdir(output_dir) if f.endswith('.jpg')]
        
        print(f"\nFound {len(audio_files)} audio files and {len(jpg_files)} JPG files")
        
        # Sort audio files by creation time (date added)
        audio_files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
        
        print("\nAudio files sorted by creation time:")
        for i, f in enumerate(audio_files):
            print(f"{i+1}. {f}")
            
        print("\nJPG files:")
        for i, f in enumerate(jpg_files):
            print(f"{i+1}. {f}")
        
        # Process files in pairs
        csv_index = 0  # Separate index for CSV data
        for audio_file in audio_files:
            print(f"\nProcessing audio file: {audio_file}")
            
            # Find matching JPG file by base name
            audio_base = os.path.splitext(audio_file)[0]
            matching_jpg = None
            for jpg_file in jpg_files:
                jpg_base = os.path.splitext(jpg_file)[0]
                if jpg_base == audio_base:
                    matching_jpg = jpg_file
                    break
            
            if matching_jpg:
                print(f"Found matching JPG: {matching_jpg}")
                try:
                    audio_path = os.path.join(output_dir, audio_file)
                    jpg_path = os.path.join(output_dir, matching_jpg)
                    
                    # Get metadata from CSV in the same order
                    if csv_index < len(csv_data):
                        row = csv_data[csv_index]
                        title = row.get('Track Name') or row.get('Track name') or 'Unknown'
                        artist = row.get('Artist Name(s)') or row.get('Artist name') or 'Unknown'
                        album = row.get('Album Name') or row.get('Album') or 'Unknown'
                        print(f"\nUsing metadata from CSV (row {csv_index+1}):")
                        print(f"  Title: {title}")
                        print(f"  Artist: {artist}")
                        print(f"  Album: {album}")
                        csv_index += 1
                    else:
                        print(f"No matching artwork found for {audio_file} (expected {jpg_file})")
                        title = os.path.splitext(audio_file)[0]
                        artist = 'Unknown Artist'
                        album = 'Unknown Album'
                        print(f"\nNo matching CSV row found, using defaults:")
                        print(f"  Title: {title}")
                        print(f"  Artist: {artist}")
                        print(f"  Album: {album}")
                    
                    if audio_file.lower().endswith('.m4a'):
                        print("\nEmbedding metadata for M4A file...")
                        audio = MP4(audio_path)
                        tags = audio.tags or MP4Tags()
                        tags['\xa9nam'] = [title]  # Title
                        tags['\xa9ART'] = [artist]  # Artist
                        tags['\xa9alb'] = [album]  # Album
                        audio.save()
                        print("M4A metadata embedded successfully")
                    else:  # MP3
                        print("\nEmbedding metadata for MP3 file...")
                        try:
                            audio = EasyID3(audio_path)
                        except:
                            audio = EasyID3()
                        audio['title'] = title
                        audio['artist'] = artist 
                        audio['album'] = album
                        audio.save()
                        print("MP3 metadata embedded successfully")
                    
                    # Embed artwork
                    print(f"\nEmbedding artwork from: {matching_jpg}")
                    self.embed_artwork(audio_path, jpg_path)
                    
                except Exception as e:
                    print(f"Error processing {audio_file}: {str(e)}")
            else:
                print(f"No matching JPG file found for {audio_file}")
            
            print(f"=== Finished processing {audio_file} ===\n")
    

    def convert_playlist(self):
        
        def normalize(text: str) -> str:
            """Lowercase and strip out any punctuation, leaving only word chars and spaces."""
            return re.sub(r"[^\w\s]", "", text.lower())

        def contains_keywords_in_order(candidate_title: str, keywords: list[str]) -> bool:
            txt = normalize(candidate_title)
            pos = 0
            for kw in keywords:
                idx = txt.find(kw, pos)
                if idx < 0:
                    return False
                pos = idx + len(kw)
            return True

        start_time = time.time()
        # Load duration filters from settings
        duration_min = self.config.get("duration_min", 0)
        duration_max = self.config.get("duration_max", float("inf"))
        self.status_label.config(text='Starting conversion...')
        playlist_name = os.path.splitext(os.path.basename(self.csv_path))[0]
        output_dir = os.path.join(self.output_folder, playlist_name)
        os.makedirs(output_dir, exist_ok=True)
        self.last_output_dir = output_dir

        cookies_path = self.config.get('cookies_path')
        if cookies_path and not os.path.isfile(cookies_path):
            messagebox.showerror('Missing Cookies', f'Cookies file not found: {cookies_path}')
            return

        downloaded = []
        not_found_songs = []
        initial_state = {
            'cursor': self.root.cget('cursor'),
            'convert_button_state': self.convert_button.cget('state'),
            'clear_button_state': self.clear_button.cget('state'),
            'progress_value': self.progress['value'],
            'status_text': self.status_label.cget('text')
        }

        try:
            if self.spotify_art_var.get():
                self.fetch_spotify_album_art(output_dir)

            base_dir = os.path.dirname(os.path.abspath(__file__))
            if platform.system() == "Darwin":
                ffmpeg_exe = os.path.join(resource_path("ffmpeg"), "ffmpeg")
                yt_dlp_exe = os.path.join(resource_path("yt-dlp"), "yt-dlp")
            else:
                ffmpeg_exe = os.path.join(base_dir, "ffmpeg", "ffmpeg.exe")
                yt_dlp_exe = os.path.join(base_dir, "yt-dlp", "yt-dlp.exe")

            if not os.path.isfile(ffmpeg_exe) or not os.path.isfile(yt_dlp_exe):
                missing = []
                if not os.path.isfile(ffmpeg_exe): missing.append('ffmpeg')
                if not os.path.isfile(yt_dlp_exe): missing.append('yt-dlp')
                messagebox.showerror('Missing Executable', f"{', '.join(missing)} not found. Please install.")
                return

            rows = list(csv.DictReader(open(self.csv_path, newline='', encoding='utf-8')))
            total = len(rows)
            self.progress['maximum'] = total
            archive_file = os.path.join(output_dir, 'downloaded.txt')
            creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0

            for i, row in enumerate(rows, start=1):
                title = row.get('Track Name') or row.get('Track name') or 'Unknown'
                artist_raw = row.get('Artist Name(s)') or row.get('Artist name') or 'Unknown'
                artist_primary = re.split(r'[,/&]| feat\.| ft\.', artist_raw, flags=re.I)[0].strip()
                safe_artist = re.sub(r"[^\w\s]", '', artist_primary)
                album = row.get('Album Name') or row.get('Album') or playlist_name
                spotify_ms = row.get('Duration (ms)')
                spotify_sec = int(spotify_ms) / 1000 if spotify_ms and spotify_ms.isdigit() else None

                safe_title = re.sub(r"[^\w\s]", '', title)
                variants = self.config.get('variants') or ['']
                if 'instrumental' in title.lower():
                    variants.insert(0, 'instrumental')

                best_file = None
                for variant in variants:
                    parts = [safe_title]
                    if safe_artist and safe_artist.lower() != 'unknown': parts.append(safe_artist)
                    if variant: parts.append(variant)
                    q = ' '.join(parts)
                    print(f"Searching for → {q!r}")
                    self.status_label.config(text=f"[{i}/{total}] Searching: {q}")
                    self.root.update_idletasks()

                    def yt_cmd(extra_args, search_spec):
                        cmd = [yt_dlp_exe, f"--ffmpeg-location={os.path.dirname(ffmpeg_exe)}", "--no-config"]
                        if cookies_path: cmd += ["--cookies", cookies_path]
                        cmd += extra_args + [search_spec]
                        return cmd

                    if self.deep_search_var.get():
                        # Phase 1: quick flat-playlist probe
                        proc_q = subprocess.run(
                            yt_cmd(["--flat-playlist", "--dump-single-json", "--no-playlist"], f"ytsearch1:{q}"),
                            capture_output=True, text=True, creationflags=creationflags
                        )
                        try:
                            data_q = json.loads(proc_q.stdout) or {}
                        except Exception:
                            data_q = {}
                        if not isinstance(data_q, dict): data_q = {}
                        entries_q = data_q.get('entries') if isinstance(data_q.get('entries'), list) else []
                        top = entries_q[0] if entries_q else {}

                        vid_title = top.get('title', '')
                        upl = (top.get('uploader') or '').lower()
                        duration = top.get('duration') or 0
                        passes = (
                            safe_title.lower() in vid_title.lower()
                            and (not safe_artist or safe_artist.lower() in upl)
                            and (not spotify_sec or abs(duration - spotify_sec) <= 10)
                            and (duration >= duration_min and duration <= duration_max)
                        )
                        if passes:
                            download_spec = top.get('webpage_url', f"https://www.youtube.com/watch?v={top.get('id','')}" )
                        else:
                            print("Deep searching : " + title)
                            # Phase 2: deep-search candidate IDs
                            proc_ids = subprocess.run(
                                yt_cmd(["--flat-playlist", "--dump-single-json", "--no-playlist"], f"ytsearch3:{q}"),
                                capture_output=True, text=True, creationflags=creationflags
                            )
                            try:
                                tmp = json.loads(proc_ids.stdout) or {}
                            except Exception:
                                tmp = {}
                            data_ids = tmp if isinstance(tmp, dict) else {}
                            entries_ids = data_ids.get('entries') if isinstance(data_ids.get('entries'), list) else []
                            ids = [e for e in entries_ids if isinstance(e, dict)][:3]

                            scored = []
                            first_words = normalize(title).split()[:5]
                            for entry in ids:
                                vid = entry.get('id')
                                url = f"https://www.youtube.com/watch?v={vid}"
                                proc_i = subprocess.run(
                                    yt_cmd(["--dump-single-json", "--no-playlist"], url),
                                    capture_output=True, text=True, creationflags=creationflags
                                )
                                if "Sign in to confirm your age" in (proc_i.stderr or ''):
                                    continue
                                try:
                                    info = json.loads(proc_i.stdout) or {}
                                except Exception:
                                    continue

                                raw_title = info.get('title','')
                                low = raw_title.lower()
                                up2 = (info.get('uploader') or '').lower()
                                dur2 = info.get('duration') or 0
                                # enforce duration bounds
                                if dur2 < duration_min or dur2 > duration_max:
                                    continue
                                if 'shorts/' in info.get('webpage_url','') or '#shorts' in low: continue
                                if safe_artist.lower() and safe_artist.lower() not in up2: continue
                                if variant and variant.lower() not in low: continue
                                if not contains_keywords_in_order(raw_title, first_words): continue
                                score = 100 if low.startswith(safe_title.lower()) else 80
                                if spotify_sec: score -= abs(dur2 - spotify_sec)
                                scored.append((score, url))
                            download_spec = scored and max(scored, key=lambda x: x[0])[1] or f"ytsearch1:{q}"
                    else:
                        download_spec = f"ytsearch1:{q}"

                    # Download
                    file_title = re.sub(r"[^\w\s]", "", title).strip()
                    base = f"{i:03d} - {file_title}" + (f" - {variant}" if variant else "")
                    tmpl = base + ".%(ext)s"
                    cmd_dl = yt_cmd([
                        '--download-archive', archive_file,
                        '-f', 'bestaudio[ext=m4a]/bestaudio',
                        '--output', os.path.join(output_dir, tmpl),
                        '--no-playlist'
                    ], download_spec)
                    if self.thumb_var.get(): cmd_dl += ['--embed-thumbnail','--add-metadata']
                    if self.mp3_var.get(): cmd_dl += ['--extract-audio','--audio-format','mp3','--audio-quality','0']
                    else: cmd_dl += ['--remux-video','m4a']
                    if self.exclude_instr_var.get(): cmd_dl += ['--reject-title','instrumental']

                    ret = subprocess.run(cmd_dl, capture_output=True, text=True, creationflags=creationflags)
                    if ret.returncode != 0:
                        stderr = ret.stderr or ''
                        if 'Sign in to confirm your age' in stderr:
                            not_found_songs.append({
                                'Track Name': title,
                                'Artist Name(s)': artist_primary,
                                'Album Name': album,
                                'Track Number': i,
                                'Error': 'Age-restricted video'
                            })
                            break
                        else:
                            print(f"Download failed for {download_spec}: {stderr[:200]}")
                            continue
                    out_ext = '.mp3' if self.mp3_var.get() else '.m4a'
                    candidate_path = os.path.join(output_dir, base + out_ext)
                    if os.path.isfile(candidate_path):
                        best_file = candidate_path
                        if out_ext == '.m4a':
                            audio = MP4(best_file); tags = audio.tags or MP4Tags()
                            tags['\xa9nam']=[title]; tags['\xa9ART']=[artist_primary]; tags['\xa9alb']=[album]; audio.save()
                        else:
                            audio = EasyID3();
                            try: audio.load(best_file)
                            except: pass
                            audio.update({'artist':artist_primary,'title':title,'album':album,'tracknumber':str(i)}); audio.save()
                        downloaded.append(os.path.basename(best_file))
                        break

                if not best_file:
                    not_found_songs.append({'Track Name':title,'Artist Name(s)':artist_primary,'Album Name':album,'Track Number':i,'Error':'No valid download'})

                elapsed = time.time() - start_time
                eta = timedelta(seconds=int((elapsed/i)*(total-i)))
                self.progress['value']=i
                self.status_label.config(text=f"Downloaded {i}/{total}, ETA: {eta}")
                self.root.update_idletasks()

            if not_found_songs:
                nf_path = os.path.join(output_dir, f"{playlist_name}_not_found.csv")
                with open(nf_path, 'w', newline='', encoding='utf-8') as cf:
                    writer = csv.DictWriter(cf, fieldnames=['Track Name','Artist Name(s)','Album Name','Track Number','Error'])
                    writer.writeheader()
                    writer.writerows(not_found_songs)
            if self.m3u_var.get():
                m3u_filename = playlist_name.replace('_',' ')
                m3u_path = os.path.join(output_dir, f"{m3u_filename}.m3u")
                with open(m3u_path,'w',encoding='utf-8') as m3u:
                    m3u.write('#EXTM3U\n')
                    audio_files = sorted([f for f in os.listdir(output_dir) if f.lower().endswith(('.mp3','.m4a'))], key=lambda x: os.path.getctime(os.path.join(output_dir,x)))
                    for fn in audio_files:
                        m3u.write(f'#EXTINF:-1,{os.path.splitext(fn)[0]}\n')
                        m3u.write(f'{fn}\n')

            if self.spotify_art_var.get():
                self.rename_album_art(output_dir)
                self.embed_all_artwork(output_dir)

            self.progress['value'] = self.progress['maximum']
            self.root.config(cursor='')
            self.convert_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)
            self.status_label.config(text=f"✅ Completed in {timedelta(seconds=int(time.time()-start_time))}")
            self.root.bell()

        except Exception as e:
            self.restore_state(initial_state)
            messagebox.showerror('Error', f'Unexpected error: {e}')
        finally:
            self.convert_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)
            self.root.update_idletasks()



    def restore_state(self, state):
        """Restore the UI to its initial state"""
        try:
            self.root.config(cursor=state['cursor'])
            self.convert_button.config(state=tk.NORMAL)  # Always enable convert button
            self.clear_button.config(state=tk.NORMAL)    # Always enable clear button
            self.progress['value'] = state['progress_value']
            self.status_label.config(text=state['status_text'])
            self.root.update_idletasks()  # Force UI update
        except Exception as e:
            print(f"Error restoring state: {e}")

    def update_artwork_options(self):
        # If thumbnail embedding is selected, disable Spotify art
        if self.thumb_var.get():
            self.spotify_art_var.set(False)
            self.spotify_art_check.config(state=tk.DISABLED)
        # If Spotify art is selected, disable thumbnail embedding
        elif self.spotify_art_var.get():
            self.thumb_var.set(False)
            self.thumb_check.config(state=tk.DISABLED)
        # If neither is selected, enable both
        else:
            self.thumb_check.config(state=tk.NORMAL)
            self.spotify_art_check.config(state=tk.NORMAL)


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
