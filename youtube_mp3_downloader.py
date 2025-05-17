import argparse
import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
from youtubesearchpython import VideosSearch
from tqdm import tqdm
import threading

lock = threading.Lock()
failed_downloads = []
playlist_metadata = []

MAX_DURATION_SECONDS = 15 * 60  # 15 minutes

def search_youtube(query, max_results=10):
    search = VideosSearch(query, limit=max_results)
    results = search.result()['result']
    # Filter results by duration if available
    filtered = []
    for video in results:
        duration_str = video.get('duration')  # e.g. "12:34" or None
        if duration_str:
            parts = duration_str.split(':')
            seconds = 0
            if len(parts) == 3:  # H:M:S
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:  # M:S
                seconds = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:  # S
                seconds = int(parts[0])
            if seconds <= MAX_DURATION_SECONDS:
                filtered.append((video['title'], video['link']))
        else:
            # No duration info, include to be safe or skip?  
            # Here we skip, but you can change if you want
            pass
    return filtered

def sanitize_filename(title):
    return ''.join(c if c.isalnum() or c in ' ._-()[]' else '_' for c in title)

def is_network_error(error_str):
    network_error_signals = [
        "HTTPError", "ConnectionResetError", "TimeoutError",
        "SSLError", "ConnectionError", "Timeout"
    ]
    return any(signal in error_str for signal in network_error_signals)

def download_audio_with_ytdlp(title, url, output_folder="downloads", quiet=False, retries=2):
    safe_title = sanitize_filename(title)
    mp3_path = os.path.join(output_folder, f"{safe_title}.mp3")

    if os.path.exists(mp3_path):
        with lock:
            tqdm.write(f"⏭️ Skipping (already downloaded): {safe_title}")
        playlist_metadata.append({
            "title": title,
            "url": url,
            "file": mp3_path
        })
        return

    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "-o", os.path.join(output_folder, f"{safe_title}.%(ext)s"),
        url
    ]
    if quiet:
        cmd += ["--quiet", "--no-warnings"]

    for attempt in range(1, retries + 2):
        try:
            subprocess.run(cmd, check=True)
            with lock:
                tqdm.write(f"✅ Downloaded: {safe_title}")
                playlist_metadata.append({
                    "title": title,
                    "url": url,
                    "file": mp3_path
                })
            return
        except subprocess.CalledProcessError as e:
            err_str = str(e)
            if attempt <= retries and is_network_error(err_str):
                with lock:
                    tqdm.write(f"🔁 Retry {attempt} for (network error): {safe_title}")
            else:
                with lock:
                    tqdm.write(f"❌ Failed: {safe_title}")
                    failed_downloads.append({"title": title, "url": url})
                break

def download_mp3s_for_query(query, max_results=10, threads=4):
    print(f"🔍 Searching YouTube for videos ≤15 minutes: '{query}'...")
    video_results = search_youtube(query, max_results)

    if not video_results:
        print("⚠️ No videos found matching duration criteria.")
        return

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        list(tqdm(executor.map(lambda args: download_audio_with_ytdlp(*args, "downloads", True), video_results), total=len(video_results)))

    # Save failed downloads log
    if failed_downloads:
        with open("failed_downloads.log", "w") as f:
            for item in failed_downloads:
                f.write(f"{item['title']} - {item['url']}\n")
        print(f"⚠️ Logged {len(failed_downloads)} failed downloads to failed_downloads.log")

    # Save playlist metadata
    with open("playlist.json", "w") as f:
        json.dump(playlist_metadata, f, indent=2, ensure_ascii=False)
    print("📄 Playlist metadata saved to playlist.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MP3s from YouTube based on a search query, max duration 15 minutes.")
    parser.add_argument("query", type=str, help="Search query for YouTube videos (use quotes for multiple words)")
    parser.add_argument("--max", type=int, default=10, help="Maximum number of results to download (default: 10)")
    parser.add_argument("--threads", type=int, default=4, help="Number of parallel downloads (default: 4)")

    args = parser.parse_args()
    download_mp3s_for_query(args.query, args.max, args.threads)
