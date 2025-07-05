# ShadowPlay Batch Uploader 🎮📤

A modern Python desktop app to automatically upload your NVIDIA ShadowPlay gameplay clips to a selected **YouTube Brand Channel**. Now with:
- Real-time upload progress (with % and MBs)
- Automatic deletion after upload (optional)
- Duplicate video detection using hashing
- **Upload queue management** (pause/resume/cancel/reorder)
- **Multiple YouTube channel support**
- **Upload presets & description templates**
- Clean, user-friendly GUI (ttkbootstrap)

---

## ✨ Features

- 🔄 **Batch Upload**: Upload all `.mp4` files from a folder to your YouTube channel.
- 🎯 **Target Brand Channel**: Uploads under your chosen brand account linked to your Google email.
- 🚀 **Progress Indicators**: Upload % and size (MB) shown live during uploads.
- 🧠 **Duplicate Detection**: Uses file hashing to skip already uploaded clips.
- 🗑️ **Auto Delete**: Optionally deletes video after upload.
- 🌙 **Dark Mode**: Toggle between light and dark themes.
- 🕹️ **Upload Queue**: Pause, resume, cancel, and reorder uploads.
- 👥 **Multiple Channels**: Manage and upload to multiple YouTube channels.
- 📝 **Presets & Templates**: Save upload settings and description templates for reuse.

---

## 📦 Folder Structure

```
ShadowPlayUploader/
├── app/                      # Main application code (GUI, logic, managers)
│   ├── main_enhanced.py      # Enhanced GUI entry point
│   ├── uploader_batch.py     # Backend YouTube upload logic
│   ├── upload_queue.py       # Upload queue management
│   ├── channel_manager.py    # Multiple channel support
│   ├── upload_presets.py     # Presets & templates
│   └── ...
├── resources/                # Static config and template files
│   ├── config.json           # App settings (safe defaults)
│   ├── upload_presets.json   # Preset definitions
│   ├── description_templates.json # Description templates
│   └── client_secrets.json   # (NOT tracked) Google OAuth credentials
├── tokens/                   # (NOT tracked) OAuth tokens
├── tests/                    # Test scripts
├── archive/                  # Old/legacy code
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
├── .gitignore                # Protects secrets/tokens
├── README.md                 # This file
```

---

## 🔧 Setup

1. **Create a Google Cloud Project**  
   - Enable YouTube Data API v3  
   - Download `client_secrets.json` and place it in `resources/` (never upload this file!)

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the app**
```bash
python main.py
```

---

## 🛠 Settings & Usage

- **Auto-delete after upload**: Removes video after successful upload.
- **Dark Mode**: Switch between light/dark themes from UI.
- **Upload Queue**: Pause, resume, cancel, and reorder uploads.
- **Multiple Channels**: Select and manage YouTube channels.
- **Presets & Templates**: Save and reuse upload settings and descriptions.
- **Hash logging**: Ensures same video is not uploaded multiple times.

---

## 🔒 Security & Version Control

- **Sensitive files are protected by `.gitignore`**:
  - `resources/client_secrets.json`, `tokens/`, `token.pickle`, and other secrets are NEVER tracked or uploaded.
- **Safe defaults only** are included in `config.json`.
- **Never share your OAuth credentials or tokens.**

---

## 💡 Inspiration

Built for creators who want to:
- Backup old ShadowPlay clips on YouTube.
- Automate uploads to alternate YouTube channels.
- Clean their local drive after archival.

---

## 🤝 Contributing & Version Control

- All development is tracked in git and on GitHub.
- Please fork, branch, and submit pull requests for improvements.
- See `.gitignore` for files that must never be committed.

---

## Activity Graph
[![Ashutosh's github activity graph](https://github-readme-activity-graph.vercel.app/graph?username=ashutosh00710&bg_color=fffff0&color=708090&line=24292e&point=24292e&area=true&hide_border=true&theme=github-compact)](https://github.com/ashutosh00710/github-readme-activity-graph)
![GitHub Activity Graph](https://github-readme-activity-graph.cyclic.app/graph?username=diluteoxygen&repo=ShadowPlayUploader&theme=github-compact)


