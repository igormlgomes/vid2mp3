import argparse
import os
import subprocess
from youtubesearchpython import VideosSearch

def search_youtube(query, max_results=10):
    search = VideosSearch(query, limit=max_results)
    results = search.result()['result']
    video_urls = [video['link'] for video in results]
    return video_urls

def download_audio_with_ytdlp(url, output_folder="downloads"):
    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Output template: downloads/<video title>.mp3
        cmd = [
            "yt-dlp",
            "-x", "--audio-format", "mp3",
            "-o", os.path.join(output_folder, "%(title)s.%(ext)s"),
            url
        ]

        subprocess.run(cmd, check=True)
        print(f"✅ Downloaded and converted: {url}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to download {url}: {e}")

def download_mp3s_for_query(query, max_results=10):
    print(f"🔍 Searching YouTube for: '{query}'...")
    video_urls = search_youtube(query, max_results)

    for i, url in enumerate(video_urls, start=1):
        print(f"\n⬇️ [{i}/{len(video_urls)}] Processing: {url}")
        download_audio_with_ytdlp(url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MP3s from YouTube based on a search query.")
    parser.add_argument("query", type=str, help="Search query for YouTube videos (use quotes for multiple words)")
    parser.add_argument("--max", type=int, default=10, help="Maximum number of results to download (default: 10)")

    args = parser.parse_args()
    download_mp3s_for_query(args.query, args.max)
