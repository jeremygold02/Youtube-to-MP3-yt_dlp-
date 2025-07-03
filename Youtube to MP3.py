import os
import json
import requests
from yt_dlp import YoutubeDL
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error

CONFIG_FILE = "ytmp3-config.json"

def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in " _-()" else "_" for c in name)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            output_folder = config.get("download_path", "").strip()
            if os.path.isdir(output_folder):
                return output_folder
            else:
                print(f"Saved path in {CONFIG_FILE} is invalid.")
        except Exception as e:
            print(f"Failed to read config: {e}")

    while True:
        user_path = input("Enter download folder path: ").strip()
        if os.path.isdir(user_path):
            with open(CONFIG_FILE, "w") as f:
                json.dump({"download_path": user_path}, f, indent=2)
            return user_path
        else:
            print("Invalid path. Please enter a valid existing folder.")

def download_youtube_audio_as_mp3(youtube_url, output_folder):
    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Get metadata first (without downloading)
        ydl_metadata_opts = {'quiet': True, 'skip_download': True}
        with YoutubeDL(ydl_metadata_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

        title = info.get("title", "audio")
        sanitized_title = sanitize_filename(title)
        thumbnail_url = info.get("thumbnail")
        artist = info.get("uploader", "Unknown")

        # Download the audio
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': True
        }

        with YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading: {title}")
            result = ydl.extract_info(youtube_url, download=True)
            filename_base = ydl.prepare_filename(result).rsplit('.', 1)[0]
            output_path = filename_base + '.mp3'

        # Download thumbnail
        thumb_path = os.path.join(output_folder, f"{sanitized_title}_thumb.jpg")
        if thumbnail_url:
            response = requests.get(thumbnail_url)
            with open(thumb_path, 'wb') as f:
                f.write(response.content)

        # Embed metadata
        try:
            audio = EasyID3(output_path)
        except error:
            audio = EasyID3()
        audio['title'] = title
        audio['artist'] = artist
        audio.save(output_path)

        # Embed album art
        audio = ID3(output_path)
        with open(thumb_path, 'rb') as albumart:
            audio['APIC'] = APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=albumart.read()
            )
        audio.save()

        os.remove(thumb_path)

        print(f"MP3 saved with metadata: {output_path}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    output_dir = load_config()
    while True:
        url = input("Enter YouTube URL: ").strip()
        if url:
            download_youtube_audio_as_mp3(url, output_dir)
        print()
