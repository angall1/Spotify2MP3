# Spotify2MP3

Spotify2MP3 is a Windows app that takes a Spotify playlist CSV (exported using Exportify) and downloads all the tracks as MP3s. 
It uses yt-dlp and ffmpeg under the hood, but everything’s bundled — no install or setup required.

You drag and drop the playlist, pick an output folder, and it does the rest.

---

## Download

You can grab the latest release from the [Releases tab](https://github.com/angall1/Spotify2MP3/releases). 
Just download the ZIP, extract it, and run `Spotify2MP3.exe`.

No install, no dependencies, no Python required.

---

## How to Use

1. Go to [https://exportify.net](https://exportify.net) and export your playlist as a CSV file
2. Open `Spotify2MP3.exe`
3. Drag and drop the CSV file into the app, or click to browse
4. Choose an output folder
5. Hit **Convert Playlist**

It'll download everything to that folder and tag the MP3s with title, artist, album, and track number. It also creates a `.m3u` playlist file.

---

## Importing to an iPod (MediaMonkey method)

If you're trying to move the playlist to an iPod:

1. Open MediaMonkey
2. Drag the generated `.m3u` file into the MediaMonkey library
3. Plug in your iPod
4. In the sidebar under Imported Playlists, drag the playlist into your iPod
5. Sync — you're done

---

## Notes

- You don't need to install anything
- ffmpeg and yt-dlp are included
- If something breaks, it usually means yt-dlp couldn't find a good match — try editing the track name or artist slightly and re-run it

---

## License

MIT
