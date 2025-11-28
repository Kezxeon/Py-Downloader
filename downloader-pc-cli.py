import os
import re
import sys
import json
import configparser
import subprocess
from pathlib import Path
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy

console = Console()

CONFIG_FILE = "spotify_converter.cfg"
DEFAULT_CONFIG = {
    "Spotify": {"client_id": "", "client_secret": ""},
    "Settings": {"output_path": str(Path.home() / "Music" / "Spotify Downloads")},
    "Download": {"audio_quality": "192K", "format": "mp3", "video_format": "mp4"},
}


def log(message, level="info"):
    colors = {
        "info": "magenta",
        "success": "green",
        "error": "red",
        "warning": "orange1",
    }
    icon = {
        "info": "[*]",
        "success": "[+]",
        "error": "[x]",
        "warning": "[!]",
    }
    console.print(f"{icon.get(level, '[*]')} [bold {colors[level]}]{message}[/]")


def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        config.read_dict(DEFAULT_CONFIG)
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
        log(f"Created new config file: {CONFIG_FILE}", "info")
    else:
        config.read(CONFIG_FILE)
        for section in DEFAULT_CONFIG:
            if section not in config:
                config[section] = {}
            for key, val in DEFAULT_CONFIG[section].items():
                if key not in config[section]:
                    config[section][key] = val
    return config


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        config.write(f)


def sanitize_filename(name):
    """Remove invalid characters for Windows filenames"""
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def initialize_spotify_client(config):
    try:
        cid = config["Spotify"]["client_id"]
        secret = config["Spotify"]["client_secret"]
        if not cid or not secret:
            log("Spotify API credentials not set. Configure them first.", "error")
            return None
        auth = SpotifyClientCredentials(client_id=cid, client_secret=secret)
        return spotipy.Spotify(auth_manager=auth)
    except Exception as e:
        log(f"Spotify client error: {e}", "error")
        return None


def download_youtube(query, output_path, is_video=False, config=None):
    if config is None:
        config = load_config()

    output_template = os.path.join(output_path, "%(title)s.%(ext)s")
    command = ["yt-dlp", "-o", output_template, "--no-warnings"]

    if is_video:
        video_format = config["Download"]["video_format"]
        command += [
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "--merge-output-format",
            video_format,
        ]
        if not re.match(r"^https?://", query):
            query = f"ytsearch1:{query} official video"
    else:
        audio_format = config["Download"]["format"]
        audio_quality = config["Download"]["audio_quality"]
        command += [
            "-x",
            "--audio-format",
            audio_format,
            "--audio-quality",
            audio_quality,
            "--embed-thumbnail",
            "--add-metadata",
            "--embed-metadata",
            "--prefer-ffmpeg",
        ]
        if not re.match(r"^https?://", query):
            query = f"ytsearch1:{query} official audio"

    command.append(query)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold magenta]Downloading...[/]"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("download", total=None)
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            progress.update(task, completed=1)

        if result.returncode == 0:
            return True
        else:
            log(f"Download failed: {result.stderr}", "error")
            return False

    except Exception as e:
        log(f"Download error: {e}", "error")
        return False


def convert_spotify_playlist(spotify, url, output_dir, config):
    match = re.search(r"(?:playlist/|playlist:)([a-zA-Z0-9]+)", url)
    if not match:
        log("Invalid Spotify playlist URL", "error")
        return

    try:
        playlist = spotify.playlist(match.group(1))
        name = sanitize_filename(playlist["name"])
        full_path = os.path.join(output_dir, name)
        os.makedirs(full_path, exist_ok=True)

        log(f"Playlist: {name}", "info")
        log(f"Output directory: {full_path}", "info")

        tracks = playlist["tracks"]["items"]

        # Handle pagination for large playlists
        while playlist["tracks"]["next"]:
            playlist["tracks"] = spotify.next(playlist["tracks"])
            tracks.extend(playlist["tracks"]["items"])

        log(f"Found {len(tracks)} tracks in playlist", "info")

        successful_downloads = 0
        skipped_downloads = 0
        failed_downloads = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold magenta]Downloading tracks...[/]"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("playlist", total=len(tracks))

            for i, item in enumerate(tracks, 1):
                track = item["track"]
                if not track:  # Skip null tracks
                    continue

                title = track["name"]
                artist = ", ".join([a["name"] for a in track["artists"]])
                query = f"{artist} - {title}"
                filename = os.path.join(full_path, sanitize_filename(f"{query}.mp3"))

                if os.path.exists(filename):
                    log(f"[{i}/{len(tracks)}] Skipping (exists): {query}", "warning")
                    skipped_downloads += 1
                    progress.advance(task)
                    continue

                log(f"[{i}/{len(tracks)}] Downloading: {query}", "info")
                success = download_youtube(
                    query, full_path, is_video=False, config=config
                )
                if success:
                    log(f"[{i}/{len(tracks)}] ✓ Downloaded: {query}", "success")
                    successful_downloads += 1
                else:
                    log(f"[{i}/{len(tracks)}] ✗ Failed: {query}", "error")
                    failed_downloads += 1

                progress.advance(task)

        # Summary
        log(
            f"Download complete: {successful_downloads} successful, {skipped_downloads} skipped, {failed_downloads} failed",
            "info",
        )

    except Exception as e:
        log(f"Error converting playlist: {e}", "error")


