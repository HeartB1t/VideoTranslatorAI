# 🎬 Video Translator AI

AI-powered video dubbing tool that automatically transcribes, translates, and re-dubs videos into 26 languages — 100% local, free, no API keys required by default. Optional features (DeepL, Speaker Diarization) may require a free API key.

## How it works

1. **Transcription** — [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcribes the audio (GPU accelerated)
2. **Voice/music separation** — [Demucs](https://github.com/facebookresearch/demucs) isolates vocals from background music
3. **Translation** — MarianMT (local, offline), Google Translate, DeepL Free, or **Ollama LLM** (Qwen3, slot-aware concise translations)
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
- 🤖 **Ollama LLM translation** *(new in v2.0)* — local LLM (Qwen3, Llama, Mistral) producing slot-aware concise translations for natural dubbing — auto-detects/installs/starts/pulls model on first use
- 🎙️ **Voice cloning** — Coqui XTTS v2 clones the original speaker's voice in the target language (~1.8 GB model), with per-segment adaptive speed and multi-seed retry on hallucinations
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
| **MarianMT** | None — downloads ~298 MB per language pair on first use | None — fully offline after download | ★★★★ |
| **DeepL Free** | Free API key at [deepl.com](https://www.deepl.com/pro-api) | 500k chars/month | ★★★★★ |
| **Ollama LLM** *(recommended for dubbing — new in v2.0)* | Auto-installed on first use (~1 GB Ollama + 5 GB model) | None — fully local | ★★★★★ |

> **MarianMT** uses [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) models, cached locally after the first download. Requires explicit source language (auto-detect not supported — select source language manually). Required Python packages (`sacremoses`, `sentencepiece`) are installed automatically on first selection if missing.

> **Ollama LLM** *(new in v2.0)* is the recommended engine for dubbing because it produces translations aware of the target time slot. Where MarianMT translates literally and produces Italian / Spanish / French ~25% longer than English (forcing audible audio compression on the TTS), the LLM is prompted to keep each segment concise and natural for spoken delivery, achieving a typical char-ratio of 0.85-0.95 vs source. The default model is `qwen3:8b` (5.2 GB on disk, ~6 GB VRAM); `qwen3:4b` (~3 GB) is the lightweight option, `qwen3:14b` the higher-quality one. The pipeline auto-detects the Ollama binary, auto-installs it via the official installer on first use (with consent popup), starts the daemon and pulls the chosen model — no manual setup required. Falls back gracefully to Google Translate if anything is missing.

## Voice Cloning (XTTS v2)

When enabled, the app extracts the speaker's voice from the original video and uses it as reference to clone the voice in the target language.

- Supported languages: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- For the remaining 9 languages, Edge-TTS is used automatically as fallback
- Model (~1.8 GB) downloaded automatically on first use to `~/.local/share/tts/`
- **VAD-filtered reference** (v1.4): 10–15 s of continuous speech selected from the original audio via [silero-vad](https://github.com/snakers4/silero-vad) for better voice cloning quality
- **Generation speed** configurable (`xtts_speed`, default `1.25`): higher values reduce post-processing audio compression artifacts when the translated text is longer than the source slot. Tune via `~/.config/videotranslatorai/config.json` or CLI `--xtts-speed`
- Runs on CUDA or CPU

## Speaker Diarization (pyannote-audio)

When enabled, the app identifies who is speaking in each segment. Combined with Voice Cloning, each speaker's voice is cloned separately — ideal for interviews, podcasts, and multi-person videos.

- Requires a free [HuggingFace token](https://huggingface.co/settings/tokens) (one-time registration)
- **Token stored securely** (v1.4) via the OS keyring: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatic migration from previous plaintext JSON storage
- After the first download, works fully offline
- Model: `pyannote/speaker-diarization-3.1`

## Lip Sync (Wav2Lip)

When enabled, the app applies Wav2Lip GAN to synchronize the subject's mouth movements with the dubbed audio — the person appears to speak the translated language.

- Model (~416 MB) and repo cloned automatically on first use to `~/.local/share/wav2lip/`
- Runs on CUDA (recommended) or CPU
- Increases processing time significantly
- Works best on videos with a single, clearly visible face

## Requirements

- Python 3.10+ (the Windows installer provisions 3.11.9 automatically)
- Windows 10 / 11 (x64), Linux, or macOS
- **NVIDIA GPU strongly recommended** — see GPU table below
- 20 GB free disk space for a full install (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg and all Python packages are installed automatically** on first launch if missing. No manual setup required.

### GPU support

The pipeline uses five GPU-accelerated components (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). GPU coverage is not uniform across vendors:

| GPU | Windows | Linux | Notes |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx or newer, CUDA 12.4 driver) | ✅ full acceleration | ✅ full acceleration | **Recommended.** All 5 components run on GPU. |
| **AMD** (Radeon) | ⚠️ incomplete (DirectML does not support XTTS and faster-whisper) | ⚠️ partial (ROCm works for Demucs/XTTS/pyannote but faster-whisper only supports CUDA) | Works but Whisper transcription stays on CPU and dominates the total time. |
| **Intel Arc** | ⚠️ immature PyTorch XPU support | ⚠️ same | Not tested. |
| **None (CPU only)** | ✅ works | ✅ works | Expect **10-20× slower** than realtime. A 5-minute clip may take 50+ minutes just to transcribe with Whisper large-v3. |

**Recommended NVIDIA VRAM:**

| VRAM | Typical cards | Experience |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Usable, can't run XTTS + Wav2Lip concurrently |
| 8 GB | RTX 3060 Ti, 4060 | Full pipeline, no margin |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Recommended — comfortable** |
| 24 GB | RTX 3090, 4090 | Headroom for large batches |

## Installation

### Windows

1. Clone or download this repository
2. Right-click `setup_windows.bat` → **Run as administrator** → menu shows `[1] Install`
3. The installer automatically:
   - Installs Python 3.11 if not present (system-wide)
   - Installs Git for Windows if not present
   - Installs all Python dependencies (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps, etc.)
   - Downloads and installs ffmpeg
   - Creates a **Public Desktop shortcut** (visible to every Windows account on the PC)

> The installer is **multi-user**: everything is installed system-wide under `%ProgramFiles%\VideoTranslatorAI` and any Windows user on the machine finds the shortcut ready to go. VS C++ Build Tools are **no longer required** — the maintained `coqui-tts` fork ships pre-built wheels.

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

## Uninstall

### Windows

Run `setup_windows.bat` (right-click → **Run as administrator**) and pick `[3] Uninstall` from the menu. Three uninstall sub-modes are offered:

| Mode | Admin required | Scope |
|------|----------------|-------|
| **[1] Full uninstall — one click** | ✅ | Removes the app folder, Public Desktop shortcut, ffmpeg from machine PATH, every user's HF model cache (Whisper/XTTS) and config (`HF token`), and all Python AI packages installed by the installer. At the end it also asks (opt-in) whether to silently uninstall **Python 3.11** and **Git for Windows** via their registry quiet-uninstall strings. |
| **[2] Current user only** | ❌ | Removes only the running user's VTAI config, HF/XTTS cache, and legacy per-user install. **Leaves the system-wide installation intact** so other Windows accounts on the PC can keep using the app. |
| **[3] Custom — granular** | ✅ for system items, ❌ for user items | Y/N prompt for each category: app folder, shortcut, machine PATH, per-user legacy installs, per-user configs/caches, then grouped Python packages (TTS, PyTorch stack, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, pipeline utilities), and finally optional Python 3.11 and Git. |

**Never removed automatically:** Visual Studio C++ Build Tools (if present from older runs). Use *Apps and features* in Windows Settings to remove them manually if desired.

### Linux / macOS

No dedicated uninstaller — remove manually:

```bash
# Python packages installed by the GUI's auto-installer
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision basicsr facexlib dlib ctranslate2

# User data and model caches
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -f  ~/.videotranslatorai_config.json
```

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
