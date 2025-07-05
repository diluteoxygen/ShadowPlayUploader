# ShadowPlay Batch Uploader 🎮📤

A minimal, modern Python desktop app that automatically uploads your NVIDIA ShadowPlay gameplay clips to a selected **YouTube Brand Channel**, with features like:
- Real-time upload progress (with % and MBs),
- Automatic deletion after upload (optional),
- Duplicate video detection using hashing,
- Clean and user-friendly GUI inspired by Apple’s design principles.

---

## ✨ Features

- 🔄 **Batch Upload**: Upload all `.mp4` files from a folder to your YouTube channel.
- 🎯 **Target Brand Channel**: Uploads under your chosen brand account linked to your Google email.
- 🚀 **Progress Indicators**: Upload % and size (MB) shown live during uploads.
- 🧠 **Duplicate Detection**: Uses file hashing to skip already uploaded clips.
- 🗑️ **Auto Delete**: Optionally deletes video after upload.
- 🌙 **Dark Mode**: Toggle between light and dark themes.

---

## 📦 Folder Structure

```
ShadowPlayUploader/
├── main.py                # GUI frontend (ttkbootstrap)
├── uploader_batch.py      # Backend YouTube upload logic
├── client_secrets.json    # Your Google OAuth credentials
├── token.pickle           # Auth token (auto-generated)
├── uploaded_hashes.txt    # Hashes of uploaded videos
├── README.md              # This file
```

---

## 🔧 Setup

1. **Create a Google Cloud Project**  
   - Enable YouTube Data API v3  
   - Download `client_secrets.json`

2. **Install dependencies**
```bash
pip install google-auth google-auth-oauthlib google-api-python-client ttkbootstrap
```

3. **Run the app**
```bash
python main.py
```

---

## 🛠 Settings

- **Auto-delete after upload**: Removes video after successful upload.
- **Dark Mode**: Switch between light/dark themes from UI.
- **Hash logging**: Ensures same video is not uploaded multiple times.

---

## 💡 Inspiration

Built for creators who want to:
- Backup old ShadowPlay clips on YouTube.
- Automate uploads to alternate YouTube channels.
- Clean their local drive after archival.

---

## ⚠️ Notes

- All clips must be `.mp4` and located in the selected folder.
- Only uploads completed files (waits if a file is being written).
- You must authorize the app once on first launch (OAuth consent screen).

---

## 🧠 Credits

Created by **Dilute Oxygen**  
- MCA Student, IET Lucknow  
- Passionate about clean tooling, AI dev, and productivity hacks.

MIT License.
