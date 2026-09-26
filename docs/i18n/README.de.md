# 🎬 Video Translator AI

[Englisch](../../README.md) | [Alle Übersetzungen](README.md)

**Lesen Sie diese Seite in:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

KI-gestütztes Video-Sprachsynchronisierungstool, das Videos automatisch in 26 Sprachen transkribiert, übersetzt und neu synchronisiert, mit lokalen Verarbeitungsoptionen und standardmäßig ohne API-Schlüssel. Whisper Spracherkennung läuft lokal; Edge-TTS, Google Translate und DeepL erfordern eine Internetverbindung. Für optionale Funktionen (DeepL, Identifizierung sprechender Personen (Diarisierung)) ist möglicherweise ein API-Schlüssel oder ein Zugriffstoken erforderlich.

> **v2.0** - modulares Paket, lokale Ollama-Übersetzung, Qualitätsprofil-Orchestrierung, installierbare Python-Metadaten und optionale Integrationstests mit realen Modellen. Die vollständige Liste der Änderungen finden Sie unter [GitHub-Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) und im Commit-Verlauf.

## Wie es funktioniert

1. **Transkription** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transkribiert das Audio (GPU-beschleunigt)
2. **Trennung von Stimme und Musik** - [Demucs](https://github.com/facebookresearch/demucs) isoliert Gesang von Hintergrundmusik
3. **Übersetzung** - MarianMT (lokal, offline), Google Translate, DeepL Free oder **Ollama LLM** (Qwen3, Slot-fähige prägnante Übersetzungen)
4. **Identifizierung der sprechenden Personen (Diarisierung)** *(optional)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifiziert, wer in jedem Segment spricht
5. **Sprachsynchronisation** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ Stimmen) oder [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (Stimmenklonen, für jeden Sprecher im Gespräch)
6. **Mischung** - synchronisierte Stimme, gemischt mit Original-Hintergrundmusik
7. **Normalisierung** - endgültiges Audio normalisiert auf -23 LUFS (EBU R128 Broadcast-Standard)
8. **Lippensynchronisation** *(optional)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synchronisiert Mundbewegungen mit dem synchronisierten Audio

## Funktionen

- 🖥️ Thematische GUI (Tkinter) - keine Befehlszeile erforderlich; Graphite-, Slate-, Light- und Neon-Themen, Akzentfarben, Textgröße und Einstellungsfelder, die Sie durch Ziehen neu anordnen können
- 🌍 **26 Zielsprachen** mit mehreren Stimmen pro Sprache
- 🌐 **Benutzeroberfläche in 26 Sprachen** - die Benutzeroberfläche selbst passt sich Ihrer Sprache an
- 🎬 **YouTube- und URL-Unterstützung** - Fügen Sie einen beliebigen YouTube-Link ein und übersetzen Sie ihn direkt (unterstützt von yt-dlp)
- ▶️ **Integrierter Videoplayer** (libmpv/mpv) - farbcodierte Transportsteuerung, Wiedergabeliste, A/B-Original vs. synchronisiertes Audio, Untertitel umschalten, Schnappschuss, Vollbild, Ordner öffnen
- ⏱️ **Übersetzung in Echtzeit** - Sehen Sie sich eine lokale Datei oder einen aufgelösten On-Demand-Videolink mit übersetzten Untertiteln und einem Verzögerungsregler im YouTube-Stil an; Motoren MarianMT / Google / DeepL / Ollama. Bei der experimentellen Sprachsynchronisierung werden Edge-TTS und eine zweite MPV-Instanz verwendet. Die Behandlung von Sprachüberlappungen und die Akzeptanz von echtem Audio/Windows sind noch in Arbeit. wachsende Live-Übertragungen werden noch nicht unterstützt. Siehe [Live-Implementierungsstatus](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Sprach-/Musiktrennung über Demucs (Hintergrundmusik bleibt erhalten)
- 🔇 **Originalton stumm schalten**, verfügbar vor und während der Live-Übersetzung, schaltet den Ton des Videos stumm, während die übersetzte Stimme hörbar bleibt. Schalten Sie es aus, um den Originalton wiederherzustellen. Es wird zurückgesetzt, wenn die Live-Sitzung endet.
- 🧠 **MarianMT** - vollständig lokale, offline neuronale Übersetzung (Helsinki-NLP, keine Begrenzung der Anfragerate, kein API-Schlüssel)
- 🤖 **Ollama LLM-Übersetzung** *(neu in v2.0)* - lokales LLM (Qwen3, Llama, Mistral), das Slot-fähige, prägnante Übersetzungen für natürliche Sprachsynchronisation erstellt, das Modell bei der ersten Verwendung automatisch erkennt/installiert/startet/zieht
- 🎙️ **Stimmenklonen** - Coqui XTTS v2 klont die Stimme der Person, die im Originalton spricht, in der Zielsprache (~1,8-GB-Modell), mit adaptiver Geschwindigkeit pro Segment und Multi-Seed-Wiederholungsversuchen bei Halluzinationen
- 👥 **Identifizierung von sprechenden Personen (Diarisierung)** - Pyannote-Audio 3.1 identifiziert mehrere sprechende Personen; XTTS klont jede Stimme einzeln
- 💋 **Lippensynchronisation** - Wav2Lip GAN synchronisiert Mundbewegungen mit dem synchronisierten Audio (~416-MB-Modell)
- 🔊 **Audio-Normalisierung** - automatische -23 LUFS-Lautheitsnormalisierung (EBU R128)
- ✏️ Untertitel-Editor - Überprüfen und korrigieren Sie Untertitel vor der Synchronisation
- 📦 Stapelverarbeitung - Übersetzen Sie mehrere Videos oder URLs gleichzeitig
- ⚡ GPU-Beschleunigung über CUDA (fällt automatisch auf die CPU zurück)
- 📄 Optionaler `.srt`-Untertitelexport
- 🔁 **DeepL Free** Übersetzungs-Engine (optional - 500.000 Zeichen/Monat, erfordert kostenlosen API-Schlüssel)
- 🔧 **Automatische Installation** - fehlende Python-Pakete und ffmpeg werden beim ersten Start automatisch installiert

## Unterstützte Sprachen

Arabisch, Chinesisch, Tschechisch, Dänisch, Niederländisch, Englisch, Finnisch, Französisch, Deutsch, Griechisch, Hindi, Ungarisch, Indonesisch, Italienisch, Japanisch, Koreanisch, Norwegisch, Polnisch, Portugiesisch, Rumänisch, Russisch, Spanisch, Schwedisch, Türkisch, Ukrainisch, Vietnamesisch

## Sprachkatalog

Der Edge-TTS-Sprachkatalog ist in `LANGUAGES` oben in `video_translator_gui.py` definiert. Dieses Wörterbuch ist die Quelle der Wahrheit für Zielsprachennamen, GUI-Sprachoptionsschaltflächen und die CLI-Fallback-Stimme, wenn `--voice` weggelassen wird.

Claude/Projektwartungshinweise spiegeln diesen Speicherort in `CLAUDE.md` unter **Voice Catalog Source Of Truth** wider, sodass zukünftige Code-Agenten wissen, wo Stimmen aktualisiert werden müssen und wohin die README-Datei Benutzer verweist.

## Übersetzungsmaschinen

| Motor | Einrichtung | Grenzen | Qualität |
|--------|-------|--------|---------|
| **Google Translate** *(Standard)* | Keine | Inoffizielles Scraping - kann bei großen Videos gedrosselt werden | ★★★★ |
| **MarianMT** | Keine - lädt bei der ersten Verwendung ca. 298 MB pro Sprachpaar herunter | Keine - nach dem Download vollständig offline | ★★★★ |
| **DeepL Free** | Kostenloser API-Schlüssel unter [deepl.com](https://www.deepl.com/pro-api) | 500.000 Zeichen/Monat | ★★★★★ |
| **Ollama LLM** *(empfohlen für Sprachsynchronisation - neu in Version 2.0)* | Wird bei der ersten Verwendung automatisch installiert (~1 GB Ollama + 5 GB-Modell) | Keine - vollständig lokal | ★★★★★ |

> **MarianMT** verwendet [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP)-Modelle, die nach dem ersten Download lokal zwischengespeichert werden. Erfordert eine explizite Quellsprache (automatische Erkennung wird nicht unterstützt - wählen Sie die Quellsprache manuell aus). Erforderliche Python-Pakete (`sacremoses`, `sentencepiece`) werden bei der ersten Auswahl automatisch installiert, wenn sie fehlen.

> **Ollama LLM** *(neu in v2.0)* ist die empfohlene Engine für die Sprachsynchronisation, da sie Übersetzungen unter Berücksichtigung des Zielzeitfensters erstellt. Während MarianMT wörtlich übersetzt und Italienisch/Spanisch/Französisch ca. 25 % länger als Englisch produziert (was eine hörbare Audiokomprimierung auf dem TTS erzwingt), wird der LLM aufgefordert, jedes Segment für die gesprochene Übermittlung prägnant und natürlich zu halten, wodurch ein typisches Zeichenverhältnis von 0,85-0,95 gegenüber der Quelle erreicht wird. Das Standardmodell ist `qwen3:8b` (5,2 GB auf Festplatte, ~6 GB VRAM); `qwen3:4b` (~3 GB) ist die leichte Option, `qwen3:14b` die höherwertige. Die Pipeline erkennt die Ollama-Binärdatei automatisch, installiert sie bei der ersten Verwendung automatisch über das offizielle Installationsprogramm (mit Zustimmungs-Popup), startet den Daemon und ruft das ausgewählte Modell ab - keine manuelle Einrichtung erforderlich. Wechselt automatisch zu Google Translate, wenn etwas fehlt.

## Sprachklonen (XTTS v2)

Wenn diese Option aktiviert ist, extrahiert die App die Stimme des Sprechers aus dem Originalvideo und verwendet sie als Referenz, um die Stimme in der Zielsprache zu klonen.

- Unterstützte Sprachen: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Für die restlichen 9 Sprachen wird automatisch Edge-TTS als Fallback verwendet
- Modell (~1,8 GB) wird bei der ersten Verwendung automatisch auf `~/.local/share/tts/` heruntergeladen
- **VAD-gefilterte Referenz** (v1.4): 10-15 s kontinuierliche Sprache, ausgewählt aus dem Originalaudio über [silero-vad](https://github.com/snakers4/silero-vad) für eine bessere Qualität beim Klonen von Stimmen
- **Generierungsgeschwindigkeit** konfigurierbar (`xtts_speed`, Standard `1.25`): Höhere Werte reduzieren Audiokomprimierungsartefakte nach der Verarbeitung, wenn der übersetzte Text länger als der Quellslot ist. Abstimmung über `~/.config/videotranslatorai/config.json` oder CLI `--xtts-speed`
- Läuft auf CUDA oder CPU

## Identifizierung von sprechenden Personen (Diarisierung) (pyannote-audio)

Wenn diese Option aktiviert ist, erkennt die App, wer in jedem Segment spricht. In Kombination mit Voice Cloning wird die Stimme jedes Sprechers separat geklont - ideal für Interviews, Podcasts und Videos mit mehreren Personen.

- Erfordert einen kostenlosen [HuggingFace-Token](https://huggingface.co/settings/tokens) (einmalige Registrierung)
- **Token sicher gespeichert** (v1.4) über den Betriebssystemschlüsselbund: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatische Migration vom vorherigen Klartext-JSON-Speicher
- Funktioniert nach dem ersten Download vollständig offline
- Modell: `pyannote/speaker-diarization-3.1`

## Lippensynchronisation (Wav2Lip)

Wenn diese Option aktiviert ist, wendet die App Wav2Lip GAN an, um die Mundbewegungen der Person mit dem synchronisierten Audio zu synchronisieren - die Person scheint die übersetzte Sprache zu sprechen.

- Modell (~416 MB) und Repo werden bei der ersten Verwendung automatisch nach `~/.local/share/wav2lip/` geklont
- Läuft auf CUDA (empfohlen) oder CPU
- Erhöht die Bearbeitungszeit erheblich
- Funktioniert am besten bei Videos mit einem einzelnen, deutlich sichtbaren Gesicht

## Anforderungen

- Python 3.10+ (das Windows-Installationsprogramm stellt 3.11.9 automatisch bereit)
- Windows 10/11 (x64), Linux oder macOS
- **NVIDIA-GPU dringend empfohlen** - siehe GPU-Tabelle unten
- 20 GB freier Festplattenspeicher für eine vollständige Installation (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg und alle Python-Pakete werden beim ersten Start automatisch installiert**, falls sie fehlen. Keine manuelle Einrichtung erforderlich.

**Optionale Systemabhängigkeit** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Wenn es installiert ist, wird es zur tonhöhenerhaltenden Zeitdehnung im profilgesteuerten Qualitätsband (Standard 1,15-1,50, bis zu 1,65 für harte Inhalte) verwendet, wodurch der verbleibende „Streifenhörnchen“-Effekt bei geklonten XTTS-Stimmen entfernt wird. Die Pipeline läuft ohne sie unverändert (automatischer Fallback auf ffmpeg `atempo`). Qualitätsprofile bevorzugen jetzt zusätzliche kurze Übersetzungswiederholungen gegenüber extremer Audiobeschleunigung.

### GPU-Unterstützung

Die Pipeline verwendet fünf GPU-beschleunigte Komponenten (faster-whisper, Demucs, XTTS, Wav2Lip, Pyannote). Die GPU-Abdeckung ist bei allen Anbietern nicht einheitlich:

| GPU | Windows | Linux | Notizen |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx oder neuer, CUDA 12.4-Treiber) | ✅ volle Beschleunigung | ✅ volle Beschleunigung | **Empfohlen.** Alle 5 Komponenten laufen auf der GPU. |
| **AMD** (Radeon) | ⚠️ unvollständig (DirectML unterstützt XTTS und faster-whisper nicht) | ⚠️ teilweise (ROCm funktioniert für Demucs/XTTS/pyannote, aber faster-whisper unterstützt nur CUDA) | Funktioniert, aber die Whisper-Transkription bleibt auf der CPU und dominiert die Gesamtzeit. |
| **Intel Arc** | ⚠️ unausgereifte PyTorch XPU-Unterstützung | ⚠️ das Gleiche | Nicht getestet. |
| **Keine (nur CPU)** | ✅ funktioniert | ✅ funktioniert | Erwarten Sie **10-20× langsamer** als in Echtzeit. Die Transkription eines 5-minütigen Clips mit Whisper large-v3 kann mehr als 50 Minuten dauern. |

**Empfohlener NVIDIA VRAM:**

| VRAM | Typische Grafikkarten | Erfahrung |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Verwendbar, XTTS + Wav2Lip können nicht gleichzeitig ausgeführt werden |
| 8 GB | RTX 3060 Ti, 4060 | Volle Pipeline, keine Marge |
| **12 GB+** | **RTX 3060 12 GB, 4070, 4080** | **Empfohlen - komfortabel** |
| 24 GB | RTX 3090, 4090 | Reservekapazität für große Chargen |

## Installation

### Windows

1. Klonen Sie dieses Repository oder laden Sie es herunter
2. Klicken Sie mit der rechten Maustaste auf `setup_windows.bat` → **Als Administrator ausführen** → Menü zeigt `[1] Install` an
3. Das Installationsprogramm führt automatisch Folgendes aus:
   - Installiert Python 3.11, falls nicht vorhanden (systemweit)
   - Installiert Git for Windows, falls nicht vorhanden
   - Installiert alle Python-Abhängigkeiten (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps usw.)
   - Lädt ffmpeg herunter und installiert es
   - Installiert den integrierten Videoplayer (python-mpv plus einen libmpv-Build in `mpv-runtime`). Der Schritt ist optional: Wenn er fehlschlägt, funktioniert alles andere und im Player-Bereich wird erklärt, was fehlt
   - Erstellt eine **Öffentliche Desktop-Verknüpfung** (sichtbar für jedes Windows-Konto auf dem PC)

> Das Installationsprogramm ist **mehrbenutzerfähig**: Alles wird systemweit unter `%ProgramFiles%\VideoTranslatorAI` installiert und jeder Windows-Benutzer auf dem Computer findet die Verknüpfung einsatzbereit vor. VS C++ Build Tools sind **nicht mehr erforderlich** - der gepflegte `coqui-tts`-Fork stellt vorkompilierte Python-Wheel-Pakete bereit.

### Linux / macOS

```bash
# Klonen Sie das Repo
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Optional: Installieren Sie den getesteten NVIDIA CUDA 12.4 PyTorch-Stack vorne
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Optional: Installieren Sie alle Python-Laufzeitpakete vor, anstatt die GUI zuzulassen
# Fehlende Pakete beim ersten Start installieren
pip install --break-system-packages -r requirements.txt

# Optional: der integrierte Videoplayer (libmpv aus der Distribution, python-mpv von PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Optional: Installieren Sie das Projekt als bearbeitbares Python-Paket
pip install --break-system-packages --no-deps -e .

# Starten Sie von der Quelle
python video_translator_gui.py

# Oder nach der bearbeitbaren/Paketinstallation
videotranslatorai
videotranslatorai --preflight
```

> Beim ersten Start erkennt die GUI fehlende Pakete (faster-whisper, Demucs, Edge-TTS usw.), installiert sie automatisch und streamt die Ausgabe an das Protokollfenster. ffmpeg wird auch automatisch über `apt-get` / `dnf` / `pacman` (Linux) installiert oder von GitHub (Windows) heruntergeladen.

> Die Kopfzeile zeigt ein **Spieler**-Abzeichen. Wenn libmpv oder python-mpv fehlt, wird im linken Bereich angezeigt, was fehlt, und es wird **Install Player** angeboten: Unter Linux wird der Paketmanager über pkexec (dann `sudo -n`) verwendet und der manuelle Befehl angezeigt, wenn keiner von beiden funktioniert. Unter Windows wird vor dem Herunterladen von libmpv nach dem aktuellen Benutzer gefragt (ca. 32 MB).

### Anforderungsprofile

| Datei | Zweck |
|------|---------|
| `requirements.txt` | Vollständige, abwärtskompatible Laufzeitinstallation. |
| `requirements-core.txt` | Von GUI/CLI verwendete Standard-Pipeline-Pakete. |
| `requirements-optional.txt` | XTTS, MarianMT-Tokenizer, Diarisierung, VAD, Schlüsselring. |
| `requirements-wav2lip.txt` | Wav2Lip-Laufzeit- und Gesichtserkennungsstapel (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch-Stack mit NVIDIA CUDA 12.4-Rädern getestet. |
| `requirements-player.txt` | Integrierter Videoplayer: python-mpv (benötigt libmpv vom System oder vom Windows-Installer). |
| `requirements-dev.txt` | Leichte Abhängigkeiten, die von CI/Unit-Tests verwendet werden. |

## Deinstallieren

### Windows

Führen Sie `setup_windows.bat` aus (Rechtsklick → **Als Administrator ausführen**) und wählen Sie `[3] Uninstall` aus dem Menü. Es werden drei Untermodi für die Deinstallation angeboten:

| Modus | Administrator erforderlich | Umfang |
|------|----------------|-------|
| **[1] Vollständige Deinstallation - ein Klick** | ✅ | Entfernt den App-Ordner, die öffentliche Desktop-Verknüpfung, ffmpeg aus dem Maschinenpfad, den HF-Modellcache (Whisper/XTTS) und die Konfiguration (`HF token`) jedes Benutzers sowie alle vom Installationsprogramm installierten Python AI-Pakete. Am Ende wird außerdem gefragt (Opt-In), ob **Python 3.11** und **Git for Windows** über ihre Registrierungszeichenfolgen für die stille Deinstallation stillschweigend deinstalliert werden sollen. |
| **[2] Nur aktueller Benutzer** | ❌ | Entfernt nur die VTAI-Konfiguration, den HF/XTTS-Cache und die Legacy-Installation pro Benutzer des aktuellen Benutzers. **Die systemweite Installation bleibt erhalten**, sodass andere Windows-Konten auf dem PC die App weiterhin verwenden können. |
| **[3] Benutzerdefiniert - granular** | ✅ für Systemelemente, ❌ für Benutzerelemente | J/N-Eingabeaufforderung für jede Kategorie: App-Ordner, Verknüpfung, Maschinenpfad, Legacy-Installationen pro Benutzer, Konfigurationen/Caches pro Benutzer, dann gruppierte Python-Pakete (TTS, PyTorch-Stack, Whisper+ctranslate2, Demucs, Wav2Lip-Deps, Pyannote, Pipeline-Dienstprogramme) und schließlich optionales Python 3.11 und Git. |

**Nie automatisch entfernt:** Visual Studio C++ Build Tools (falls aus älteren Ausführungen vorhanden). Verwenden Sie *Apps und Funktionen* in den Windows-Einstellungen, um sie bei Bedarf manuell zu entfernen.

### Linux / macOS

Kein spezielles Deinstallationsprogramm - manuell entfernen:

```bash
# Python-Pakete, die vom automatischen Installationsprogramm der GUI installiert werden
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Benutzerdaten- und Modell-Caches
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (Themen, Panel-Reihenfolge, Einstellungen)
rm -f  ~/.videotranslatorai_config.json     # Legacy-Konfiguration von Versionen <= 1.9, falls vorhanden
```

## Nutzung

### Diagnose

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Führt eine lokale Umgebungsdiagnose durch, ohne die Übersetzung zu starten oder etwas zu installieren. `--preflight-lipsync` behandelt Wav2Lip-Gesichtspakete nach Bedarf, was nützlich ist, bevor **Lip Sync** aktiviert wird. Die GUI stellt die gleiche Basisprüfung über die Schaltfläche **Diagnose** des Protokollfensters bereit. `--preflight-player` behandelt den integrierten Videoplayer (python-mpv und eine ladbare libmpv) nach Bedarf. `python -m videotranslator.libmpv_runtime check` prüft nur libmpv (Exit 0 bereit, 2 nicht verfügbar).

### GUI

```bash
python video_translator_gui.py
```

**Layout:** Batch-Übersetzungseinstellungen befinden sich in der rechten Spalte als Stapel von Einstellungsfeldern: **Eingabe**, **Übersetzung**, **Workflow-Profil**, **Start** und die zusammenklappbaren erweiterten Abschnitte (Modell, Übersetzungs-Engine, Audio, Stimmklonen, Lippensynchronisation, Diarisierung, Optionen, Hotwords). Der große Bereich auf der linken Seite ist der **integrierte Videoplayer** (Transport, Wiedergabeliste, A/B-Original vs. synchronisierter Ton, Untertitel, Schnappschuss, Vollbild) mit der Leiste **Echtzeitübersetzung** darunter. Ziehen Sie eine Karte an ihrem Titel oder am **≡**-Griff, um sie in der Spalte nach oben oder unten zu verschieben. Die Bestellung wird gespeichert (`ui_panel_order`) und beim nächsten Start wiederhergestellt. Das Protokollfenster unten kann mit **Protokoll ausblenden** ausgeblendet werden. Beim Start wird das Fenster zentriert auf dem aktuellen Monitor (dem unter dem Zeiger) und maximiert geöffnet, sodass es sich bei einer Konfiguration mit mehreren Monitoren gut verhält.

**Video-Video-Player-Steuerelemente:** Symbole verwenden in jedem Thema konsistente Funktionsfarben, unabhängig von der ausgewählten Akzentfarbe:

| Kontrolle | Farbe |
|---------|--------|
| Video abspielen | Grün |
| Pause (ersetzt Play während der Wiedergabe) | Bernstein |
| Stoppen Sie die Wiedergabe | Korallenrot |
| Zurück / 10 s zurück / 10 s vor / weiter | Blau |
| Schnappschuss | Violett |
| Ordner öffnen | Gold |

Durch Schweben wird ein dezent getönter Hintergrund hinzugefügt. Nicht verfügbare Steuerelemente sind neutral; Die Playlist-Navigation bleibt auch nach Stopp nutzbar. Tooltips und Tastaturfokusanzeigen bleiben verfügbar, sodass die Farbe nicht die einzige Möglichkeit ist, Aktionen zu kennzeichnen.

**Aus lokalen Dateien:**
1. Klicken Sie auf **Hinzufügen**, um eine oder mehrere Videodateien auszuwählen
2. Wählen Sie Ausgangs- und Zielsprache
3. Öffnen Sie den Abschnitt **Modell** und wählen Sie ein Whisper-Modell aus (`small` bietet ein gutes Gleichgewicht zwischen Geschwindigkeit und Genauigkeit).
4. Wählen Sie eine Stimme und passen Sie die TTS-Geschwindigkeit bei Bedarf an
5. *(Optional)* Wählen Sie in **Übersetzungs-Engine** **Google** (Standard), **MarianMT** (lokal/offline), **DeepL Free** oder **Ollama LLM** (lokal, empfohlen für Sprachsynchronisation) aus.
6. *(Optional)* Aktivieren Sie **Voice Cloning** (XTTS v2) und/oder **Identifizierung von sprechenden Personen (Diarisierung)**
7. *(Optional)* **Lippensynchronisation** aktivieren (Wav2Lip)
8. Klicken Sie auf **Übersetzung starten**

**Von YouTube (oder einer anderen unterstützten Website):**
1. Fügen Sie eine oder mehrere URLs in das Feld **URL** ein (eine pro Zeile).
2. Konfigurieren Sie Sprache, Modell und Stimme wie gewohnt
3. Klicken Sie auf **⬇ Herunterladen und übersetzen**

> yt-dlp unterstützt YouTube, Vimeo, Twitter/X, TikTok und [1000+ andere Websites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Hinweis zur fairen Nutzung:** Das Herunterladen von Videos über yt-dlp gilt als automatisierter Zugriff durch Plattformen wie YouTube und verstößt möglicherweise gegen deren Nutzungsbedingungen. Eine starke oder wiederholte Nutzung derselben IP-Adresse kann zu vorübergehenden Blockaden führen (Fehler HTTP 429/Anmeldung erforderlich). Verwenden Sie ein VPN oder wechseln Sie Ihre IP, wenn Download-Fehler auftreten. Dieses Tool ist nur für den persönlichen, nicht kommerziellen Gebrauch bestimmt. Die Weiterverbreitung übersetzter Inhalte kann gegen das Urheberrecht verstoßen - respektieren Sie stets die Rechte des ursprünglichen Erstellers.

### Echtzeitübersetzung (Untertitel und experimentelle Synchronisation)

Sehen Sie sich eine lokale Datei oder einen aufgelösten On-Demand-Videolink mit übersetzten Untertiteln und optionaler gesprochener Übersetzung an. Benutzen Sie die Leiste unter dem Player:

**Von einem Link:**

1. Fügen Sie einen Link in das Feld **URL** ein
2. Legen Sie die Quell- und Zielsprache fest, wählen Sie eine Stimme und passen Sie den Schieberegler **Verzögerung** an
3. Wählen Sie **Synchronisation** und/oder **Untertitel**
4. Um nur die übersetzte Stimme zu hören, wählen Sie vor dem Start **Originalton stummschalten** (auf Italienisch: **Silenzia originale**, neben dem Untertitel-Kontrollkästchen).
5. Klicken Sie auf **In Echtzeit übersetzen** - der Link wird aufgelöst und die Übersetzung beginnt

**Aus einer geladenen Datei:** Laden Sie ein Video in den Player (Eingabe -> Hinzufügen, dann auswählen), lassen Sie das URL-Feld leer, wählen Sie dieselben Live-Einstellungen und klicken Sie auf **In Echtzeit übersetzen**. Eine URL hat Priorität, wenn das Feld nicht leer ist.

- **Engine:** MarianMT (offline, Standard), Google, DeepL oder Ollama. Die Spracherkennung (Whisper) wird lokal ausgeführt. Offline-Modelle benötigen einen ersten Download.
- **Sprachsynchronisierung:** experimentelle Edge-TTS-Sprachwiedergabe über eine zweite MPV-Instanz. Es erfordert einen Internetzugang und ist vom Batch-Voice-Klonen getrennt.
- **Originalton stummschalten:** verfügbar sowohl vor Beginn als auch während der Übersetzung. Dadurch wird der gesamte Originalsoundtrack einschließlich Musik und Effekten stummgeschaltet, die übersetzte Stimme bleibt jedoch hörbar. Die Person, die im Originalton spricht, wird dadurch nicht isoliert. Schalten Sie es aus, um den Soundtrack wiederherzustellen. Es wird zurückgesetzt, wenn die Live-Sitzung endet. Die Lautsprechertaste des Players dient der allgemeinen Stummschaltung, nicht dieser unabhängigen Steuerung.
- **Pause und Suche:** Die Steuerelemente des Videoplayers sind mit der Live-Sitzung verbunden. Für die End-to-End-Audiosynchronisierung sind noch plattformspezifische Abnahmetests erforderlich.
- **Aktuelle Grenzen:** Clip-Überlappungs-/Fade-Handhabung, Audio-Timing-Kalibrierung und Windows-Akzeptanz bleiben offen. Zunehmende Live-Übertragungen werden noch nicht unterstützt; Die Bezeichnung „Live-Modus“ impliziert keine Unterstützung für die Aufnahme einer Übertragung, wenn sie wächst. Siehe [Implementierungsstatus und verbleibende Arbeit](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Für ein gespeichertes synchronisiertes Video verwenden Sie **Herunterladen & Übersetzen** / **Übersetzung starten** anstelle der Echtzeitvorschau.

### Übersetzungs-Engine-Blöcke und VPN

Es können zwei verschiedene Blockaden mit unterschiedlichen Korrekturen auftreten:

| Blockieren | Symptom | Beheben |
|-------|---------|-----|
| **Herunterladen** (yt-dlp) | „Melden Sie sich an, um zu bestätigen, dass Sie kein Bot sind“, HTTP 429 | **VPN** / IP wechseln oder in Ihrem Browser bei YouTube angemeldet sein (Cookies werden automatisch gelesen) |
| **Übersetzung** (kostenloser Google-Endpunkt) | „Google Translate konnte nicht übersetzen... Anforderungsrate begrenzt/blockiert“ | Verwenden Sie **MarianMT** (offline) oder **Ollama** (lokal) - keine Begrenzung der Anfragerate. Ein VPN hilft auch. Der Batch-Flow fällt jetzt **automatisch auf MarianMT zurück**, wenn Google blockiert ist. |

### Themen und Aussehen

Klicken Sie auf das Zahnradsymbol in der Kopfzeile, um **Einstellungen** zu öffnen:

- **Thema**: Automatisch (folgt dem Dunkel-/Hellmodus des Betriebssystems), Graphite (Standard), Slate, Light, Neon.
- **Akzentfarbe**: Standard pro Thema oder Blau, Blaugrün, Violett, Grün, Bernstein, Rose.
- **Textgröße**: klein, normal, groß, extra groß.
- **Schnittstellensprache**: 26 Sprachen.

Änderungen gelten sofort, ohne Neustart, und werden in der Konfigurationsdatei (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`) gespeichert. **Standardeinstellungen wiederherstellen** stellt das Graphite-Design, den Standardakzent, die normale Textgröße und die Standardreihenfolge der Einstellungsbereiche wieder her.

### Befehlszeile

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Alle Optionen:**

| CLI-Option | Beschreibung | Standard |
|------|-------------|---------|
| `--lang-source` | Quellsprache (`auto` für automatische Erkennung) | `auto` |
| `--lang-target` | Code der Zielsprache (z. B. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS-Sprachname | auto |
| `--model` | Whisper-Modell (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS-Geschwindigkeitsanpassung (z. B. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` oder `deepl` | `google` |
| `--deepl-key` | DeepL Free API-Schlüssel | - |
| `--diarize` | Ermöglichen Sie die Identifizierung sprechender Personen (Diarisierung) (pyannote) | - |
| `--hf-token` | HuggingFace-Token zur Diarisierung | - |
| `--lipsync` | Wenden Sie Wav2Lip Lip Sync nach der Synchronisation an | - |
| `--subs-only` | Generieren Sie nur `.srt`, überspringen Sie die Synchronisierung | - |
| `--no-subs` | Generation `.srt` überspringen | - |
| `--no-demucs` | Überspringen Sie die Trennung von Stimme und Musik | - |
| `--output` / `-o` | Pfad der Ausgabedatei | auto |
| `--output-dir` | Ordner für übersetzte Dateien (ein Ort, Windows und Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Mehrere Dateien verarbeiten | - |

### Integrationstests mit realen Modellen

Die Standardtestsuite vermeidet das Herunterladen echter Modelle und lange GPU-Arbeit. So führen Sie empirische Opt-in-Prüfungen für den installierten lokalen Stack durch:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Diese Prüfungen validieren echte Wav2Lip-Importe, die Verfügbarkeit von Torch CUDA, die Verfügbarkeit des Ollama-Daemons und faster-Whisper für synthetische Sprache. Sie schlagen absichtlich fehl oder überspringen, wenn der lokale Treiber-/Daemon-/Modellstatus nicht bereit ist.

**Beispiele:**

```bash
# Übersetzen Sie italienische Videos mit dem lokalen MarianMT ins Englische
# (lädt das Modell mit ca. 298 MB bei der ersten Verwendung herunter, dann vollständig offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Übersetzen mit Stimmenklonen + Identifizierung der sprechenden Personen (Diarisierung)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Übersetzen Sie mit Lippensynchronisation
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Nur Untertitel (keine Synchronisation)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper-Modelle

| Modell | Größe | Geschwindigkeit | Genauigkeit |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` ist eine destillierte Version von `large-v3` (4 Decoderschichten gegenüber 32) - nahezu große Qualität bei ungefähr der Geschwindigkeit der `medium`-Stufe. Empfohlene Standardeinstellung auf einer modernen GPU, wenn die Transkriptionsgeschwindigkeit wichtig ist; Der Qualitätsabfall bei mehrsprachigem Material ist gering.

> Modelle werden bei der ersten Verwendung automatisch heruntergeladen.

## Eigenständige Modul-CLIs

Das modulare Paket stellt vier benutzerorientierte Tools bereit, die direkt aufgerufen werden können, ohne die gesamte Pipeline zu starten:

```bash
# Führen Sie vor dem Flug ein Video zur Gesichtspräsenz durch (Wav2Lip würde bei Abwesenheit überspringen).
python3 -m videotranslator.face_detector path/to/video.mp4
# Ausgang 0 = Gesicht vorhanden, Ausgang 1 = kein Gesicht

# Analysieren Sie eine *_metrics.csv, die von build_dubbed_track erstellt wurde.
# Berichte P50/P75/P90/P95 von pre_stretch_ratio, Aufschlüsselung des Hörbereichs,
# Stretch-Engine-Nutzung und die Top-N-Ausreißer mit den schlimmsten Ausreißern mit ihrem Zieltext.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Text für TTS bereinigen (Doppelpunkte, Semikolons, Auslassungspunkte und Bindestriche werden neu geschrieben).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Schätzen Sie den Schwierigkeitsgrad der Sprachsynchronisierung anhand einer .srt- oder .json-Segmentdatei, BEVOR Sie TTS ausführen.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Jedes Werkzeug verfügt über `-h`/`--help` für vollständige Optionen. Sie sind in sich geschlossen und verwenden dieselben Module wieder, auf denen die Sprachsynchronisierungspipeline basiert, sodass ihre Ausgabe mit der Laufzeit konsistent bleibt.

## Lizenz

MIT

### Komponenten von Drittanbietern

Der Repository-Code ist MIT. Die Installationsprogramme laden die folgenden Komponenten zum Zeitpunkt der Installation von ihren eigenen Quellen herunter; Das Projekt verteilt sie nicht weiter.

- **libmpv** (https://github.com/mpv-player/mpv), die Engine des integrierten Videoplayers. Windows: Zuerst wird der LGPL-Build von zhongfly (https://github.com/zhongfly/mpv-winbuild) ausprobiert; Ein angehefteter GPL-Build von Shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) ist der Fallback. `mpv-runtime\BUILD.txt` zeichnet die Quelle, die Lizenzvariante und das MPV-Commit auf, und der Lizenztext befindet sich neben der DLL. Linux: das Distributionspaket (`libmpv2`, `libmpv1`, `mpv-libs` oder `mpv`).
- **FFmpeg** innerhalb von libmpv (LGPL oder GPL, nach dem libmpv-Build).
- **python-mpv** (`mpv` auf PyPI), GPLv2+ oder LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), wird vom Windows-Installationsprogramm zum Extrahieren von libmpv verwendet und anschließend gelöscht.
- **Vulkan-Loader** (Khronos, MIT und Apache-2.0), nur unter Windows heruntergeladen, wenn `vulkan-1.dll` fehlt.
- **edge-tts** (LGPLv3), wird von der Sprachsynchronisierungspipeline verwendet.
- **MarianMT-Modelle** (Helsinki-NLP), heruntergeladen vom Hugging Face Hub bei der ersten Verwendung unter ihren eigenen Lizenzen (Apache-2.0 für die `opus-mt`-Modelle, CC-BY-4.0 für `opus-mt-tc-big`).
