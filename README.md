# 🎬 Video Translator AI

AI-powered video dubbing tool that automatically transcribes, translates, and re-dubs videos into 26 languages — 100% local, free, no API keys required by default. Optional features (DeepL, Speaker Diarization) may require a free API key.

## How it works

1. **Transcription** — [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcribes the audio (GPU accelerated)
2. **Voice/music separation** — [Demucs](https://github.com/facebookresearch/demucs) isolates vocals from background music
3. **Translation** — MarianMT (local, offline) or Google Translate or DeepL Free
4. **Speaker diarization** *(optional)* — [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifies who is speaking in each segment
5. **Dubbing** — [Edge-TTS](https://github.com/rany2/edge-tts) (400+ voices) or [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (voice cloning, per-speaker)
6. **Mixing** — dubbed voice mixed back with original background music
7. **Normalization** — final audio normalized to -23 LUFS (EBU R128 broadcast standard)
8. **Lip Sync** *(optional)* — [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synchronizes mouth movements to the dubbed audio

## Features

- 🖥️ Dark-themed GUI (Tkinter) — no command line needed
- 🌍 **26 target languages** with multiple voices per language
- 🌐 **UI in 26 languages** — the interface itself adapts to your language
- 🎬 **YouTube & URL support** — paste any YouTube link and translate directly (powered by yt-dlp)
- 🎵 Voice/music separation via Demucs (keeps background music)
- 🧠 **MarianMT** — fully local, offline neural translation (Helsinki-NLP, no rate limits, no API key)
- 🎙️ **Voice cloning** — Coqui XTTS v2 clones the original speaker's voice in the target language (~1.8 GB model)
- 👥 **Speaker diarization** — pyannote-audio 3.1 identifies multiple speakers; XTTS clones each voice separately
- 💋 **Lip Sync** — Wav2Lip GAN synchronizes mouth movements to the dubbed audio (~416 MB model)
- 🔊 **Audio normalization** — automatic -23 LUFS loudness normalization (EBU R128)
- ✏️ Subtitle editor — review and correct subtitles before dubbing
- 📦 Batch processing — translate multiple videos or URLs at once
- ⚡ GPU acceleration via CUDA (falls back to CPU automatically)
- 📄 Optional `.srt` subtitle export
- 🔁 **DeepL Free** translation engine (optional — 500k chars/month, requires free API key)
- 🔧 **Auto-install** — missing Python packages and ffmpeg are installed automatically on first launch

## Supported languages

Arabic, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Greek,
Hindi, Hungarian, Indonesian, Italian, Japanese, Korean, Norwegian, Polish,
Portuguese, Romanian, Russian, Spanish, Swedish, Turkish, Ukrainian, Vietnamese

## Translation engines

| Engine | Setup | Limits | Quality |
|--------|-------|--------|---------|
| **Google Translate** *(default)* | None | Unofficial scraping — may be throttled on large videos | ★★★★ |
| **MarianMT** *(recommended for heavy use)* | None — downloads ~298 MB per language pair on first use | None — fully offline after download | ★★★★ |
| **DeepL Free** | Free API key at [deepl.com](https://www.deepl.com/pro-api) | 500k chars/month | ★★★★★ |

> **MarianMT** uses [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) models, cached locally after the first download. Requires explicit source language (auto-detect not supported — select source language manually). Required Python packages (`sacremoses`, `sentencepiece`) are installed automatically on first selection if missing.

## Voice Cloning (XTTS v2)

When enabled, the app extracts the speaker's voice from the original video and uses it as reference to clone the voice in the target language.

- Supported languages: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- For the remaining 9 languages, Edge-TTS is used automatically as fallback
- Model (~1.8 GB) downloaded automatically on first use to `~/.local/share/tts/`
- Runs on CUDA or CPU

## Speaker Diarization (pyannote-audio)

When enabled, the app identifies who is speaking in each segment. Combined with Voice Cloning, each speaker's voice is cloned separately — ideal for interviews, podcasts, and multi-person videos.

- Requires a free [HuggingFace token](https://huggingface.co/settings/tokens) (one-time registration)
- Token is saved locally and reused on subsequent runs
- After the first download, works fully offline
- Model: `pyannote/speaker-diarization-3.1`

## Lip Sync (Wav2Lip)

When enabled, the app applies Wav2Lip GAN to synchronize the subject's mouth movements with the dubbed audio — the person appears to speak the translated language.

- Model (~416 MB) and repo cloned automatically on first use to `~/.local/share/wav2lip/`
- Runs on CUDA (recommended) or CPU
- Increases processing time significantly
- Works best on videos with a single, clearly visible face

## Requirements

- Python 3.9+
- NVIDIA GPU recommended (CUDA 12.4) — CPU works but is slower

> **ffmpeg and all Python packages are installed automatically** on first launch if missing. No manual setup required.

## Installation

### Windows

1. Clone or download this repository
2. Right-click `install_windows.bat` → **Run as administrator**
3. The installer automatically:
   - Installs Python 3.11 if not present
   - Installs all Python dependencies (PyTorch CUDA 12.4, faster-whisper, Demucs, etc.)
   - Installs VS C++ Build Tools (required for Coqui TTS voice cloning)
   - Downloads and installs ffmpeg
   - Creates a Desktop shortcut

### Linux / macOS

```bash
# Clone the repo
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Install PyTorch with CUDA 12.4 (NVIDIA GPU) — skip for CPU only
pip install --break-system-packages torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# Launch — everything else installs automatically on first run
python video_translator_gui.py
```

> On first launch the GUI detects any missing packages (faster-whisper, Demucs, Edge-TTS, etc.) and installs them automatically, streaming the output to the log window. ffmpeg is also installed automatically via `apt-get` / `dnf` / `pacman` (Linux) or downloaded from GitHub (Windows).

## Usage

### GUI

```bash
python video_translator_gui.py
```

**From local files:**
1. Click **Add** to select one or more video files
2. Choose source and target language
3. Select a Whisper model (`small` is a good balance of speed/accuracy)
4. Pick a voice and adjust TTS speed if needed
5. *(Optional)* Select translation engine: **Google** (default), **MarianMT** (local/offline), or **DeepL Free**
6. *(Optional)* Enable **Voice Cloning** (XTTS v2) and/or **Speaker Diarization**
7. *(Optional)* Enable **Lip Sync** (Wav2Lip)
8. Click **Start Translation**

**From YouTube (or any supported site):**
1. Paste one or more URLs in the **URL** field (one per line)
2. Configure language, model and voice as usual
3. Click **⬇ Download & Translate**

> yt-dlp supports YouTube, Vimeo, Twitter/X, TikTok, and [1000+ other sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Fair use notice:** Downloading videos via yt-dlp is considered automated access by platforms like YouTube and may violate their Terms of Service. Heavy or repeated use from the same IP address can result in temporary blocks (HTTP 429 / sign-in required errors). Use a VPN or rotate your IP if you encounter download failures. This tool is intended for personal, non-commercial use only. Redistribution of translated content may infringe copyright — always respect the original creator's rights.

### Command line

```bash
python video_translator_gui.py video.mp4 --lang-target en
```

**All options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--lang-source` | Source language (`auto` for auto-detect) | `auto` |
| `--lang-target` | Target language code (e.g. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS voice name | auto |
| `--model` | Whisper model (`tiny` → `large-v3`) | `small` |
| `--tts-rate` | TTS speed adjustment (e.g. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian`, or `deepl` | `google` |
| `--deepl-key` | DeepL Free API key | — |
| `--diarize` | Enable speaker diarization (pyannote) | — |
| `--hf-token` | HuggingFace token for diarization | — |
| `--lipsync` | Apply Wav2Lip lip sync after dubbing | — |
| `--subs-only` | Generate `.srt` only, skip dubbing | — |
| `--no-subs` | Skip `.srt` generation | — |
| `--no-demucs` | Skip voice/music separation | — |
| `--output` / `-o` | Output file path | auto |
| `--batch` | Process multiple files | — |

**Examples:**

```bash
# Translate Italian video to English with local MarianMT
# (downloads ~298 MB model on first use, then fully offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Translate with voice cloning + speaker diarization
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Translate with lip sync
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Subtitles only (no dubbing)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

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
