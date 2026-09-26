# 🎬 Video Translator AI

[engelsk](../../README.md) | [Alle oversættelser](README.md)

**Læs denne side i:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

AI-drevet videostemmeoverspilningsværktøj, der automatisk transskriberer, oversætter og gendubber videoer til 26 sprog, med lokale behandlingsmuligheder og ingen API-nøgler påkrævet som standard. Whisper talegenkendelse kører lokalt; Edge-TTS, Google Translate og DeepL kræver en internetforbindelse. Valgfri funktioner (DeepL, identifikation af personer, der taler (diarisering)) kan kræve en API-nøgle eller adgangstoken.

> **v2.0** - modulær pakke, lokal Ollama-oversættelse, kvalitetsprofilorkestrering, installerbare Python-metadata og opt-in-integrationstest med rigtige modeller. Se [GitHub Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) og commit-historikken for den fulde liste over ændringer.

## Hvordan det virker

1. **Transskription** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transskriberer lyden (GPU accelereret)
2. **Stemme-/musikadskillelse** - [Demucs](https://github.com/facebookresearch/demucs) isolerer vokal fra baggrundsmusik
3. **Oversættelse** - MarianMT (lokal, offline), Google Translate, DeepL Free eller **Ollama LLM** (Qwen3, slot-bevidste kortfattede oversættelser)
4. **identifikation af personer, der taler (diarisering)** *(valgfrit)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identificerer, hvem der taler i hvert segment
5. **stemmedubbing** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ stemmer) eller [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (stemmekloning, for hver højttaler i samtalen)
6. **Mixing** - dubbet stemme blandet tilbage med original baggrundsmusik
7. **Normalisering** - endelig lyd normaliseret til -23 LUFS (EBU R128 udsendelsesstandard)
8. **Lip Sync** *(valgfrit)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synkroniserer mundbevægelser med den dubbede lyd

## Funktioner

- 🖥️ Tema-GUI (Tkinter) - ingen kommandolinje nødvendig; Graphite, Slate, Light og Neon temaer, accentfarver, tekststørrelse og indstillingspaneler, du kan omarrangere ved at trække
- 🌍 **26 målsprog** med flere stemmer pr. sprog
- 🌐 **UI på 26 sprog** - selve grænsefladen tilpasser sig dit sprog
- 🎬 **YouTube- og URL-understøttelse** - indsæt ethvert YouTube-link og oversæt direkte (drevet af yt-dlp)
- ▶️ **Integreret videoafspiller** (libmpv/mpv) - farvekodede transportkontroller, afspilningsliste, A/B original vs dubbet lyd, undertekstskift, snapshot, fuldskærm, åben mappe
- ⏱️ **Oversættelse i realtid** - se en lokal fil eller et løst on-demand videolink med oversatte undertekster og en forsinkelsesskyder i YouTube-stil; motorer MarianMT / Google / DeepL / Ollama. Eksperimentel stemmedubbing bruger Edge-TTS og en anden mpv-instans. Stemmeoverlapningshåndtering og ægte lyd/Windows-accept er stadig i gang; voksende live-udsendelser understøttes ikke endnu. Se [live implementeringsstatus](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Stemme-/musikadskillelse via Demucs (beholder baggrundsmusik)
- 🔇 **Slå originallyd fra**, tilgængelig før og under liveoversættelse, dæmper videoens lydspor, mens den oversatte stemme holdes hørbar. Slå den fra for at gendanne den originale lyd; den nulstilles, når livesessionen slutter.
- 🧠 **MarianMT** - fuldt lokal, offline neural oversættelse (Helsinki-NLP, ingen grænser for anmodningshastighed, ingen API-nøgle)
- 🤖 **Ollama LLM-oversættelse** *(nyt i v2.0)* - lokal LLM (Qwen3, Llama, Mistral), der producerer slot-bevidste kortfattede oversættelser til naturlig stemmedubbing, auto-detekterer/installerer/starter/trækker model ved første brug
- 🎙️ **Stemmekloning** - Coqui XTTS v2 kloner personen, der taler med den originale lyds stemme på målsproget (~1,8 GB model), med adaptiv hastighed pr. segment og genforsøg med flere frø på hallucinationer
- 👥 **identifikation af personer, der taler (diarisering)** - Pyannote-audio 3.1 identificerer flere personer, der taler; XTTS kloner hver stemme separat
- 💋 **Lip Sync** - Wav2Lip GAN synkroniserer mundbevægelser til den dubbede lyd (~416 MB model)
- 🔊 **Lydnormalisering** - automatisk -23 LUFS loudness normalisering (EBU R128)
- ✏️ Underteksteditor - gennemgå og ret undertekster før stemmedubbing
- 📦 Batchbehandling - oversæt flere videoer eller URL'er på én gang
- ⚡ GPU-acceleration via CUDA (falder automatisk tilbage til CPU)
- 📄 Valgfri `.srt` underteksteksport
- 🔁 **DeepL Free** oversættelsesmotor (valgfrit - 500.000 tegn/måned, kræver gratis API-nøgle)
- 🔧 **Auto-installation** - manglende Python-pakker og ffmpeg installeres automatisk ved første lancering

## Understøttede sprog

Arabisk, kinesisk, tjekkisk, dansk, hollandsk, engelsk, finsk, fransk, tysk, græsk, hindi, ungarsk, indonesisk, italiensk, japansk, koreansk, norsk, polsk, portugisisk, rumænsk, russisk, spansk, svensk, tyrkisk, ukrainsk, vietnamesisk

## Stemmekatalog

Edge-TTS stemmekataloget er defineret i `LANGUAGES` nær toppen af `video_translator_gui.py`. Denne ordbog er kilden til sandheden for målsprogsnavne, GUI-stemmeradioknapper og CLI-tilbagegangsstemmen, når `--voice` er udeladt.

Claude/projekt-vedligeholdelsesnotater afspejler denne placering i `CLAUDE.md` under **Voice Catalog Source Of Truth**, så fremtidige kodeagenter ved, hvor de skal opdatere stemmer, og hvor README peger brugere.

## Oversættelsesmotorer

| Motor | Opsætning | Grænser | Kvalitet |
|--------|-------|--------|---------|
| **Google Translate** *(standard)* | Ingen | Uofficiel skrabning - kan blive droslet på store videoer | ★★★★ |
| **MarianMT** | Ingen - downloader ~298 MB pr. sprogpar ved første brug | Ingen - helt offline efter download | ★★★★ |
| **DeepL Free** | Gratis API-nøgle på [deepl.com](https://www.deepl.com/pro-api) | 500.000 tegn/måned | ★★★★★ |
| **Ollama LLM** *(anbefales til stemmedubbing - ny i v2.0)* | Automatisk installeret ved første brug (~1 GB Ollama + 5 GB model) | Ingen - helt lokalt | ★★★★★ |

> **MarianMT** bruger [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) modeller, cachelagret lokalt efter den første download. Kræver eksplicit kildesprog (auto-detektering understøttes ikke - vælg kildesprog manuelt). Nødvendige Python-pakker (`sacremoses`, `sentencepiece`) installeres automatisk ved første valg, hvis de mangler.

> **Ollama LLM** *(nyt i v2.0)* er den anbefalede motor til stemmedubbing, fordi den producerer oversættelser, der er opmærksomme på måltidsvinduet. Hvor MarianMT oversætter bogstaveligt og producerer italiensk/spansk/fransk ~25 % længere end engelsk (tvinger hørbar lydkomprimering på TTS), bliver LLM bedt om at holde hvert segment kortfattet og naturligt for talt levering, hvilket opnår et typisk char-forhold på 0,85-0,95 vs. kilde. Standardmodellen er `qwen3:8b` (5,2 GB på disk, ~6 GB VRAM); `qwen3:4b` (~3 GB) er den lette mulighed, `qwen3:14b` den højere kvalitet. Pipelinen detekterer automatisk Ollama-binæren, installerer den automatisk via det officielle installationsprogram ved første brug (med samtykke popup), starter dæmonen og trækker den valgte model - ingen manuel opsætning påkrævet. Skifter automatisk til Google Translate, hvis der mangler noget.

## Stemmekloning (XTTS v2)

Når den er aktiveret, udtrækker appen talerens stemme fra den originale video og bruger den som reference til at klone stemmen på målsproget.

- Understøttede sprog: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- For de resterende 9 sprog bruges Edge-TTS automatisk som reserve
- Model (~1,8 GB) downloades automatisk ved første brug til `~/.local/share/tts/`
- **VAD-filtreret reference** (v1.4): 10-15 s kontinuerlig tale valgt fra den originale lyd via [silero-vad](https://github.com/snakers4/silero-vad) for bedre stemmekloningskvalitet
- **Generationshastighed** konfigurerbar (`xtts_speed`, standard `1.25`): højere værdier reducerer efterbehandlingslydkomprimeringsartefakter, når den oversatte tekst er længere end kildepladsen. Tune via `~/.config/videotranslatorai/config.json` eller CLI `--xtts-speed`
- Kører på CUDA eller CPU

## identifikation af personer, der taler (diarisering) (pyannote-lyd)

Når den er aktiveret, identificerer appen, hvem der taler i hvert segment. Kombineret med stemmekloning klones hver højttalers stemme separat - ideel til interviews, podcasts og videoer med flere personer.

- Kræver et gratis [HuggingFace-token](https://huggingface.co/settings/tokens) (engangsregistrering)
- **Token opbevaret sikkert** (v1.4) via OS nøglering: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatisk migrering fra tidligere JSON-lager i almindelig tekst
- Efter den første download fungerer den fuldt offline
- Model: `pyannote/speaker-diarization-3.1`

## Lip Sync (Wav2Lip)

Når den er aktiveret, anvender appen Wav2Lip GAN til at synkronisere motivets mundbevægelser med den dubbede lyd - personen ser ud til at tale det oversatte sprog.

- Model (~416 MB) og repo klonet automatisk ved første brug til `~/.local/share/wav2lip/`
- Kører på CUDA (anbefales) eller CPU
- Øger behandlingstiden markant
- Fungerer bedst på videoer med et enkelt, klart synligt ansigt

## Krav

- Python 3.10+ (Windows-installationsprogrammet sørger automatisk for 3.11.9)
- Windows 10/11 (x64), Linux eller macOS
- **NVIDIA GPU anbefales stærkt** - se GPU-tabellen nedenfor
- 20 GB ledig diskplads til en fuld installation (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg og alle Python-pakker installeres automatisk** ved første lancering, hvis de mangler. Ingen manuel opsætning påkrævet.

**Valgfri systemafhængighed** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Når den er installeret, bruges den til tonehøjdebevarende tidsudstrækning i det profilkontrollerede kvalitetsbånd (standard 1,15-1,50, op til 1,65 for hårdt indhold), hvilket fjerner den resterende "chipmunk"-effekt på klonede XTTS-stemmer. Pipelinen kører uændret uden den (auto-fallback til ffmpeg `atempo`). Kvalitetsprofiler foretrækker nu ekstra korte oversættelsesforsøg frem for ekstrem lydhastighed.

### GPU understøttelse

Rørledningen bruger fem GPU-accelererede komponenter (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). GPU-dækning er ikke ensartet på tværs af leverandører:

| GPU | Windows | Linux | Noter |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx eller nyere, CUDA 12.4 driver) | ✅ fuld acceleration | ✅ fuld acceleration | **Anbefalet.** Alle 5 komponenter kører på GPU. |
| **AMD** (Radeon) | ⚠️ ufuldstændig (DirectML understøtter ikke XTTS og faster-whisper) | ⚠️ delvis (ROCm virker for Demucs/XTTS/pyannote, men faster-whisper understøtter kun CUDA) | Virker, men Whisper-transskription forbliver på CPU og dominerer den samlede tid. |
| **Intel Arc** | ⚠️ umoden PyTorch XPU-understøttelse | ⚠️ det samme | Ikke testet. |
| **Ingen (kun CPU)** | ✅ virker | ✅ virker | Forvent **10-20× langsommere** end i realtid. Et 5-minutters klip kan tage 50+ minutter bare at transskribere med Whisper large-v3. |

**Anbefalet NVIDIA VRAM:**

| VRAM | Typiske grafikkort | Erfaring |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Brugbar, kan ikke køre XTTS + Wav2Lip samtidigt |
| 8 GB | RTX 3060 Ti, 4060 | Fuld pipeline, ingen margin |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Anbefalet - behagelig** |
| 24 GB | RTX 3090, 4090 | Reservekapacitet til store partier |

## Installation

### Windows

1. Klon eller download dette lager
2. Højreklik på `setup_windows.bat` → **Kør som administrator** → menuen viser `[1] Install`
3. Installationsprogrammet automatisk:
   - Installerer Python 3.11, hvis den ikke er til stede (systemdækkende)
   - Installerer Git for Windows, hvis den ikke er til stede
   - Installerer alle Python-afhængigheder (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps osv.)
   - Downloader og installerer ffmpeg
   - Installerer den integrerede videoafspiller (python-mpv plus en libmpv-build i `mpv-runtime`). Trinnet er valgfrit: Hvis det mislykkes, virker alt andet, og afspillerruden forklarer, hvad der mangler
   - Opretter en **offentlig skrivebordsgenvej** (synlig for alle Windows-konti på pc'en)

> Installationsprogrammet er **multi-user**: alt er installeret på hele systemet under `%ProgramFiles%\VideoTranslatorAI`, og enhver Windows-bruger på maskinen finder genvejen klar til brug. VS C++ byggeværktøjer er **ikke længere påkrævet** - den vedligeholdte `coqui-tts` forgaffel giver prækompilerede Python-hjulpakker.

### Linux / macOS

```bash
# Klon repoen
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Valgfrit: Installer den testede NVIDIA CUDA 12.4 PyTorch-stak foran
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Valgfrit: Forinstaller alle Python runtime-pakker i stedet for at lade GUI'en
# installer manglende pakker ved første kørsel
pip install --break-system-packages -r requirements.txt

# Valgfrit: den integrerede videoafspiller (libmpv fra distributionen, python-mpv fra PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Valgfrit: Installer projektet som en redigerbar Python-pakke
pip install --break-system-packages --no-deps -e .

# Start fra kilden
python video_translator_gui.py

# Eller efter redigerbar/pakkeinstallation
videotranslatorai
videotranslatorai --preflight
```

> Ved første lancering registrerer GUI eventuelle manglende pakker (faster-whisper, Demucs, Edge-TTS osv.) og installerer dem automatisk og streamer output til logvinduet. ffmpeg installeres også automatisk via `apt-get` / `dnf` / `pacman` (Linux) eller downloades fra GitHub (Windows).

> Overskriften viser et **Player**-badge. Når libmpv eller python-mpv mangler, siger den venstre rude, hvad der mangler, og tilbyder **Installer afspiller**: på Linux bruger den pakkehåndteringen gennem pkexec (derefter `sudo -n`) og viser den manuelle kommando, når ingen af ​​dem virker; på Windows spørger den før download af libmpv for den aktuelle bruger (ca. 32 MB).

### Krav profiler

| Fil | Formål |
|------|---------|
| `requirements.txt` | Fuld, bagudkompatibel runtime-installation. |
| `requirements-core.txt` | Standard pipeline-pakker brugt af GUI/CLI. |
| `requirements-optional.txt` | XTTS, MarianMT tokenizere, diarisering, VAD, nøglering. |
| `requirements-wav2lip.txt` | Wav2Lip runtime og ansigtsgenkendelsesstak (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch stack testet med NVIDIA CUDA 12.4 hjul. |
| `requirements-player.txt` | Integreret videoafspiller: python-mpv (kræver libmpv fra systemet eller fra Windows-installationsprogrammet). |
| `requirements-dev.txt` | Letvægtsafhængigheder brugt af CI/enhedstest. |

## Afinstaller

### Windows

Kør `setup_windows.bat` (højreklik → **Kør som administrator**) og vælg `[3] Uninstall` fra menuen. Der tilbydes tre undertilstande til afinstallation:

| tilstand | Admin påkrævet | Omfang |
|------|----------------|-------|
| **[1] Fuld afinstallation - ét klik** | ✅ | Fjerner app-mappen, Public Desktop-genvejen, ffmpeg fra maskinen PATH, hver brugers HF-modelcache (Whisper/XTTS) og config (`HF token`) og alle Python AI-pakker installeret af installationsprogrammet. I slutningen spørger den også (opt-in), om de skal afinstallere **Python 3.11** og **Git for Windows** stille og roligt via deres registreringsstrenge for stille afinstallation. |
| **[2] Kun nuværende bruger** | ❌ | Fjerner kun den kørende brugers VTAI-konfiguration, HF/XTTS-cache og ældre installation pr. bruger. **Efterlader installationen for hele systemet intakt**, så andre Windows-konti på pc'en kan blive ved med at bruge appen. |
| **[3] Brugerdefineret - granulær** | ✅ for systemelementer, ❌ for brugerelementer | Y/N-spørgsmål for hver kategori: appmappe, genvej, systemets PATH, ældre installationer pr. bruger, brugerkonfigurationer og caches, derefter grupper af Python-pakker (TTS, PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip-afhængigheder, pyannote og pipelineværktøjer) og til sidst valgfri fjernelse af Python 3.11 og Git. |

**Aldrig fjernet automatisk:** Visual Studio C++ Build Tools (hvis de findes fra ældre kørsler). Brug *Apps og funktioner* i Windows-indstillinger til at fjerne dem manuelt, hvis det ønskes.

### Linux / macOS

Ingen dedikeret afinstallationsprogram - fjern manuelt:

```bash
# Python-pakker installeret af GUI's auto-installer
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Brugerdata og modelcaches
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (temaer, panelrækkefølge, indstillinger)
rm -f  ~/.videotranslatorai_config.json     # ældre konfiguration af versioner <= 1.9, hvis den findes
```

## Brug

### Diagnostik

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Kører lokalmiljødiagnostik uden at starte oversættelse eller installere noget. `--preflight-lipsync` behandler Wav2Lip ansigtspakker efter behov, hvilket er nyttigt, før du aktiverer **Lip Sync**. GUI'en afslører det samme basistjek fra logpanelets **Diagnostik**-knap. `--preflight-player` behandler den integrerede videoafspiller (python-mpv og en indlæsbar libmpv) efter behov. `python -m videotranslator.libmpv_runtime check` sonderer libmpv alene (udgang 0 klar, 2 utilgængelige).

### GUI

```bash
python video_translator_gui.py
```

**Layout:** batch-oversættelsesindstillinger findes i kolonnen til højre, som en stak af indstillingspaneler: **Input**, **Oversættelse**, **Workflow-profil**, **Start** og de sammenklappelige avancerede sektioner (model, oversættelsesmaskine, lyd, stemmekloning, læbesynkronisering, diarisering, muligheder, hotwords). Det store område til venstre er den **integrerede videoafspiller** (transport, afspilningsliste, A/B-original vs dubbet lyd, undertekster, snapshot, fuldskærm), med linjen **realtidsoversættelse** nedenunder. Træk et kort efter dets titel eller **≡**-håndtaget for at flytte det op eller ned i kolonnen; ordren gemmes (`ui_panel_order`) og gendannes ved næste start. Logpanelet i bunden kan skjules med **Skjul log**. Ved start åbnes vinduet centreret om den aktuelle skærm (den under markøren) og maksimeret, så det opfører sig godt på en multi-monitor opsætning.

**Video-videoafspillerens kontrolelementer:** ikoner bruger ensartede funktionelle farver i hvert tema, uafhængigt af den valgte accentfarve:

| Kontrol | Farve |
|---------|--------|
| Afspil video | Grøn |
| Pause (erstatter Afspil under afspilning) | Amber |
| Stop afspilning | Koralrød |
| Forrige / tilbage 10 s / frem 10 s / næste | Blå |
| Snapshot | Violet |
| Åbn mappe | Guld |

At svæve tilføjer en subtil tonet baggrund. Utilgængelige kontroller er neutrale; afspilningslistenavigation forbliver brugbar efter Stop. Værktøjstip og tastaturfokusindikatorer forbliver tilgængelige, så farve er ikke den eneste måde at identificere handlinger på.

**Fra lokale filer:**
1. Klik på **Tilføj** for at vælge en eller flere videofiler
2. Vælg kilde- og målsprog
3. Åbn sektionen **Model** og vælg en Whisper-model (`small` er en god balance mellem hastighed/nøjagtighed)
4. Vælg en stemme, og juster TTS-hastigheden, hvis det er nødvendigt
5. *(Valgfrit)* I **Oversættelsesprogrammet** skal du vælge **Google** (standard), **MarianMT** (lokalt/offline), **DeepL Free** eller **Ollama LLM** (lokalt, anbefales til stemmedubbing)
6. *(Valgfrit)* Aktiver **Stemmekloning** (XTTS v2) og/eller **identifikation af personer, der taler (diarisering)**
7. *(Valgfrit)* Aktiver **Lip Sync** (Wav2Lip)
8. Klik på **Start oversættelse**

**Fra YouTube (eller et hvilket som helst understøttet websted):**
1. Indsæt en eller flere webadresser i feltet **URL** (en pr. linje)
2. Konfigurer sprog, model og stemme som normalt
3. Klik på **⬇ Download og oversæt**

> yt-dlp understøtter YouTube, Vimeo, Twitter/X, TikTok og [1000+ andre websteder](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Bemærkning om rimelig brug:** At downloade videoer via yt-dlp betragtes som automatiseret adgang af platforme som YouTube og kan overtræde deres servicevilkår. Tung eller gentagen brug fra den samme IP-adresse kan resultere i midlertidige blokeringer (HTTP 429 / log-in påkrævet fejl). Brug en VPN eller roter din IP, hvis du støder på downloadfejl. Dette værktøj er kun beregnet til personlig, ikke-kommerciel brug. Videredistribution af oversat indhold kan krænke ophavsretten - respekter altid den oprindelige skabers rettigheder.

### Oversættelse i realtid (undertekster og eksperimentel stemmedubbing)

Se en lokal fil eller et løst on-demand videolink med oversatte undertekster og valgfri talt oversættelse. Brug bjælken under afspilleren:

**Fra et link:**

1. Indsæt et link i feltet **URL**
2. Indstil kilde- og målsprog, vælg en stemme og juster skyderen **Delay**
3. Vælg **Dubbet stemme** og/eller **Undertekster**
4. For kun at høre den oversatte stemme skal du vælge **Slå originallyd fra** før start (på italiensk: **Silenzia originale**, ud for afkrydsningsfeltet for undertekster)
5. Klik på **Oversæt i realtid** - linket er løst, og oversættelsen starter

**Fra en indlæst fil:** indlæs en video i afspilleren (Input -> Tilføj, vælg den), lad URL-feltet stå tomt, vælg de samme live-indstillinger, og klik på **Oversæt i realtid**. En URL har prioritet, når feltet ikke er tomt.

- **Motor:** MarianMT (offline, standard), Google, DeepL eller Ollama. Talegenkendelse (Whisper) kører lokalt. Offline-modeller har brug for en første download.
- **Stemmeoverspilning:** eksperimentel Edge-TTS-taleafspilning gennem en anden mpv-instans. Det kræver internetadgang og er adskilt fra batch-stemmekloning.
- **Slå originallyd fra:** tilgængelig både før start og under oversættelse. Det dæmper hele det originale soundtrack, inklusive musik og effekter, men efterlader den oversatte stemme hørbar. Det isolerer ikke den person, der taler i den originale lyd. Slå det fra for at gendanne lydsporet; den nulstilles, når livesessionen slutter. Afspillerens højttalerknap er den generelle mute, ikke denne uafhængige kontrol.
- **Pause og søg:** videoafspillerens kontroller er forbundet til livesessionen; ende-til-ende lydsynkronisering kræver stadig platformspecifikke accepttests.
- **Nuværende grænser:** håndtering af klip overlap/fade, kalibrering af lydtiming og Windows-accept forbliver åbne. Voksende live-udsendelser understøttes ikke endnu; etiketten for livetilstand indebærer ikke understøttelse af indtagelse af en udsendelse, efterhånden som den vokser. Se [implementeringsstatus og resterende arbejde](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

For en gemt dubbet video skal du bruge **Download & Oversæt** / **Start oversættelse** i stedet for forhåndsvisningen i realtid.

### Oversættelsesmotorblokke og VPN

To forskellige blokke kan ske med forskellige rettelser:

| Bloker | Symptom | Fix |
|-------|---------|-----|
| **Download** (yt-dlp) | "Log ind for at bekræfte, at du ikke er en bot", HTTP 429 | **VPN** / roter IP, eller bliv logget ind på YouTube i din browser (cookies læses automatisk) |
| **Oversættelse** (Google gratis slutpunkt) | "Google Translate kunne ikke oversætte... anmodningshastighed begrænset/blokeret" | Brug **MarianMT** (offline) eller **Ollama** (lokalt) - ingen anmodningssatsgrænse. En VPN hjælper også. Batchflowet **falder nu automatisk tilbage til MarianMT**, når Google er blokeret. |

### Temaer og udseende

Klik på tandhjulsikonet i overskriften for at åbne **Indstillinger**:

- **Tema**: Automatisk (følger OS mørk/lys-tilstand), Graphite (standard), Slate, Light, Neon.
- **Accentfarve**: standard pr. tema eller blå, blågrøn, violet, grøn, rav, rosa.
- **Tekststørrelse**: lille, normal, stor, ekstra stor.
- **Interfacesprog**: 26 sprog.

Ændringer gælder med det samme uden genstart og gemmes i konfigurationsfilen (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Gendan standardindstillinger** bringer Graphite-temaet tilbage, standardaccenten, den normale tekststørrelse og standardrækkefølgen af ​​indstillingspanelerne.

### Kommandolinje

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Alle muligheder:**

| CLI mulighed | Beskrivelse | Standard |
|------|-------------|---------|
| `--lang-source` | Kildesprog (`auto` til automatisk registrering) | `auto` |
| `--lang-target` | Målsprogskode (f.eks. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS stemmenavn | auto |
| `--model` | Whisper model (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS-hastighedsjustering (f.eks. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` eller `deepl` | `google` |
| `--deepl-key` | DeepL Free API nøgle | - |
| `--diarize` | Aktiver identifikation af personer, der taler (diarisering) (pyannote) | - |
| `--hf-token` | HuggingFace token til diarisering | - |
| `--lipsync` | Anvend Wav2Lip lip sync efter stemmedubbing | - |
| `--subs-only` | Generer kun `.srt`, spring stemmedubbing over | - |
| `--no-subs` | Spring `.srt` generation over | - |
| `--no-demucs` | Spring stemme-/musikadskillelse over | - |
| `--output` / `-o` | Output filsti | auto |
| `--output-dir` | Mappe til oversatte filer (én sted, Windows og Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Behandle flere filer | - |

### integrationstest med rigtige modeller

Standardtestpakken undgår reelle modeldownloads og langt GPU-arbejde. Sådan kører du empiriske tilvalgstjek for den installerede lokale stak:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Disse kontroller validerer ægte Wav2Lip-import, Torch CUDA tilgængelighed, Ollama daemon tilgængelighed og faster-Whisper på syntetisk tale. De fejler med vilje eller springer over, når den lokale driver/dæmon/modeltilstand ikke er klar.

**Eksempler:**

```bash
# Oversæt italiensk video til engelsk med lokale MarianMT
# (downloader ~298 MB model ved første brug, derefter helt offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Oversæt med stemmekloning + identifikation af personer, der taler (diarisering)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Oversæt med lip sync
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Kun undertekster (ingen stemmedubbing)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper modeller

| Model | Størrelse | Hastighed | Nøjagtighed |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` er en destilleret version af `large-v3` (4 dekoderlag mod 32) - næsten stor kvalitet ved nogenlunde `medium`-tierhastighed. Anbefalet standard på en moderne GPU, når transskriptionshastighed betyder noget; kvalitetsfald på flersproget materiale er mindre.

> Modeller downloades automatisk ved første brug.

## Standalone modul CLI'er

Den modulære pakke afslører fire brugervendte værktøjer, der kan påberåbes direkte uden at starte hele pipelinen:

```bash
# Pre-flight en video for ansigt tilstedeværelse (Wav2Lip ville springe over, hvis fraværende).
python3 -m videotranslator.face_detector path/to/video.mp4
# udgang 0 = ansigt til stede, udgang 1 = intet ansigt

# Analyser en *_metrics.csv produceret af build_dubbed_track.
# Rapporterer P50/P75/P90/P95 af pre_stretch_ratio, hørbarhedsbåndopdeling,
# strækmotorbrug, og top-N værste outliers med deres måltekst.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Rengør tekst til TTS (omskriver kolon, semikolon, ellipse, bindestreger).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Vurder sværhedsgraden ved stemmedubbing fra en .srt- eller .json-segmentfil, FØR TTS køres.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Hvert værktøj har `-h`/`--help` for alle muligheder. De er selvstændige og genbruger de samme moduler, som pipeline til stemmedubbing er afhængig af, så deres output forbliver i overensstemmelse med kørselstiden.

## Licens

MIT

### Tredjeparts komponenter

Depotkoden er MIT. Installatørerne downloader komponenterne nedenfor fra deres egne kilder på installationstidspunktet; projektet viderefordeler dem ikke.

- **libmpv** (https://github.com/mpv-player/mpv), motoren i den integrerede videoafspiller. Windows: LGPL bygget af zhongfly (https://github.com/zhongfly/mpv-winbuild) prøves først; en fastgjort GPL bygget af shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) er tilbagefaldet. `mpv-runtime\BUILD.txt` registrerer kilden, licensens smag og mpv-commit, og licensteksten sidder ved siden af ​​DLL'en. Linux: distributionspakken (`libmpv2`, `libmpv1`, `mpv-libs` eller `mpv`).
- **FFmpeg** inde i libmpv (LGPL eller GPL, efter libmpv build).
- **python-mpv** (`mpv` på PyPI), GPLv2+ eller LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), brugt af Windows-installationsprogrammet til at udpakke libmpv og slettet bagefter.
- **Vulkan loader** (Khronos, MIT og Apache-2.0), downloades kun på Windows, når `vulkan-1.dll` mangler.
- **edge-tts** (LGPLv3), brugt af pipeline til stemmedubbing.
- **MarianMT-modeller** (Helsinki-NLP), downloadet fra Hugging Face Hub ved første brug under deres egne licenser (Apache-2.0 for `opus-mt`-modellerne, CC-BY-4.0 for `opus-mt-tc-big`).