def download_single(config):
    url = input("Enter YouTube URL or search query: ").strip()
    if not url:
        log("No input provided", "error")
        return

    vtype = input("Download as (m)usic or (v)ideo? [m/v]: ").lower().strip()
    is_video = vtype == "v"
    output_path = config["Settings"]["output_path"]
    os.makedirs(output_path, exist_ok=True)

    success = download_youtube(url, output_path, is_video, config)
    if success:
        log("Download completed successfully!", "success")
    else:
        log("Download failed!", "error")


def configure_spotify_api(config):
    console.print("\n[bold cyan]Spotify API Configuration[/]")
    console.print("To get Spotify API credentials:")
    console.print("1. Go to [link]https://developer.spotify.com/dashboard[/]")
    console.print("2. Log in and create an app")
    console.print("3. Copy the Client ID and Client Secret\n")

    cid = input("Enter Spotify Client ID: ").strip()
    secret = input("Enter Spotify Client Secret: ").strip()

    if cid and secret:
        config["Spotify"]["client_id"] = cid
        config["Spotify"]["client_secret"] = secret
        save_config(config)
        log("Spotify credentials saved successfully!", "success")
    else:
        log("Invalid credentials provided", "error")


def set_output_directory(config):
    current_path = config["Settings"]["output_path"]
    console.print(f"\n[bold cyan]Current output directory:[/] {current_path}")

    path = input(
        "Enter new output directory path (press Enter to keep current): "
    ).strip()

    if not path:
        log("Output directory unchanged", "info")
        return

    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        config["Settings"]["output_path"] = path
        save_config(config)
        log(f"Output path set to: {path}", "success")
    except Exception as e:
        log(f"Invalid directory: {e}", "error")


def configure_download_settings(config):
    console.print("\n[bold cyan]Download Settings[/]")

    current_quality = config["Download"]["audio_quality"]
    current_format = config["Download"]["format"]
    current_video_format = config["Download"]["video_format"]

    console.print(f"1. Audio Quality (current: {current_quality})")
    console.print(f"2. Audio Format (current: {current_format})")
    console.print(f"3. Video Format (current: {current_video_format})")

    choice = input("\nChoose setting to change (1-3) or Enter to cancel: ").strip()

    if choice == "1":
        quality = input("Enter audio quality (e.g., 128K, 192K, 320K): ").strip()
        if quality:
            config["Download"]["audio_quality"] = quality
            save_config(config)
            log(f"Audio quality set to: {quality}", "success")

    elif choice == "2":
        format_choice = input("Enter audio format (mp3, m4a, flac, etc.): ").strip()
        if format_choice:
            config["Download"]["format"] = format_choice
            save_config(config)
            log(f"Audio format set to: {format_choice}", "success")

    elif choice == "3":
        video_format = input("Enter video format (mp4, mkv, avi, etc.): ").strip()
        if video_format:
            config["Download"]["video_format"] = video_format
            save_config(config)
            log(f"Video format set to: {video_format}", "success")


def check_dependencies():
    """Check if required dependencies are installed"""
    missing_deps = []

    # Check yt-dlp
    try:
        subprocess.run(["yt-dlp", "--version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        missing_deps.append("yt-dlp")

    # Check ffmpeg (optional but recommended)
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        log("FFmpeg not found - some features may not work properly", "warning")

    # Check spotipy
    try:
        import spotipy
    except ImportError:
        missing_deps.append("spotipy")

    if missing_deps:
        console.print("\n[red][x] Missing dependencies:[/]")
        for dep in missing_deps:
            if dep == "yt-dlp":
                console.print(
                    "    • yt-dlp: Download and install from https://github.com/yt-dlp/yt-dlp"
                )
            elif dep == "spotipy":
                console.print("    • spotipy: Run: pip install spotipy")
        return False

    return True


def menu():
    if not check_dependencies():
        sys.exit(1)

    config = load_config()

    while True:
        console.print("\n[bold magenta]🎵 Spotify & YouTube Downloader 🎵[/]\n")
        console.print("[cyan]1.[/] Convert Spotify Playlist")
        console.print("[cyan]2.[/] Download Single YouTube Video/Music")
        console.print("[cyan]3.[/] Configure Spotify API")
        console.print("[cyan]4.[/] Set Output Directory")
        console.print("[cyan]5.[/] Download Settings")
        console.print("[cyan]6.[/] Exit")

        choice = input("\nChoose an option (1-6): ").strip()

        if choice == "1":
            spotify = initialize_spotify_client(config)
            if not spotify:
                continue
            url = input("Enter Spotify Playlist URL: ").strip()
            output_path = config["Settings"]["output_path"]
            convert_spotify_playlist(spotify, url, output_path, config)

        elif choice == "2":
            download_single(config)

        elif choice == "3":
            configure_spotify_api(config)

        elif choice == "4":
            set_output_directory(config)

        elif choice == "5":
            configure_download_settings(config)

        elif choice == "6":
            console.print("[green]Goodbye![/]")
            break

        else:
            log("Invalid choice. Please try again.", "warning")


if __name__ == "__main__":
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")

    menu()
