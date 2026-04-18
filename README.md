# 🎬 Video Translator AI

AI-powered video dubbing tool that automatically transcribes, translates, and re-dubs videos into 26 languages — 100% local, free, no API keys required.

## How it works

1. **Transcription** — [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcribes the audio (GPU accelerated)
2. **Voice/music separation** — [Demucs](https://github.com/facebookresearch/demucs) isolates vocals from background music
3. **Translation** — Google Translate (default) or DeepL Free (optional)
4. **Dubbing** — [Edge-TTS](https://github.com/rany2/edge-tts) (400+ voices) or [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (voice cloning)
5. **Mixing** — dubbed voice mixed back with original background music
6. **Normalization** — final audio normalized to -23 LUFS (EBU R128 broadcast standard)

## Features

- 🖥️ Dark-themed GUI (Tkinter) — no command line needed
- 🎬 **YouTube & URL support** — paste any YouTube link and translate directly (powered by yt-dlp)
- 🌍 26 target languages with multiple voices per language
- 🎵 Voice/music separation via Demucs (keeps background music)
- 🎙️ **Voice cloning** — [Coqui XTTS v2](https://github.com/coqui-ai/TTS) clones the original speaker's voice in the target language (optional, ~1.8 GB model)
- 🔊 **Audio normalization** — automatic -23 LUFS loudness normalization (EBU R128)
- ✏️ Subtitle editor — review and correct subtitles before dubbing
- 📦 Batch processing — translate multiple videos or URLs at once
- ⚡ GPU acceleration via CUDA (falls back to CPU automatically)
- 🌐 UI available in Italian and English
- 📄 Optional `.srt` subtitle export
- 🔁 **DeepL Free** translation engine (optional — 500k chars/month free, requires API key)

## Supported languages

Arabic, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Greek,
Hindi, Hungarian, Indonesian, Italian, Japanese, Korean, Norwegian, Polish,
Portuguese, Romanian, Russian, Spanish, Swedish, Turkish, Ukrainian, Vietnamese

## Voice Cloning (XTTS v2)

When enabled, the app extracts the speaker's voice from the original video (via Demucs) and uses it as reference to clone the voice in the target language.

- Supported languages: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- For the remaining 9 languages, Edge-TTS is used automatically as fallback
- Model (~1.8 GB) is downloaded automatically on first use
- Runs on CUDA or CPU

## Requirements

- Python 3.9+
- ffmpeg
- NVIDIA GPU recommended (CUDA 12.4) — CPU works but is slower

## Installation

### Windows

1. Download or clone this repository
2. Right-click `install_windows.bat` → **Run as administrator**
3. The installer will automatically:
   - Install Python 3.11 if not present
   - Install all Python dependencies (PyTorch CUDA 12.4, faster-whisper, Demucs, etc.)
   - Install VS C++ Build Tools (required for Coqui TTS voice cloning)
   - Download and install ffmpeg
   - Create a Desktop shortcut

### Linux / macOS

```bash
# Install ffmpeg
sudo apt install ffmpeg       # Debian/Ubuntu/Kali
# brew install ffmpeg         # macOS

# Install Python dependencies
pip install -r requirements.txt

# Install PyTorch with CUDA 12.4 (NVIDIA GPU)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# Launch the GUI
python video_translator_gui.py
```

## Usage

### GUI

```bash
python video_translator_gui.py
```

**From local files:**
1. Click **Add** to select one or more video files
2. Choose the source and target language
3. Select a Whisper model (`small` is a good balance of speed/accuracy)
4. Pick a voice and adjust TTS speed if needed
5. (Optional) Check **Voice Cloning** to clone the original speaker's voice
6. Click **Start Translation**

**From YouTube (or any supported site):**
1. Paste one or more URLs in the **URL** field (one per line)
2. Configure language, model and voice as usual
3. Click **⬇ Download & Translate** — the app downloads and translates automatically

> yt-dlp supports YouTube, Vimeo, Twitter/X, TikTok, and [1000+ other sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

**Translation engines (Options):**
- **Google Translate** — default, no setup required, no rate limits for typical use
- **DeepL Free** — optional, higher quality, 500k characters/month free ([register at deepl.com](https://www.deepl.com/pro-api))

### Command line

```bash
python video_translator_gui.py video.mp4 --lang-target it --voice it-IT-ElsaNeural
```

**Main options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--lang-source` | Source language (`auto` for auto-detect) | `auto` |
| `--lang-target` | Target language code (e.g. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS voice name | auto |
| `--model` | Whisper model (`tiny` → `large-v3`) | `small` |
| `--tts-rate` | TTS speed adjustment (e.g. `+10%`, `-20%`) | `+0%` |
| `--subs-only` | Generate `.srt` only, skip dubbing | — |
| `--no-subs` | Skip `.srt` generation | — |
| `--no-demucs` | Skip voice/music separation | — |
| `--output` / `-o` | Output file path | auto |
| `--batch` | Process multiple files | — |

## Whisper models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1.5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |

> Models are downloaded automatically on first use.

## License

MIT
