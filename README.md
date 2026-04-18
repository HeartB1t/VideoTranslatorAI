# 🎬 Video Translator AI

AI-powered video dubbing tool that automatically transcribes, translates, and re-dubs videos into 26 languages.

## How it works

1. **Transcription** — [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcribes the audio (GPU accelerated)
2. **Voice/music separation** — [Demucs](https://github.com/facebookresearch/demucs) isolates vocals from background music
3. **Translation** — [Google Translate](https://pypi.org/project/deep-translator/) translates the subtitles
4. **Dubbing** — [Edge-TTS](https://github.com/rany2/edge-tts) generates the dubbed audio (400+ voices)
5. **Mixing** — the dubbed voice is mixed back with the original background music

## Features

- 🖥️ Dark-themed GUI (Tkinter) — no command line needed
- 🌍 26 target languages with multiple voices per language
- 🎵 Voice/music separation via Demucs (keeps background music)
- ✏️ Subtitle editor — review and correct subtitles before dubbing
- 📦 Batch processing — translate multiple videos at once
- ⚡ GPU acceleration via CUDA (falls back to CPU automatically)
- 🌐 UI available in Italian and English
- 📄 Optional `.srt` subtitle export

## Supported languages

Arabic, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Greek,
Hindi, Hungarian, Indonesian, Italian, Japanese, Korean, Norwegian, Polish,
Portuguese, Romanian, Russian, Spanish, Swedish, Turkish, Ukrainian, Vietnamese

## Requirements

- Python 3.9+
- ffmpeg
- NVIDIA GPU recommended (CUDA 12.4) — CPU works but is slower

## Installation

### Windows

1. Download or clone this repository
2. Double-click `install_windows.bat`
3. The installer will automatically:
   - Install all Python dependencies
   - Install PyTorch with CUDA 12.4
   - Download ffmpeg
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

1. Click **Add** to select one or more video files
2. Choose the source and target language
3. Select a Whisper model (`small` is a good balance of speed/accuracy)
4. Pick a voice and adjust TTS speed if needed
5. Click **Start Translation**

### Command line

```bash
python video_translator.py video.mp4 --lang-target it --voice it-IT-ElsaNeural
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
