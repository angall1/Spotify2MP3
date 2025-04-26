import os
import subprocess
import time

def get_file_timestamps(file_path):
    return {
        'created': os.path.getctime(file_path),
        'modified': os.path.getmtime(file_path)
    }

def set_file_timestamps(file_path, timestamps):
    os.utime(file_path, (timestamps['modified'], timestamps['modified']))
    # Note: Creation time can't be directly set on Unix systems, but we preserve it where possible

def embed_artwork(audio_file, jpg_file):
    print(f"\nEmbedding artwork for: {audio_file}")
    print(f"Using artwork: {jpg_file}")
    
    # Save original timestamps
    timestamps = get_file_timestamps(audio_file)
    
    temp_output = f"temp_{audio_file}"
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
        set_file_timestamps(audio_file, timestamps)
        print(f"Successfully embedded artwork for {audio_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {audio_file}: {e.stderr.decode()}")
        if os.path.exists(temp_output):
            os.remove(temp_output)

def main():
    # Get all audio files (both M4A and MP3)
    audio_files = [f for f in os.listdir('.') if f.lower().endswith(('.m4a', '.mp3'))]
    for audio_file in audio_files:
        jpg_file = os.path.splitext(audio_file)[0] + '.jpg'
        if os.path.exists(jpg_file):
            embed_artwork(audio_file, jpg_file)
        else:
            print(f"No matching artwork found for {audio_file} (expected {jpg_file})")

if __name__ == "__main__":
    main() 