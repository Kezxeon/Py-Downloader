# 🚀 Spotify & YouTube Downloader

A cross-platform tool for downloading music and videos from **Spotify** and **YouTube**  
with playlist support, metadata tagging, and multiple output formats.

---

## 🔧 **Prerequisites**
- **Python 3.8+**
- **Spotify Developer Account** (required for API keys)
- **yt-dlp** *(auto-installed if missing)*

---

## 🎧 **Spotify API Setup**
1. Go to the **Spotify Developer Dashboard**
2. Create a **new app**
3. Copy your **Client ID** and **Client Secret**
4. Paste them into the app’s settings panel

---

## 📘 **Basic Usage**

### 🎵 **Download Spotify Playlist**
- Copy the **Spotify playlist URL**
- Paste it into the application
- Choose an **output folder**
- Click **Start Conversion**

### ▶️ **Download YouTube Content**
- Enter a **YouTube URL** or **search query**
- Select **MP3 (audio)** or **MP4 (video)**
- Choose a **save location**
- Start the download

---

## ⚙️ **Configuration**

### **Default Settings**
- **Output Path:**  
  - PC: `~/Music/Spotify Downloads/`  
  - Termux: `~/downloads/`
- **Audio Quality:** `192K MP3`
- **Video Format:** `MP4`
- **Theme:** Dark Mode

---

### **Customizable Options**
- Audio Quality: `128K`, `192K`, `320K`
- Audio Formats: `MP3`, `M4A`, `FLAC`
- Video Formats: `MP4`, `MKV`, `AVI`
- Output Directory
- UI Theme / Colors

---

## 📦 **Dependencies**

### **Core**
- `yt-dlp` — YouTube downloader
- `spotipy` — Spotify Web API wrapper
- `ffmpeg` — Recommended for media processing

### **GUI Version**
- `customtkinter` — Modern UI toolkit

### **CLI Version**
- `rich` — Terminal styling

---

## 🛠️ **Common Issues & Fixes**

### **Spotify API Issues**
- ❌ **Invalid credentials** → Recheck Client ID/Secret  
- ❌ **Playlist not found** → Ensure it’s public or accessible  
- ❌ **Rate limited** → Wait before retrying  

### **Download Issues**
- ⚠️ **No audio in videos** → Install `ffmpeg`  
- ⚠️ **Metadata missing** → Update `yt-dlp`  
- ⚠️ **Slow speeds** → Check network or lower quality  

### **Platform Notes**
- **Windows:** Run as Administrator if permissions fail  
- **Termux:**  
  ```bash
  termux-setup-storage
