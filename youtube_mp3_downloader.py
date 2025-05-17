import argparse
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from youtubesearchpython import VideosSearch
from tqdm import tqdm
import threading

lock = threading.Lock()

def search_youtube(query, max_results=10):
    search = VideosSearch(query, limit=max_results)
    results = search.result()['result']
    return [(video['title'], video['link']) for video in results]

def sanitize_filename(title):
    return ''.join(c if c.isalnum() or c in ' ._-()[]' else '_' for c in title)

def download_audio_with_ytdlp(title, url, output_folder="downloads", quiet=False):
    safe_title = sanitize_filename(title)
    mp3_path = os.path.join(output_folder, f"{safe_title}.mp3")

    if os.path.exists(mp3_path):
        with lock:
            tqdm.write(f"⏭️ Skipping already downloaded: {safe_title}")
        return

    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "-o", os.path.join(output_folder, f"{safe_title}.%(ext)s"),
        url
    ]
    if quiet:
        cmd += ["--quiet", "--no-warnings"]

    try:
        subprocess.run(cmd, check=True)
        with lock:
            tqdm.write(f"✅ Downloaded: {safe_title}")
    except subprocess.CalledProcessError:
        with lock:
            tqdm.write(f"❌ Failed to download: {safe_title}")

def download_mp3s_for_query(query, max_results=10, threads=4):
    print(f"🔍 Searching YouTube for: '{query}'...")
    video_results = search_youtube(query, max_results)

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        list(tqdm(executor.map(lambda args: download_audio_with_ytdlp(*args, "downloads", True), video_results), total=len(video_results)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MP3s from YouTube based on a search query.")
    parser.add_argument("query", type=str, help="Search query for YouTube videos (use quotes for multiple words)")
    parser.add_argument("--max", type=int, default=10, help="Maximum number of results to download (default: 10)")
    parser.add_argument("--threads", type=int, default=4, help="Number of parallel downloads (default: 4)")

    args = parser.parse_args()
    download_mp3s_for_query(args.query, args.max, args.threads)
