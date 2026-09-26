# 🎬 Video Translator AI

[engelska](../../README.md) | [Alla översättningar](README.md)

**Läs denna sida i:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

AI-drivet videoröstdubbningsverktyg som automatiskt transkriberar, översätter och dubbar om videor till 26 språk, med lokala bearbetningsalternativ och inga API-nycklar krävs som standard. Whisper taligenkänning körs lokalt; Edge-TTS, Google Translate och DeepL kräver en internetanslutning. Valfria funktioner (DeepL, identifiering av personer som talar (diarisering)) kan kräva en API-nyckel eller åtkomsttoken.

> **v2.0** - modulpaket, lokal Ollama-översättning, kvalitetsprofilorkestrering, installerbar Python-metadata och opt-in-integreringstester med riktiga modeller. Se [GitHub Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) och commit-historiken för en fullständig lista över ändringar.

## Hur det fungerar

1. **Transkription** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transkriberar ljudet (GPU-accelererad)
2. **Separation av röst/musik** - [Demucs](https://github.com/facebookresearch/demucs) isolerar sång från bakgrundsmusik
3. **Översättning** - MarianMT (lokalt, offline), Google Translate, DeepL Free eller **Ollama LLM** (Qwen3, kortfattade översättningar med kortfattad information)
4. **identifiering av personer som talar (diarisering)** *(valfritt)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifierar vem som talar i varje segment
5. **röstdubbning** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ röster) eller [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (röstkloning, för varje talare i konversationen)
6. **Mixing** - dubbad röst blandad tillbaka med original bakgrundsmusik
7. **Normalisering** - slutligt ljud normaliserat till -23 LUFS (EBU R128 sändningsstandard)
8. **Lip Sync** *(valfritt)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synkroniserar munrörelser till det dubbade ljudet

## Funktioner

- 🖥️ GUI med tema (Tkinter) - ingen kommandorad behövs; Graphite, Slate, Light och Neon teman, accentfärger, textstorlek och inställningspaneler som du kan ordna om genom att dra
- 🌍 **26 målspråk** med flera röster per språk
- 🌐 **UI på 26 språk** - själva gränssnittet anpassar sig efter ditt språk
- 🎬 **YouTube- och URL-stöd** - klistra in valfri YouTube-länk och översätt direkt (driven av yt-dlp)
- ▶️ **Integrerad videospelare** (libmpv/mpv) - färgkodade transportkontroller, spellista, A/B-original kontra dubbat ljud, växla mellan undertexter, ögonblicksbild, helskärm, öppen mapp
- ⏱️ **Översättning i realtid** - titta på en lokal fil eller en löst videolänk på begäran med översatta undertexter och en fördröjningsreglage i YouTube-stil; motorer MarianMT / Google / DeepL / Ollama. Experimentell röstdubbning använder Edge-TTS och en andra mpv-instans. Hantering av röstöverlappning och äkta ljud/Windows-acceptans fortsätter; växande livesändningar stöds inte ännu. Se [live implementeringsstatus](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Röst-/musikseparation via Demucs (behåller bakgrundsmusik)
- 🔇 **Stäng av originalljud**, tillgängligt före och under liveöversättning, tystar videons ljudspår samtidigt som den översatta rösten hålls hörbar. Stäng av den för att återställa originalljudet; den återställs när livesessionen slutar.
- 🧠 **MarianMT** - helt lokal, offline neural översättning (Helsingfors-NLP, inga gränser för begäranden, ingen API-nyckel)
- 🤖 **Ollama LLM-översättning** *(ny i v2.0)* - lokal LLM (Qwen3, Llama, Mistral) som producerar kortfattade översättningar för naturlig röstdubbning, automatisk upptäcker/installerar/startar/drar modell vid första användning
- 🎙️ **Röstkloning** - Coqui XTTS v2 klonar personen som talar med originalljudets röst på målspråket (~1,8 GB-modell), med adaptiv hastighet per segment och flerfröförsök på hallucinationer
- 👥 **identifiering av personer som talar (diarisering)** - Pyannote-audio 3.1 identifierar flera personer som talar; XTTS klonar varje röst separat
- 💋 **Lip Sync** - Wav2Lip GAN synkroniserar munrörelser till det dubbade ljudet (~416 MB modell)
- 🔊 **Ljudnormalisering** - automatisk -23 LUFS loudness normalisering (EBU R128)
- ✏️ Undertextredigerare - granska och korrigera undertexter före röstdubbning
- 📦 Batchbearbetning - översätt flera videor eller webbadresser samtidigt
- ⚡ GPU-acceleration via CUDA (faller tillbaka till CPU automatiskt)
- 📄 Valfri `.srt` undertextexport
- 🔁 **DeepL Free** översättningsmotor (valfritt - 500 000 tecken/månad, kräver gratis API-nyckel)
- 🔧 **Auto-installation** - saknade Python-paket och ffmpeg installeras automatiskt vid första lanseringen

## Språk som stöds

Arabiska, kinesiska, danska, nederländska, engelska, finska, franska, grekiska, hindi, ungerska, indonesiska, italienska, japanska, koreanska, norska, polska, portugisiska, rumänska, ryska, spanska, svenska, turkiska, ukrainska, vietnamesiska, tyska

## Röstkatalog

Edge-TTS-röstkatalogen är definierad i `LANGUAGES` nära toppen av `video_translator_gui.py`. Den ordboken är källan till sanningen för målspråksnamn, GUI-röstradioknappar och CLI reservrösten när `--voice` utelämnas.

Claude/projekt-underhållsanteckningar speglar denna plats i `CLAUDE.md` under **Voice Catalog Source Of Truth**, så framtida kodagenter vet var de ska uppdatera röster och var README pekar användare.

## Översättningsmotorer

| Motor | Inställning | Gränser | Kvalitet |
|--------|-------|--------|---------|
| **Google Translate** *(standard)* | Inga | Inofficiell skrapning - kan strypas på stora videor | ★★★★ |
| **MarianMT** | Ingen - nedladdningar ~298 MB per språkpar vid första användningen | Ingen - helt offline efter nedladdning | ★★★★ |
| **DeepL Free** | Gratis API-nyckel på [deepl.com](https://www.deepl.com/pro-api) | 500 000 tecken/månad | ★★★★★ |
| **Ollama LLM** *(rekommenderas för röstdubbning - ny i v2.0)* | Autoinstallerad vid första användningen (~1 GB Ollama + 5 GB-modell) | Inga - helt lokalt | ★★★★★ |

> **MarianMT** använder [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) modeller, cachade lokalt efter den första nedladdningen. Kräver explicit källspråk (automatisk identifiering stöds inte - välj källspråk manuellt). Nödvändiga Python-paket (`sacremoses`, `sentencepiece`) installeras automatiskt vid första val om de saknas.

> **Ollama LLM** *(ny i v2.0)* är den rekommenderade motorn för röstdubbning eftersom den producerar översättningar som är medvetna om måltidsluckan. Där MarianMT översätter bokstavligt och producerar italienska / spanska / franska ~25 % längre än engelska (tvingar fram ljudkomprimering på TTS), uppmanas LLM att hålla varje segment kortfattat och naturligt för talad leverans, vilket uppnår ett typiskt char-förhållande på 0,85-0,95 mot källan. Standardmodellen är `qwen3:8b` (5,2 GB på disk, ~6 GB VRAM); `qwen3:4b` (~3 GB) är det lätta alternativet, `qwen3:14b` det högre kvalitet. Pipelinen upptäcker automatiskt Ollama-binären, installerar den automatiskt via den officiella installationsprogrammet vid första användningen (med samtycke popup), startar demonen och drar den valda modellen - ingen manuell installation krävs. Växlar automatiskt till Google Translate om något saknas.

## Röstkloning (XTTS v2)

När den är aktiverad extraherar appen talarens röst från originalvideon och använder den som referens för att klona rösten på målspråket.

- Språk som stöds: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- För de återstående 9 språken används Edge-TTS automatiskt som reserv
- Modell (~1,8 GB) laddas ned automatiskt vid första användningen till `~/.local/share/tts/`
- **VAD-filtrerad referens** (v1.4): 10-15 s kontinuerligt tal valt från originalljudet via [silero-vad](https://github.com/snakers4/silero-vad) för bättre röstkloningskvalitet
- **Generationshastighet** konfigurerbar (`xtts_speed`, standard `1.25`): högre värden minskar efterbehandlade ljudkomprimeringsartefakter när den översatta texten är längre än källplatsen. Ställ in via `~/.config/videotranslatorai/config.json` eller CLI `--xtts-speed`
- Körs på CUDA eller CPU

## identifiering av personer som talar (diarisering) (pyannote-audio)

När den är aktiverad identifierar appen vem som talar i varje segment. I kombination med röstkloning klonas varje talares röst separat - perfekt för intervjuer, poddsändningar och videor med flera personer.

- Kräver en gratis [HuggingFace-token](https://huggingface.co/settings/tokens) (engångsregistrering)
- **Token lagras säkert** (v1.4) via OS-nyckelringen: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatisk migrering från tidigare JSON-lagring i klartext
- Efter den första nedladdningen fungerar helt offline
- Modell: `pyannote/speaker-diarization-3.1`

## Lip Sync (Wav2Lip)

När den är aktiverad använder appen Wav2Lip GAN för att synkronisera motivets munrörelser med det dubbade ljudet - personen verkar tala det översatta språket.

- Modell (~416 MB) och repo klonas automatiskt vid första användningen till `~/.local/share/wav2lip/`
- Körs på CUDA (rekommenderas) eller CPU
- Ökar handläggningstiden avsevärt
- Fungerar bäst på videor med ett enda, tydligt synligt ansikte

## Krav

- Python 3.10+ (Windows-installationsprogrammet tillhandahåller 3.11.9 automatiskt)
- Windows 10/11 (x64), Linux eller macOS
- **NVIDIA GPU rekommenderas starkt** - se GPU-tabellen nedan
- 20 GB ledigt diskutrymme för en fullständig installation (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg och alla Python-paket installeras automatiskt** vid första lanseringen om de saknas. Ingen manuell installation krävs.

**Valfritt systemberoende** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). När den är installerad används den för tonhöjdsbevarande tidsutsträckning i det profilkontrollerade kvalitetsbandet (standard 1,15-1,50, upp till 1,65 för hårt innehåll), vilket tar bort den kvarvarande "chipmunk"-effekten på klonade XTTS-röster. Pipelinen körs oförändrad utan den (auto-backup till ffmpeg `atempo`). Kvalitetsprofiler föredrar nu extra korta översättningsförsök framför extrem ljudhastighet.

### GPU-stöd

Pipelinen använder fem GPU-accelererade komponenter (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). GPU-täckningen är inte enhetlig mellan leverantörer:

| GPU | Windows | Linux | Anteckningar |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx eller nyare, CUDA 12.4-drivrutin) | ✅ full acceleration | ✅ full acceleration | **Rekommenderas.** Alla 5 komponenter körs på GPU. |
| **AMD** (Radeon) | ⚠️ ofullständig (DirectML stöder inte XTTS och faster-whisper) | ⚠️ partiell (ROCm fungerar för Demucs/XTTS/pyannote men faster-whisper stöder bara CUDA) | Fungerar men Whisper-transkriptionen stannar på CPU och dominerar den totala tiden. |
| **Intel Arc** | ⚠️ stöd för omoget PyTorch XPU | ⚠️ samma sak | Ej testad. |
| **Ingen (endast CPU)** | ✅ fungerar | ✅ fungerar | Räkna med **10-20× långsammare** än i realtid. Ett klipp på 5 minuter kan ta mer än 50 minuter bara att transkribera med Whisper large-v3. |

**Rekommenderad NVIDIA VRAM:**

| VRAM | Vanliga grafikkort | Erfarenhet |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Användbar, kan inte köra XTTS + Wav2Lip samtidigt |
| 8 GB | RTX 3060 Ti, 4060 | Full pipeline, ingen marginal |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Rekommenderas - bekvämt** |
| 24 GB | RTX 3090, 4090 | Reservkapacitet för stora partier |

## Installation

### Windows

1. Klona eller ladda ner det här förrådet
2. Högerklicka `setup_windows.bat` → **Kör som administratör** → menyn visar `[1] Install`
3. Installationsprogrammet automatiskt:
   - Installerar Python 3.11 om det inte finns (systemomfattande)
   - Installerar Git for Windows om den inte finns
   - Installerar alla Python-beroenden (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps, etc.)
   - Laddar ner och installerar ffmpeg
   - Installerar den integrerade videospelaren (python-mpv plus en libmpv-build i `mpv-runtime`). Steget är valfritt: om det misslyckas fungerar allt annat och spelarrutan förklarar vad som saknas
   - Skapar en **genväg för offentligt skrivbord** (synlig för alla Windows-konton på datorn)

> Installationsprogrammet är **multi-användare**: allt är installerat i hela systemet under `%ProgramFiles%\VideoTranslatorAI` och alla Windows-användare på maskinen hittar genvägen redo att gå. VS C++ byggverktyg krävs **inte längre** - den underhållna `coqui-tts`-gaffeln tillhandahåller förkompilerade Python-hjulpaket.

### Linux/macOS

```bash
# Klona repet
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Valfritt: installera den testade NVIDIA CUDA 12.4 PyTorch-stacken framtill
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Valfritt: förinstallera alla Python runtime-paket istället för att låta det grafiska gränssnittet
# installera saknade paket vid första körningen
pip install --break-system-packages -r requirements.txt

# Valfritt: den integrerade videospelaren (libmpv från distributionen, python-mpv från PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Valfritt: installera projektet som ett redigerbart Python-paket
pip install --break-system-packages --no-deps -e .

# Starta från källan
python video_translator_gui.py

# Eller efter redigerbar/paketinstallation
videotranslatorai
videotranslatorai --preflight
```

> Vid första start upptäcker det grafiska användargränssnittet alla saknade paket (faster-whisper, Demucs, Edge-TTS, etc.) och installerar dem automatiskt och strömmar utdata till loggfönstret. ffmpeg installeras också automatiskt via `apt-get` / `dnf` / `pacman` (Linux) eller laddas ner från GitHub (Windows).

> Rubriken visar ett **Spelare**-märke. När libmpv eller python-mpv saknas, säger den vänstra rutan vad som saknas och erbjuder **Installera spelare**: på Linux använder den pakethanteraren genom pkexec (då `sudo -n`) och visar det manuella kommandot när inget av dem fungerar; på Windows frågar den innan libmpv laddas ner för den aktuella användaren (cirka 32 MB).

### Kravprofiler

| Arkiv | Syfte |
|------|---------|
| `requirements.txt` | Fullständig, bakåtkompatibel körtidsinstallation. |
| `requirements-core.txt` | Standardpipeline-paket som används av GUI/CLI. |
| `requirements-optional.txt` | XTTS, MarianMT tokenizers, diarisering, VAD, nyckelring. |
| `requirements-wav2lip.txt` | Wav2Lip körtid och stack för ansiktsdetektering (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch stack testad med NVIDIA CUDA 12.4 hjul. |
| `requirements-player.txt` | Integrerad videospelare: python-mpv (behöver libmpv från systemet eller från Windows-installationsprogrammet). |
| `requirements-dev.txt` | Lättviktsberoenden som används av CI/enhetstester. |

## Avinstallera

### Windows

Kör `setup_windows.bat` (högerklicka → **Kör som administratör**) och välj `[3] Uninstall` från menyn. Tre avinstallationsunderlägen erbjuds:

| Läge | Admin krävs | Omfattning |
|------|----------------|-------|
| **[1] Fullständig avinstallation - ett klick** | ✅ | Tar bort app-mappen, Public Desktop-genväg, ffmpeg från maskinen PATH, varje användares HF-modellcache (Whisper/XTTS) och config (`HF token`) och alla Python AI-paket installerade av installationsprogrammet. I slutet frågar den också (opt-in) om de ska avinstallera **Python 3.11** och **Git for Windows** tyst via deras registersträngar för tyst avinstallation. |
| **[2] Endast nuvarande användare** | ❌ | Tar endast bort den körande användarens VTAI-konfiguration, HF/XTTS-cache och äldre installation per användare. **Lämnar den systemomfattande installationen intakt** så att andra Windows-konton på datorn kan fortsätta använda appen. |
| **[3] Anpassad - granulär** | ✅ för systemobjekt, ❌ för användarobjekt | Y/N-fråga för varje kategori: appmapp, genväg, systemets PATH, äldre installationer per användare, användarkonfigurationer och cacheminnen, därefter grupper av Python-paket (TTS, PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip-beroenden, pyannote och verktyg för bearbetningskedjan) och till sist valfri avinstallation av Python 3.11 och Git. |

**Aldrig borttagen automatiskt:** Visual Studio C++ Build Tools (om de finns från äldre körningar). Använd *Appar och funktioner* i Windows-inställningarna för att ta bort dem manuellt om så önskas.

### Linux/macOS

Inget dedikerat avinstallationsprogram - ta bort manuellt:

```bash
# Python-paket installerade av det grafiska användargränssnittets autoinstallerare
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Användardata och modellcacher
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (teman, panelordning, inställningar)
rm -f  ~/.videotranslatorai_config.json     # äldre konfiguration av versioner <= 1.9, om sådan finns
```

## Användning

### Diagnostik

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Kör lokal miljödiagnostik utan att starta översättning eller installera något. `--preflight-lipsync` behandlar Wav2Lip ansiktspaket efter behov, vilket är användbart innan du aktiverar **Lip Sync**. GUI exponerar samma baskontroll från loggpanelens **Diagnostik**-knapp. `--preflight-player` behandlar den integrerade videospelaren (python-mpv och en laddningsbar libmpv) efter behov. `python -m videotranslator.libmpv_runtime check` sonderar enbart libmpv (utgång 0 klar, 2 otillgängliga).

### GUI

```bash
python video_translator_gui.py
```

**Layout:** inställningar för batchöversättning finns i kolumnen till höger, som en bunt med inställningspaneler: **Indata**, **Översättning**, **Arbetsflödesprofil**, **Start** och de hopfällbara avancerade sektionerna (modell, översättningsmotor, ljud, röstkloning, läppsynkronisering, diarisering, alternativ, hotwords). Det stora området till vänster är den **integrerade videospelaren** (transport, spellista, A/B-original vs dubbat ljud, undertexter, ögonblicksbild, helskärm), med fältet **realtidsöversättning** under den. Dra ett kort efter dess titel eller **≡**-handtaget för att flytta det uppåt eller nedåt i kolumnen; ordern sparas (`ui_panel_order`) och återställs vid nästa start. Loggpanelen längst ner kan döljas med **Göm logg**. Vid start öppnas fönstret centrerat på den aktuella monitorn (den under pekaren) och maximerat, så det fungerar bra på en multi-monitor setup.

**Videospelarens kontroller:** ikoner använder konsekventa funktionella färger i varje tema, oberoende av den valda accentfärgen:

| Kontroll | Färg |
|---------|--------|
| Spela upp video | Grönt |
| Pausa (ersätter Spela medan du spelar) | Amber |
| Stoppa uppspelningen | Korallröd |
| Föregående / bakåt 10 s / framåt 10 s / nästa | Blå |
| Ögonblicksbild | Violett |
| Öppna mappen | Guld |

Att sväva lägger till en subtil tonad bakgrund. Ej tillgängliga kontroller är neutrala; navigering i spellistan förblir användbar efter stopp. Verktygstips och tangentbordsfokusindikatorer förblir tillgängliga, så färg är inte det enda sättet att identifiera åtgärder.

**Från lokala filer:**
1. Klicka på **Lägg till** för att välja en eller flera videofiler
2. Välj käll- och målspråk
3. Öppna avsnittet **Modell** och välj en Whisper-modell (`small` är en bra balans mellan hastighet och noggrannhet)
4. Välj en röst och justera TTS-hastigheten om det behövs
5. *(Valfritt)* I **Översättningsmotorn** väljer du **Google** (standard), **MarianMT** (lokalt/offline), **DeepL Free** eller **Ollama LLM** (lokalt, rekommenderas för röstdubbning)
6. *(Valfritt)* Aktivera **Röstkloning** (XTTS v2) och/eller **identifiering av personer som talar (diarisering)**
7. *(Valfritt)* Aktivera **Lip Sync** (Wav2Lip)
8. Klicka på **Starta översättning**

**Från YouTube (eller någon annan webbplats som stöds):**
1. Klistra in en eller flera webbadresser i fältet **URL** (en per rad)
2. Konfigurera språk, modell och röst som vanligt
3. Klicka på **⬇ Ladda ner och översätt**

> yt-dlp stöder YouTube, Vimeo, Twitter/X, TikTok och [1000+ andra webbplatser](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Meddelande om skälig användning:** Nedladdning av videor via yt-dlp anses vara automatisk åtkomst av plattformar som YouTube och kan bryta mot deras användarvillkor. Tung eller upprepad användning från samma IP-adress kan resultera i tillfälliga blockeringar (HTTP 429 / inloggningsfel). Använd en VPN eller rotera din IP om du stöter på nedladdningsfel. Detta verktyg är endast avsett för personligt, icke-kommersiellt bruk. Omdistribution av översatt innehåll kan göra intrång i upphovsrätten - respektera alltid den ursprungliga skaparens rättigheter.

### Realtidsöversättning (undertexter och experimentell röstdubbning)

Titta på en lokal fil eller en löst videolänk på begäran med översatta undertexter och valfri talad översättning. Använd fältet under spelaren:

**Från en länk:**

1. Klistra in en länk i fältet **URL**
2. Ställ in käll- och målspråk, välj en röst och justera skjutreglaget **Delay**
3. Välj **Dubbad röst** och/eller **Undertexter**
4. För att bara höra den översatta rösten, välj **Stäng av originalljud** innan du startar (på italienska: **Silenzia originale**, bredvid kryssrutan under textning)
5. Klicka på **Översätt i realtid** - länken är löst och översättningen startar

**Från en laddad fil:** ladda en video i spelaren (Inmatning -> Lägg till, välj den), lämna URL-fältet tomt, välj samma liveinställningar och klicka på **Översätt i realtid**. En URL har prioritet när fältet inte är tomt.

- **Motor:** MarianMT (offline, standard), Google, DeepL eller Ollama. Taligenkänning (Whisper) körs lokalt. Offlinemodeller behöver en första nedladdning.
- **Röstdubbning:** experimentell Edge-TTS-taluppspelning genom en andra mpv-instans. Det kräver internetåtkomst och är separat från batch-röstkloning.
- **Stäng av originalljud:** tillgängligt både före start och under översättning. Den tystar hela originalsoundtracket, inklusive musik och effekter, men låter den översatta rösten höras. Det isolerar inte personen som talar i originalljudet. Stäng av den för att återställa ljudspåret; den återställs när livesessionen slutar. Spelarens högtalarknapp är den allmänna tysta kontrollen, inte denna oberoende kontroll.
- **Paus och sök:** videospelarens kontroller är anslutna till livesessionen; end-to-end ljudsynkronisering kräver fortfarande plattformsspecifika acceptanstest.
- **Nuvarande gränser:** hantering av klippöverlappning/tonning, kalibrering av ljudtiming och Windows-acceptans förblir öppna. Växande livesändningar stöds inte ännu; etiketten för liveläge innebär inte stöd för att ta in en sändning när den växer. Se [implementeringsstatus och återstående arbete](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

För en sparad dubbad video, använd **Ladda ner och översätt** / **Starta översättning** istället för förhandsgranskningen i realtid.

### Översättningsmotorblock och VPN

Två olika block kan hända, med olika korrigeringar:

| Block | Symptom | Fixa |
|-------|---------|-----|
| **Ladda ned** (yt-dlp) | "Logga in för att bekräfta att du inte är en bot", HTTP 429 | **VPN** / rotera IP, eller logga in på YouTube i din webbläsare (cookies läses automatiskt) |
| **Översättning** (Googles kostnadsfria slutpunkt) | "Google Translate kunde inte översätta... förfrågningsfrekvens begränsad/blockerad" | Använd **MarianMT** (offline) eller **Ollama** (lokalt) - ingen gräns för begäranden. En VPN hjälper också. Batchflödet **faller nu tillbaka till MarianMT automatiskt** när Google blockeras. |

### Teman och utseende

Klicka på kugghjulsikonen i rubriken för att öppna **Inställningar**:

- **Tema**: Automatisk (följer operativsystemets mörka/ljusläge), Graphite (standard), Slate, Light, Neon.
- **Accentfärg**: standard per tema, eller blå, kricka, violett, grön, bärnsten, ros.
- **Textstorlek**: liten, normal, stor, extra stor.
- **Gränssnittsspråk**: 26 språk.

Ändringar gäller omedelbart, utan att starta om, och sparas i konfigurationsfilen (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Återställ standardvärden** tar tillbaka Graphite-temat, standardaccenten, normal textstorlek och standardordningen för inställningspanelerna.

### Kommandorad

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Alla alternativ:**

| CLI-alternativ | Beskrivning | Standard |
|------|-------------|---------|
| `--lang-source` | Källspråk (`auto` för automatisk identifiering) | `auto` |
| `--lang-target` | Målspråkskod (t.ex. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS röstnamn | auto |
| `--model` | Whisper-modell (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS-hastighetsjustering (t.ex. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` eller `deepl` | `google` |
| `--deepl-key` | DeepL Free API-nyckel | - |
| `--diarize` | Aktivera identifiering av personer som talar (diarisering) (pyannote) | - |
| `--hf-token` | HuggingFace token för diarisering | - |
| `--lipsync` | Applicera Wav2Lip läppsynk efter röstdubbning | - |
| `--subs-only` | Generera endast `.srt`, hoppa över röstdubbning | - |
| `--no-subs` | Hoppa över `.srt`-generationen | - |
| `--no-demucs` | Hoppa över röst-/musikseparation | - |
| `--output` / `-o` | Utdatafilens sökväg | auto |
| `--output-dir` | Mapp för översatta filer (ett ställe, Windows och Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Bearbeta flera filer | - |

### integrationstester med riktiga modeller

Standardtestsviten undviker nedladdningar av riktiga modeller och långt GPU-arbete. Så här kör du opt-in empiriska kontroller för den installerade lokala stacken:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Dessa kontroller validerar riktiga Wav2Lip-importer, Torch CUDA-tillgänglighet, Ollama-demontillgänglighet och faster-Whisper på syntetiskt tal. De misslyckas avsiktligt eller hoppar över när den lokala föraren/demonen/modellen inte är redo.

**Exempel:**

```bash
# Översätt italiensk video till engelska med lokala MarianMT
# (laddar ner ~298 MB-modell vid första användningen, sedan helt offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Översätt med röstkloning + identifiering av personer som talar (diarisering)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Översätt med läppsynk
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Endast undertexter (ingen röstdubbning)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper-modeller

| Modell | Storlek | Hastighet | Noggrannhet |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` är en destillerad version av `large-v3` (4 avkodarlager mot 32) - nästan hög kvalitet vid ungefär `medium`-nivåhastighet. Rekommenderad standard på en modern GPU när transkriptionshastigheten spelar roll; Kvalitetsminskningen på flerspråkigt material är liten.

> Modeller laddas ner automatiskt vid första användningen.

## Fristående modul CLI

Det modulära paketet exponerar fyra användarvända verktyg som kan anropas direkt utan att starta hela pipelinen:

```bash
# Pre-flight en video för ansiktsnärvaro (Wav2Lip skulle hoppa över om den saknas).
python3 -m videotranslator.face_detector path/to/video.mp4
# utgång 0 = ansikte närvarande, utgång 1 = inget ansikte

# Analysera en *_metrics.csv producerad av build_dubbed_track.
# Rapporter P50/P75/P90/P95 av pre_stretch_ratio, hörbarhetsbanduppdelning,
# sträckmotoranvändning och de sämsta avvikelserna i topp-N med sin måltext.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Rensa text för TTS (skriver om kolon, semikolon, ellips, streck).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Beräkna röstdubbningssvårigheter från en .srt- eller .json-segmentfil INNAN du kör TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Varje verktyg har `-h`/`--help` för kompletta alternativ. De är fristående och återanvänder samma moduler som pipelinen för röstdubbning är beroende av, så deras utdata förblir konsekventa med körtiden.

## Licens

MIT

### Komponenter från tredje part

Förvarskoden är MIT. Installatörerna laddar ner komponenterna nedan från sina egna källor vid installationen; projektet omfördelar dem inte.

- **libmpv** (https://github.com/mpv-player/mpv), motorn för den integrerade videospelaren. Windows: LGPL byggd av zhongfly (https://github.com/zhongfly/mpv-winbuild) testas först; en stiftad GPL byggd av shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) är en reserv. `mpv-runtime\BUILD.txt` registrerar källan, licensens smak och mpv-commit, och licenstexten sitter bredvid DLL-filen. Linux: distributionspaketet (`libmpv2`, `libmpv1`, `mpv-libs` eller `mpv`).
- **FFmpeg** inuti libmpv (LGPL eller GPL, efter libmpv-bygget).
- **python-mpv** (`mpv` på PyPI), GPLv2+ eller LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), används av Windows-installationsprogrammet för att extrahera libmpv och raderas efteråt.
- **Vulkan loader** (Khronos, MIT och Apache-2.0), laddas ner på Windows endast när `vulkan-1.dll` saknas.
- **edge-tts** (LGPLv3), används av pipeline för röstdubbning.
- **MarianMT-modeller** (Helsingfors-NLP), nedladdade från Hugging Face Hub vid första användningen under sina egna licenser (Apache-2.0 för `opus-mt`-modellerna, CC-BY-4.0 för `opus-mt-tc-big`).
