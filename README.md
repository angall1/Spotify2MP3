# Spotify2MP3

Spotify2MP3 is a cross-platform standalone app (Windows EXE, macOS .app) that takes a playlist CSV exported from Spotify via [Exportify](https://exportify.net), Apple Music/YouTube Music via [TuneMyMusic](https://tunemymusic.com), or any other service and batch downloads every track as **M4A** (remuxed at up to the original 128 kbps AAC bitrate) or **high-quality MP3** (VBR 0). Everything’s bundled, no Python or external installs required.

---

##  Download

Grab the latest build from the [Releases page](https://github.com/angall1/Spotify2MP3/releases):

- **Windows**: Download the ZIP, extract, and run `Spotify2MP3.exe`  
- **macOS**: Download the ZIP, unzip, and open `Spotify2MP3.app`  

---

##  How to Use

1. **Export your CSV**  
   - Spotify → [Exportify](https://exportify.net)  
   - Apple/YouTube/other → [TuneMyMusic](https://tunemymusic.com)  
2. **Launch the app**.  
3. **Drag & drop** your CSV (or click the box to browse).  
4. **Select an output folder**.  
5. (Optional) Click **Settings** to toggle:  
   - **Transcode to MP3 (VBR 0)**  
   - **Generate M3U playlist**  
   - **Exclude instrumental versions**  
   - **Other tweaks**  
6. Hit **Convert Playlist**.  

It will fetch each track remuxing to M4A or re-encoding to MP3 VBR 0—automatically tag title/artist/album/track number, and (if enabled) create a `.m3u` file.

---

##  Importing to an iPod (MediaMonkey)

1. In MediaMonkey, **File → Add/Rescan files to the Library**, and pick your output folder.  
2. Plug in your iPod.  
3. Under **Playlists → Imported Playlists**, drag the generated `.m3u` onto your device.  
4. Sync

---

## Notes

- **Any CSV** with the usual headers (`Track Name`, `Artist Name`, `Album Name`) will work.  
- **M4A mode** uses the original AAC stream (usually capped at 128 kbps).  
- **MP3 mode** always uses ffmpeg’s best VBR 0 setting for maximum quality.  
- FFmpeg and yt-dlp are bundled—no extra installs.  
- If a track fails, tweak its title/artist or flip settings and retry.

---

## License

MIT  
