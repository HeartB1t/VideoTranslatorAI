# 🎬 Video Translator AI

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

AI-powered video dubbing tool that automatically transcribes, translates, and re-dubs videos into 26 languages, with local processing options and no API keys required by default. Whisper speech recognition runs locally; Edge-TTS, Google Translate and DeepL require an internet connection. Optional features (DeepL, Speaker Diarization) may require an API key or access token.

> **v2.0** - modular package, local Ollama translation, quality-profile orchestration, installable Python metadata, and opt-in heavy smoke tests. See [GitHub Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) and the commit history for the full list of changes.

## How it works

1. **Transcription** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcribes the audio (GPU accelerated)
2. **Voice/music separation** - [Demucs](https://github.com/facebookresearch/demucs) isolates vocals from background music
3. **Translation** - MarianMT (local, offline), Google Translate, DeepL Free, or **Ollama LLM** (Qwen3, slot-aware concise translations)
4. **Speaker diarization** *(optional)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifies who is speaking in each segment
5. **Dubbing** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ voices) or [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (voice cloning, per-speaker)
6. **Mixing** - dubbed voice mixed back with original background music
7. **Normalization** - final audio normalized to -23 LUFS (EBU R128 broadcast standard)
8. **Lip Sync** *(optional)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synchronizes mouth movements to the dubbed audio

## Features

- 🖥️ Themed GUI (Tkinter) - no command line needed; Graphite, Slate, Light and Neon themes, accent colours, text size, and cards you can reorder by dragging
- 🌍 **26 target languages** with multiple voices per language
- 🌐 **UI in 26 languages** - the interface itself adapts to your language
- 🎬 **YouTube & URL support** - paste any YouTube link and translate directly (powered by yt-dlp)
- ▶️ **Integrated video player** (libmpv/mpv) - colour-coded transport controls, playlist, A/B original vs dubbed audio, subtitles toggle, snapshot, fullscreen, open folder
- ⏱️ **Real-time translation** - watch a local file or a resolved on-demand video link with translated subtitles and a YouTube-style delay slider; engines MarianMT / Google / DeepL / Ollama. Experimental voice dubbing uses Edge-TTS and a second mpv instance. Voice overlap handling and real audio/Windows acceptance remain in progress; growing live broadcasts are not supported yet. See the [live implementation status](docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Voice/music separation via Demucs (keeps background music)
- 🔇 **Mute original audio**, available before and during live translation, silences the video's soundtrack while keeping the translated voice audible. Toggle it off to restore the original audio; it resets when the live session ends.
- 🧠 **MarianMT** - fully local, offline neural translation (Helsinki-NLP, no rate limits, no API key)
- 🤖 **Ollama LLM translation** *(new in v2.0)* - local LLM (Qwen3, Llama, Mistral) producing slot-aware concise translations for natural dubbing, auto-detects/installs/starts/pulls model on first use
- 🎙️ **Voice cloning** - Coqui XTTS v2 clones the original speaker's voice in the target language (~1.8 GB model), with per-segment adaptive speed and multi-seed retry on hallucinations
- 👥 **Speaker diarization** - pyannote-audio 3.1 identifies multiple speakers; XTTS clones each voice separately
- 💋 **Lip Sync** - Wav2Lip GAN synchronizes mouth movements to the dubbed audio (~416 MB model)
- 🔊 **Audio normalization** - automatic -23 LUFS loudness normalization (EBU R128)
- ✏️ Subtitle editor - review and correct subtitles before dubbing
- 📦 Batch processing - translate multiple videos or URLs at once
- ⚡ GPU acceleration via CUDA (falls back to CPU automatically)
- 📄 Optional `.srt` subtitle export
- 🔁 **DeepL Free** translation engine (optional - 500k chars/month, requires free API key)
- 🔧 **Auto-install** - missing Python packages and ffmpeg are installed automatically on first launch

## Supported languages

Arabic, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Greek,
Hindi, Hungarian, Indonesian, Italian, Japanese, Korean, Norwegian, Polish,
Portuguese, Romanian, Russian, Spanish, Swedish, Turkish, Ukrainian, Vietnamese

## Voice Catalog

The Edge-TTS voice catalog is defined in `LANGUAGES` near the top of
`video_translator_gui.py`. That dictionary is the source of truth for target
language names, GUI voice radio buttons, and the CLI fallback voice when
`--voice` is omitted.

Claude/project-maintenance notes mirror this location in `CLAUDE.md` under
**Voice Catalog Source Of Truth**, so future code agents know where to update
voices and where the README points users.

## Translation engines

| Engine | Setup | Limits | Quality |
|--------|-------|--------|---------|
| **Google Translate** *(default)* | None | Unofficial scraping - may be throttled on large videos | ★★★★ |
| **MarianMT** | None - downloads ~298 MB per language pair on first use | None - fully offline after download | ★★★★ |
| **DeepL Free** | Free API key at [deepl.com](https://www.deepl.com/pro-api) | 500k chars/month | ★★★★★ |
| **Ollama LLM** *(recommended for dubbing - new in v2.0)* | Auto-installed on first use (~1 GB Ollama + 5 GB model) | None - fully local | ★★★★★ |

> **MarianMT** uses [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) models, cached locally after the first download. Requires explicit source language (auto-detect not supported - select source language manually). Required Python packages (`sacremoses`, `sentencepiece`) are installed automatically on first selection if missing.

> **Ollama LLM** *(new in v2.0)* is the recommended engine for dubbing because it produces translations aware of the target time slot. Where MarianMT translates literally and produces Italian / Spanish / French ~25% longer than English (forcing audible audio compression on the TTS), the LLM is prompted to keep each segment concise and natural for spoken delivery, achieving a typical char-ratio of 0.85-0.95 vs source. The default model is `qwen3:8b` (5.2 GB on disk, ~6 GB VRAM); `qwen3:4b` (~3 GB) is the lightweight option, `qwen3:14b` the higher-quality one. The pipeline auto-detects the Ollama binary, auto-installs it via the official installer on first use (with consent popup), starts the daemon and pulls the chosen model - no manual setup required. Falls back gracefully to Google Translate if anything is missing.

## Voice Cloning (XTTS v2)

When enabled, the app extracts the speaker's voice from the original video and uses it as reference to clone the voice in the target language.

- Supported languages: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- For the remaining 9 languages, Edge-TTS is used automatically as fallback
- Model (~1.8 GB) downloaded automatically on first use to `~/.local/share/tts/`
- **VAD-filtered reference** (v1.4): 10-15 s of continuous speech selected from the original audio via [silero-vad](https://github.com/snakers4/silero-vad) for better voice cloning quality
- **Generation speed** configurable (`xtts_speed`, default `1.25`): higher values reduce post-processing audio compression artifacts when the translated text is longer than the source slot. Tune via `~/.config/videotranslatorai/config.json` or CLI `--xtts-speed`
- Runs on CUDA or CPU

## Speaker Diarization (pyannote-audio)

When enabled, the app identifies who is speaking in each segment. Combined with Voice Cloning, each speaker's voice is cloned separately - ideal for interviews, podcasts, and multi-person videos.

- Requires a free [HuggingFace token](https://huggingface.co/settings/tokens) (one-time registration)
- **Token stored securely** (v1.4) via the OS keyring: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatic migration from previous plaintext JSON storage
- After the first download, works fully offline
- Model: `pyannote/speaker-diarization-3.1`

## Lip Sync (Wav2Lip)

When enabled, the app applies Wav2Lip GAN to synchronize the subject's mouth movements with the dubbed audio - the person appears to speak the translated language.

- Model (~416 MB) and repo cloned automatically on first use to `~/.local/share/wav2lip/`
- Runs on CUDA (recommended) or CPU
- Increases processing time significantly
- Works best on videos with a single, clearly visible face

## Requirements

- Python 3.10+ (the Windows installer provisions 3.11.9 automatically)
- Windows 10 / 11 (x64), Linux, or macOS
- **NVIDIA GPU strongly recommended** - see GPU table below
- 20 GB free disk space for a full install (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg and all Python packages are installed automatically** on first launch if missing. No manual setup required.

**Optional system dependency** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). When installed it is used for pitch-preserving time-stretching in the profile-controlled quality band (default 1.15-1.50, up to 1.65 for hard content), removing the residual "chipmunk" effect on cloned XTTS voices. The pipeline runs unchanged without it (auto-fallback to ffmpeg `atempo`). Quality profiles now prefer extra short-translation retries over extreme audio speed-up.

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
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Recommended - comfortable** |
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
   - Installs the integrated video player (python-mpv plus a libmpv build in `mpv-runtime`). The step is optional: if it fails, everything else works and the player pane explains what is missing
   - Creates a **Public Desktop shortcut** (visible to every Windows account on the PC)

> The installer is **multi-user**: everything is installed system-wide under `%ProgramFiles%\VideoTranslatorAI` and any Windows user on the machine finds the shortcut ready to go. VS C++ Build Tools are **no longer required** - the maintained `coqui-tts` fork ships pre-built wheels.

### Linux / macOS

```bash
# Clone the repo
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Optional: install the tested NVIDIA CUDA 12.4 PyTorch stack up front
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Optional: pre-install all Python runtime packages instead of letting the GUI
# install missing packages on first run
pip install --break-system-packages -r requirements.txt

# Optional: the integrated video player (libmpv from the distribution, python-mpv from PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Optional: install the project as an editable Python package
pip install --break-system-packages --no-deps -e .

# Launch from source
python video_translator_gui.py

# Or, after editable/package install
videotranslatorai
videotranslatorai --preflight
```

> On first launch the GUI detects any missing packages (faster-whisper, Demucs, Edge-TTS, etc.) and installs them automatically, streaming the output to the log window. ffmpeg is also installed automatically via `apt-get` / `dnf` / `pacman` (Linux) or downloaded from GitHub (Windows).

> The header shows a **Player** badge. When libmpv or python-mpv is missing, the left pane says what is missing and offers **Install player**: on Linux it uses the package manager through pkexec (then `sudo -n`) and shows the manual command when neither works; on Windows it asks before downloading libmpv for the current user (about 32 MB).

### Requirement profiles

| File | Purpose |
|------|---------|
| `requirements.txt` | Full, backward-compatible runtime install. |
| `requirements-core.txt` | Default pipeline packages used by GUI/CLI. |
| `requirements-optional.txt` | XTTS, MarianMT tokenizers, diarization, VAD, keyring. |
| `requirements-wav2lip.txt` | Wav2Lip runtime and face-detection stack (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch stack tested with NVIDIA CUDA 12.4 wheels. |
| `requirements-player.txt` | Integrated video player: python-mpv (needs libmpv from the system or from the Windows installer). |
| `requirements-dev.txt` | Lightweight dependencies used by CI/unit tests. |

## Uninstall

### Windows

Run `setup_windows.bat` (right-click → **Run as administrator**) and pick `[3] Uninstall` from the menu. Three uninstall sub-modes are offered:

| Mode | Admin required | Scope |
|------|----------------|-------|
| **[1] Full uninstall - one click** | ✅ | Removes the app folder, Public Desktop shortcut, ffmpeg from machine PATH, every user's HF model cache (Whisper/XTTS) and config (`HF token`), and all Python AI packages installed by the installer. At the end it also asks (opt-in) whether to silently uninstall **Python 3.11** and **Git for Windows** via their registry quiet-uninstall strings. |
| **[2] Current user only** | ❌ | Removes only the running user's VTAI config, HF/XTTS cache, and legacy per-user install. **Leaves the system-wide installation intact** so other Windows accounts on the PC can keep using the app. |
| **[3] Custom - granular** | ✅ for system items, ❌ for user items | Y/N prompt for each category: app folder, shortcut, machine PATH, per-user legacy installs, per-user configs/caches, then grouped Python packages (TTS, PyTorch stack, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, pipeline utilities), and finally optional Python 3.11 and Git. |

**Never removed automatically:** Visual Studio C++ Build Tools (if present from older runs). Use *Apps and features* in Windows Settings to remove them manually if desired.

### Linux / macOS

No dedicated uninstaller - remove manually:

```bash
# Python packages installed by the GUI's auto-installer
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# User data and model caches
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (themes, panel order, settings)
rm -f  ~/.videotranslatorai_config.json     # legacy config of versions <= 1.9, if present
```

## Usage

### Diagnostics

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Runs local environment diagnostics without starting translation or installing
anything. `--preflight-lipsync` treats Wav2Lip face packages as required,
which is useful before enabling **Lip Sync**. The GUI exposes the same base
check from the log panel's **Diagnostics** button. `--preflight-player` treats the integrated video player (python-mpv and a loadable libmpv) as required. `python -m videotranslator.libmpv_runtime check` probes libmpv alone (exit 0 ready, 2 unavailable).

### GUI

```bash
python video_translator_gui.py
```

**Layout:** batch translation settings live in the column on the right, as a stack of
cards: **Input**, **Translation**, **Workflow profile**, **Start**, and the
collapsible advanced sections (model, translation engine, audio, voice
cloning, lip sync, diarization, options, hotwords). The large area on the
left is the **integrated video player** (transport, playlist, A/B original vs
dubbed audio, subtitles, snapshot, fullscreen), with the **real-time
translation** bar underneath it. Drag a card by its title or by the **≡**
handle to move it up or down the column; the order is saved (`ui_panel_order`)
and restored at the next start. The log panel at the bottom can be hidden with
**Hide log**. On start the window opens centered on the current monitor (the one
under the pointer) and maximized, so it behaves well on a multi-monitor setup.

**Player controls:** icons use consistent functional colours in every theme,
independent of the selected accent colour:

| Control | Colour |
|---------|--------|
| Play | Green |
| Pause (replaces Play while playing) | Amber |
| Stop | Coral red |
| Previous / back 10 s / forward 10 s / next | Blue |
| Snapshot | Violet |
| Open folder | Gold |

Hovering adds a subtle tinted background. Unavailable controls are neutral;
playlist navigation remains usable after Stop. Tooltips and keyboard focus
indicators remain available, so colour is not the only way to identify actions.

**From local files:**
1. Click **Add** to select one or more video files
2. Choose source and target language
3. Open the **Model** section and select a Whisper model (`small` is a good balance of speed/accuracy)
4. Pick a voice and adjust TTS speed if needed
5. *(Optional)* In **Translation engine** select **Google** (default), **MarianMT** (local/offline), **DeepL Free**, or **Ollama LLM** (local, recommended for dubbing)
6. *(Optional)* Enable **Voice Cloning** (XTTS v2) and/or **Speaker Diarization**
7. *(Optional)* Enable **Lip Sync** (Wav2Lip)
8. Click **Start Translation**

**From YouTube (or any supported site):**
1. Paste one or more URLs in the **URL** field (one per line)
2. Configure language, model and voice as usual
3. Click **⬇ Download & Translate**

> yt-dlp supports YouTube, Vimeo, Twitter/X, TikTok, and [1000+ other sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Fair use notice:** Downloading videos via yt-dlp is considered automated access by platforms like YouTube and may violate their Terms of Service. Heavy or repeated use from the same IP address can result in temporary blocks (HTTP 429 / sign-in required errors). Use a VPN or rotate your IP if you encounter download failures. This tool is intended for personal, non-commercial use only. Redistribution of translated content may infringe copyright - always respect the original creator's rights.

### Real-time translation (subtitles and experimental dubbing)

Watch a local file or a resolved on-demand video link with translated subtitles
and optional spoken translation. Use the bar under the player:

**From a link:**

1. Paste a link in the **URL** field
2. Set source and target language, choose a voice and adjust the **Delay** slider
3. Select **Dubbed voice** and/or **Subtitles**
4. To hear only the translated voice, select **Mute original audio** before
   starting (in Italian: **Silenzia originale**, next to the subtitle checkbox)
5. Click **Translate in real time** - the link is resolved and translation starts

**From a loaded file:** load a video in the player (Input -> Add, then select
it), leave the URL field empty, choose the same live settings, and click
**Translate in real time**. A URL takes priority when the field is not empty.

- **Engine:** MarianMT (offline, default), Google, DeepL, or Ollama. Speech
  recognition (Whisper) runs locally. Offline models need an initial download.
- **Voice dubbing:** experimental Edge-TTS speech playback through a second mpv
  instance. It requires internet access and is separate from batch voice cloning.
- **Mute original audio:** available both before starting and during translation.
  It silences the entire original soundtrack, including music and effects, but
  leaves the translated voice audible. It does not isolate the original speaker.
  Toggle it off to restore the soundtrack; it resets when the live session ends.
  The player's speaker button is the general mute, not this independent control.
- **Pause and seek:** player controls are connected to the live session;
  end-to-end audio synchronization still needs platform-specific acceptance tests.
- **Current limits:** clip overlap/fade handling, audio timing calibration and
  Windows acceptance remain open. Growing live broadcasts are not supported yet;
  the live mode label does not imply support for ingesting a broadcast as it grows.
  See the [implementation status and remaining work](docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

For a saved dubbed video, use **Download & Translate** / **Start Translation**
instead of the real-time preview.

### Translation engine blocks and VPN

Two different blocks can happen, with different fixes:

| Block | Symptom | Fix |
|-------|---------|-----|
| **Download** (yt-dlp) | "Sign in to confirm you're not a bot", HTTP 429 | **VPN** / rotate IP, or be logged into YouTube in your browser (cookies are read automatically) |
| **Translation** (Google free endpoint) | "Google Translate could not translate... rate limited/blocked" | Use **MarianMT** (offline) or **Ollama** (local) - no rate limit. A VPN also helps. The batch flow now **falls back to MarianMT automatically** when Google is blocked. |

### Themes and appearance

Click the gear icon in the header to open **Settings**:

- **Theme**: Automatic (follows the OS dark/light mode), Graphite (default), Slate, Light, Neon.
- **Accent colour**: default per theme, or blue, teal, violet, green, amber, rose.
- **Text size**: small, normal, large, extra large.
- **Interface language**: 26 languages.

Changes apply immediately, without restarting, and are saved in the config file
(`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Restore defaults** brings
back the Graphite theme, the default accent, the normal text size and the
default order of the cards.

### Command line

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**All options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--lang-source` | Source language (`auto` for auto-detect) | `auto` |
| `--lang-target` | Target language code (e.g. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS voice name | auto |
| `--model` | Whisper model (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS speed adjustment (e.g. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian`, or `deepl` | `google` |
| `--deepl-key` | DeepL Free API key | - |
| `--diarize` | Enable speaker diarization (pyannote) | - |
| `--hf-token` | HuggingFace token for diarization | - |
| `--lipsync` | Apply Wav2Lip lip sync after dubbing | - |
| `--subs-only` | Generate `.srt` only, skip dubbing | - |
| `--no-subs` | Skip `.srt` generation | - |
| `--no-demucs` | Skip voice/music separation | - |
| `--output` / `-o` | Output file path | auto |
| `--output-dir` | Folder for translated files (one place, Windows and Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Process multiple files | - |

### Heavy Smoke Tests

The default test suite avoids real model downloads and long GPU work. To run
opt-in empirical checks for the installed local stack:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

These checks validate real Wav2Lip imports, Torch CUDA availability, Ollama
daemon availability, and faster-Whisper on synthetic speech. They intentionally
fail or skip when the local driver/daemon/model state is not ready.

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
| large-v3-turbo | 1.6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` is a distilled version of `large-v3` (4 decoder layers vs 32) - near-large quality at roughly `medium`-tier speed. Recommended default on a modern GPU when transcription speed matters; quality drop on multilingual material is minor.

> Models are downloaded automatically on first use.

## Standalone module CLIs

The modular package exposes four user-facing tools that can be invoked directly without launching the full pipeline:

```bash
# Pre-flight a video for face presence (Wav2Lip would skip if absent).
python3 -m videotranslator.face_detector path/to/video.mp4
# exit 0 = face present, exit 1 = no face

# Analyse a *_metrics.csv produced by build_dubbed_track.
# Reports P50/P75/P90/P95 of pre_stretch_ratio, audibility band breakdown,
# stretch engine usage, and the top-N worst outliers with their target text.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Sanitize text for TTS (rewrites colons, semicolons, ellipsis, dashes).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Estimate dubbing difficulty from a .srt or .json segments file BEFORE running TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Each tool has `-h`/`--help` for full options. They are self-contained and reuse the same modules the dubbing pipeline relies on, so their output stays consistent with the runtime.

## License

MIT

### Third-party components

The repository code is MIT. The installers download the components below from their own sources at install time; the project does not redistribute them.

- **libmpv** (https://github.com/mpv-player/mpv), the engine of the integrated video player. Windows: the LGPL build by zhongfly (https://github.com/zhongfly/mpv-winbuild) is tried first; a pinned GPL build by shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) is the fallback. `mpv-runtime\BUILD.txt` records the source, the licence flavour and the mpv commit, and the licence text sits next to the DLL. Linux: the distribution package (`libmpv2`, `libmpv1`, `mpv-libs` or `mpv`).
- **FFmpeg** inside libmpv (LGPL or GPL, following the libmpv build).
- **python-mpv** (`mpv` on PyPI), GPLv2+ or LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), used by the Windows installer to extract libmpv and deleted afterwards.
- **Vulkan loader** (Khronos, MIT and Apache-2.0), downloaded on Windows only when `vulkan-1.dll` is missing.
- **edge-tts** (LGPLv3), used by the dubbing pipeline.
- **MarianMT models** (Helsinki-NLP), downloaded from the Hugging Face Hub at first use under their own licences (Apache-2.0 for the `opus-mt` models, CC-BY-4.0 for `opus-mt-tc-big`).
