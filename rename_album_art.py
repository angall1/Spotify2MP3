import os
import subprocess
from datetime import datetime
import re

def get_modified_time(file_path):
    return os.path.getmtime(file_path)

def clean_filename_for_artwork(filename):
    # Remove file extension
    filename = os.path.splitext(filename)[0]
    return filename

def get_jpg_number(filename):
    # Extract the number prefix from jpg files (e.g., "1_" or "42_")
    match = re.match(r'^(\d+)_', filename)
    return int(match.group(1)) if match else float('inf')

def main():
    # Get all audio files (MP3 and M4A) and JPG files
    audio_files = [f for f in os.listdir('.') if f.lower().endswith(('.mp3', '.m4a'))]
    jpg_files = [f for f in os.listdir('.') if f.endswith('.jpg')]
    
    # Sort audio files by modification time
    audio_files.sort(key=get_modified_time)
    
    # Sort JPG files by their number prefix
    jpg_files.sort(key=get_jpg_number)
    
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
        new_jpg_name = clean_filename_for_artwork(audio_file) + '.jpg'
        print(f"New JPG name: {new_jpg_name}")
        
        try:
            os.rename(jpg_file, new_jpg_name)
            print(f"Successfully renamed {jpg_file} to {new_jpg_name}")
        except Exception as e:
            print(f"Error renaming file: {e}")

if __name__ == "__main__":
    main() 