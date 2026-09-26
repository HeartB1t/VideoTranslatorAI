# 🎬 Video Translator AI

[Engels](../../README.md) | [Alle vertalingen](README.md)

**Lees deze pagina in:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Door AI aangedreven tool voor het nasynchroniseren van video's die video's automatisch transcribeert, vertaalt en opnieuw kopieert in 26 talen, met lokale verwerkingsopties en standaard geen API-sleutels vereist. Whisper spraakherkenning draait lokaal; Edge-TTS, Google Translate en DeepL vereisen een internetverbinding. Voor optionele functies (DeepL, identificatie van sprekende mensen (diarisering)) is mogelijk een API-sleutel of toegangstoken vereist.

> **v2.0** - modulair pakket, lokale Ollama-vertaling, orkestratie van kwaliteitsprofielen, installeerbare Python-metagegevens en opt-in-integratietests met echte modellen. Zie [GitHub Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) en de commitgeschiedenis voor de volledige lijst met wijzigingen.

## Hoe het werkt

1. **Transcriptie** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcribeert de audio (GPU-versneld)
2. **Stem/muziekscheiding** - [Demucs](https://github.com/facebookresearch/demucs) isoleert zang van achtergrondmuziek
3. **Vertaling** - MarianMT (lokaal, offline), Google Translate, DeepL Free of **Ollama LLM** (Qwen3, slotbewuste beknopte vertalingen)
4. **identificatie van mensen die spreken (diariseren)** *(optioneel)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identificeert wie er in elk segment spreekt
5. **stemnasynchronisatie** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ stemmen) of [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (stemklonen, voor elke spreker in het gesprek)
6. **Mixen** - nagesynchroniseerde stem teruggemixt met originele achtergrondmuziek
7. **Normalisatie** - uiteindelijke audio genormaliseerd naar -23 LUFS (EBU R128 uitzendstandaard)
8. **Lip Sync** *(optioneel)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synchroniseert mondbewegingen met de nagesynchroniseerde audio

## Kenmerken

- 🖥️ Thematische GUI (Tkinter) - geen opdrachtregel nodig; Graphite, Slate, Light en Neon thema's, accentkleuren, tekstgrootte en instellingenpanelen die u kunt herschikken door te slepen
- 🌍 **26 doeltalen** met meerdere stemmen per taal
- 🌐 **UI in 26 talen** - de interface past zich aan uw taal aan
- 🎬 **YouTube- en URL-ondersteuning** - plak een YouTube-link en vertaal deze direct (mogelijk gemaakt door yt-dlp)
- ▶️ **Geïntegreerde videospeler** (libmpv/mpv) - kleurgecodeerde transportbedieningen, afspeellijst, A/B origineel versus nagesynchroniseerde audio, ondertitels schakelen, momentopname, volledig scherm, map openen
- ⏱️ **Realtime vertaling** - bekijk een lokaal bestand of een opgeloste on-demand videolink met vertaalde ondertitels en een vertragingsschuifregelaar in YouTube-stijl; motoren MarianMT / Google / DeepL / Ollama. Experimentele voice-nasynchronisatie maakt gebruik van Edge-TTS en een tweede mpv-instantie. De afhandeling van spraakoverlappingen en de acceptatie van echte audio/Windows blijven aan de gang; groeiende live-uitzendingen worden nog niet ondersteund. Zie de [live-implementatiestatus](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Stem-/muziekscheiding via Demucs (behoudt achtergrondmuziek)
- 🔇 **Originele audio dempen**, beschikbaar voor en tijdens live vertaling, dempt de soundtrack van de video terwijl de vertaalde stem hoorbaar blijft. Schakel het uit om de originele audio te herstellen; het wordt gereset wanneer de livesessie eindigt.
- 🧠 **MarianMT** - volledig lokale, offline neurale vertaling (Helsinki-NLP, geen limieten voor verzoeksnelheid, geen API-sleutel)
- 🤖 **Ollama LLM-vertaling** *(nieuw in v2.0)* - lokale LLM (Qwen3, Llama, Mistral) produceert slotbewuste, beknopte vertalingen voor natuurlijke stemnasynchronisatie, detecteert/installeert/start/haalt model automatisch bij eerste gebruik
- 🎙️ **Stemklonen** - Coqui XTTS v2 kloont de persoon die in de originele audiostem spreekt in de doeltaal (~1,8 GB-model), met adaptieve snelheid per segment en herhaalde pogingen bij hallucinaties
- 👥 **identificatie van sprekende mensen (diarisatie)** - pyannote-audio 3.1 identificeert meerdere sprekende mensen; XTTS kloont elke stem afzonderlijk
- 💋 **Lip Sync** - Wav2Lip GAN synchroniseert mondbewegingen met de nagesynchroniseerde audio (~416 MB model)
- 🔊 **Audionormalisatie** - automatisch -23 LUFS luidheidsnormalisatie (EBU R128)
- ✏️ Ondertiteleditor - bekijk en corrigeer ondertitels vóór het nasynchroniseren van stemmen
- 📦 Batchverwerking - vertaal meerdere video's of URL's tegelijk
- ⚡ GPU-versnelling via CUDA (valt automatisch terug naar CPU)
- 📄 Optionele `.srt` ondertitelexport
- 🔁 **DeepL Free** vertaalengine (optioneel - 500.000 tekens/maand, vereist gratis API-sleutel)
- 🔧 **Auto-installatie** - ontbrekende Python-pakketten en ffmpeg worden automatisch geïnstalleerd bij de eerste keer opstarten

## Ondersteunde talen

Arabisch, Chinees, Tsjechisch, Deens, Nederlands, Engels, Fins, Frans, Duits, Grieks, Hindi, Hongaars, Indonesisch, Italiaans, Japans, Koreaans, Noors, Pools, Portugees, Roemeens, Russisch, Spaans, Zweeds, Turks, Oekraïens, Vietnamees

## Stemcatalogus

De Edge-TTS-spraakcatalogus is gedefinieerd in `LANGUAGES` bovenaan `video_translator_gui.py`. Dat woordenboek is de bron van waarheid voor doeltaalnamen, GUI-stemkeuzerondjes en de CLI-fallback-stem wanneer `--voice` wordt weggelaten.

Claude/projectonderhoudsnotities weerspiegelen deze locatie in `CLAUDE.md` onder **Voice Catalog Source Of Truth**, zodat toekomstige codeagenten weten waar ze stemmen moeten bijwerken en waar de README gebruikers naar verwijst.

## Vertaalmachines

| Motor | Installatie | Grenzen | Kwaliteit |
|--------|-------|--------|---------|
| **Google Translate** *(standaard)* | Geen | Onofficieel schrapen: kan worden beperkt bij grote video's | ★★★★ |
| **MarianMT** | Geen - downloadt ~298 MB per talenpaar bij het eerste gebruik | Geen - volledig offline na download | ★★★★ |
| **DeepL Free** | Gratis API-sleutel op [deepl.com](https://www.deepl.com/pro-api) | 500.000 tekens/maand | ★★★★★ |
| **Ollama LLM** *(aanbevolen voor stemnasynchronisatie - nieuw in v2.0)* | Automatisch geïnstalleerd bij eerste gebruik (~1 GB Ollama + 5 GB-model) | Geen - volledig lokaal | ★★★★★ |

> **MarianMT** gebruikt [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) modellen, lokaal in de cache opgeslagen na de eerste download. Vereist expliciete brontaal (automatische detectie niet ondersteund - selecteer de brontaal handmatig). Vereiste Python-pakketten (`sacremoses`, `sentencepiece`) worden automatisch geïnstalleerd bij de eerste selectie als ze ontbreken.

> **Ollama LLM** *(nieuw in v2.0)* is de aanbevolen engine voor voice dubbing omdat deze vertalingen produceert die rekening houden met het beoogde tijdslot. Waar MarianMT letterlijk vertaalt en Italiaans/Spaans/Frans ~25% langer produceert dan Engels (waardoor hoorbare audiocompressie op de TTS wordt geforceerd), wordt de LLM gevraagd om elk segment beknopt en natuurlijk te houden voor gesproken weergave, waardoor een typische tekenverhouding van 0,85-0,95 ten opzichte van de bron wordt bereikt. Het standaardmodel is `qwen3:8b` (5,2 GB op schijf, ~6 GB VRAM); `qwen3:4b` (~3 GB) is de lichtgewicht optie, `qwen3:14b` de hogere kwaliteit. De pijplijn detecteert automatisch het Ollama-binaire bestand, installeert het automatisch via het officiële installatieprogramma bij het eerste gebruik (met toestemmingspop-up), start de daemon en haalt het gekozen model op - geen handmatige installatie vereist. Schakelt automatisch over naar Google Translate als er iets ontbreekt.

## Spraakklonen (XTTS v2)

Indien ingeschakeld, haalt de app de stem van de spreker uit de originele video en gebruikt deze als referentie om de stem in de doeltaal te klonen.

- Ondersteunde talen: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Voor de overige 9 talen wordt Edge-TTS automatisch als fallback gebruikt
- Model (~1,8 GB) wordt bij het eerste gebruik automatisch gedownload naar `~/.local/share/tts/`
- **VAD-gefilterde referentie** (v1.4): 10-15 s continue spraak geselecteerd uit de originele audio via [silero-vad](https://github.com/snakers4/silero-vad) voor een betere kwaliteit van stemklonen
- **Generatiesnelheid** configureerbaar (`xtts_speed`, standaard `1.25`): hogere waarden verminderen artefacten bij nabewerking van audiocompressie wanneer de vertaalde tekst langer is dan de bronsleuf. Afstemmen via `~/.config/videotranslatorai/config.json` of CLI `--xtts-speed`
- Draait op CUDA of CPU

## identificatie van sprekende mensen (diariseren) (pyannote-audio)

Indien ingeschakeld, identificeert de app wie er in elk segment spreekt. In combinatie met Voice Cloning wordt de stem van elke spreker afzonderlijk gekloond - ideaal voor interviews, podcasts en video's met meerdere personen.

- Vereist een gratis [HuggingFace-token](https://huggingface.co/settings/tokens) (eenmalige registratie)
- **Token veilig opgeslagen** (v1.4) via de sleutelhanger van het besturingssysteem: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatische migratie van eerdere JSON-opslag in platte tekst
- Werkt na de eerste download volledig offline
- Model: `pyannote/speaker-diarization-3.1`

## Lipsynchronisatie (Wav2Lip)

Indien ingeschakeld, past de app Wav2Lip GAN toe om de mondbewegingen van het onderwerp te synchroniseren met de nagesynchroniseerde audio - het lijkt erop dat de persoon de vertaalde taal spreekt.

- Model (~416 MB) en opslagplaats automatisch gekloond bij eerste gebruik naar `~/.local/share/wav2lip/`
- Draait op CUDA (aanbevolen) of CPU
- Verhoogt de verwerkingstijd aanzienlijk
- Werkt het beste bij video's met één duidelijk zichtbaar gezicht

## Vereisten

- Python 3.10+ (het Windows-installatieprogramma voorziet automatisch in 3.11.9)
- Windows 10/11 (x64), Linux of macOS
- **NVIDIA GPU sterk aanbevolen** - zie GPU-tabel hieronder
- 20 GB vrije schijfruimte voor een volledige installatie (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg en alle Python-pakketten worden automatisch geïnstalleerd** bij de eerste keer opstarten als ze ontbreken. Geen handmatige installatie vereist.

**Optionele systeemafhankelijkheid** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Indien geïnstalleerd, wordt het gebruikt voor het behouden van de toonhoogte in de profielgestuurde kwaliteitsband (standaard 1,15-1,50, tot 1,65 voor harde inhoud), waardoor het resterende "chipmunk"-effect op gekloonde XTTS-stemmen wordt verwijderd. Zonder deze pijplijn blijft de pijplijn ongewijzigd (automatische terugval naar ffmpeg `atempo`). Kwaliteitsprofielen geven nu de voorkeur aan extra korte vertaalpogingen boven extreme audiosnelheid.

### GPU-ondersteuning

De pijplijn maakt gebruik van vijf GPU-versnelde componenten (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). GPU-dekking is niet uniform bij alle leveranciers:

| GPU | Windows | Linux | Opmerkingen |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx of nieuwer, CUDA 12.4-stuurprogramma) | ✅ volledige acceleratie | ✅ volledige acceleratie | **Aanbevolen.** Alle 5 componenten draaien op GPU. |
| **AMD** (Radeon) | ⚠️ onvolledig (DirectML ondersteunt geen XTTS en faster-whisper) | ⚠️ gedeeltelijk (ROCm werkt voor Demucs/XTTS/pyannote maar faster-whisper ondersteunt alleen CUDA) | Werkt, maar de Whisper-transcriptie blijft op de CPU en domineert de totale tijd. |
| **Intel Arc** | ⚠️ onvolwassen PyTorch XPU-ondersteuning | ⚠️ hetzelfde | Niet getest. |
| **Geen (alleen CPU)** | ✅ werkt | ✅ werkt | Verwacht **10-20× langzamer** dan realtime. Het transcriberen van een clip van 5 minuten kan meer dan 50 minuten duren, alleen al met Whisper large-v3. |

**Aanbevolen NVIDIA VRAM:**

| VRAM | Gangbare grafische kaarten | Ervaring |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Bruikbaar, kan XTTS + Wav2Lip niet tegelijkertijd uitvoeren |
| 8 GB | RTX 3060 Ti, 4060 | Volledige pijplijn, geen marge |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Aanbevolen - comfortabel** |
| 24 GB | RTX 3090, 4090 | Reservecapaciteit voor grote batches |

## Installatie

### Windows

1. Kloon of download deze repository
2. Klik met de rechtermuisknop op `setup_windows.bat` → **Uitvoeren als beheerder** → menu toont `[1] Install`
3. Het installatieprogramma automatisch:
   - Installeert Python 3.11 indien niet aanwezig (systeembreed)
   - Installeert Git for Windows indien niet aanwezig
   - Installeert alle Python-afhankelijkheden (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps, etc.)
   - Download en installeer ffmpeg
   - Installeert de geïntegreerde videospeler (python-mpv plus een libmpv-build in `mpv-runtime`). Deze stap is optioneel: als het mislukt, werkt al het andere en legt het spelervenster uit wat er ontbreekt
   - Creëert een **openbare bureaubladsnelkoppeling** (zichtbaar voor elk Windows-account op de pc)

> Het installatieprogramma is **multi-user**: alles wordt systeembreed geïnstalleerd onder `%ProgramFiles%\VideoTranslatorAI` en elke Windows-gebruiker op de machine vindt de snelkoppeling klaar voor gebruik. VS C++ Build Tools zijn **niet langer vereist** - de onderhouden `coqui-tts`-vork biedt vooraf gecompileerde Python-wielpakketten.

### Linux/macOS

```bash
# Kloon de opslagplaats
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Optioneel: installeer de geteste NVIDIA CUDA 12.4 PyTorch-stack vooraan
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Optioneel: installeer alle Python-runtimepakketten vooraf in plaats van de GUI te laten werken
# installeer ontbrekende pakketten bij de eerste keer uitvoeren
pip install --break-system-packages -r requirements.txt

# Optioneel: de geïntegreerde videospeler (libmpv uit de distributie, python-mpv uit PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Optioneel: installeer het project als een bewerkbaar Python-pakket
pip install --break-system-packages --no-deps -e .

# Start vanaf de bron
python video_translator_gui.py

# Of, na bewerkbare/pakketinstallatie
videotranslatorai
videotranslatorai --preflight
```

> Bij de eerste keer opstarten detecteert de GUI ontbrekende pakketten (faster-whisper, Demucs, Edge-TTS, enz.) en installeert deze automatisch, waarbij de uitvoer naar het logvenster wordt gestreamd. ffmpeg wordt ook automatisch geïnstalleerd via `apt-get` / `dnf` / `pacman` (Linux) of gedownload van GitHub (Windows).

> In de koptekst staat een **Speler**-badge. Als libmpv of python-mpv ontbreekt, geeft het linkerdeelvenster aan wat er ontbreekt en wordt **Installeer speler** aangeboden: op Linux gebruikt het de pakketbeheerder via pkexec (vervolgens `sudo -n`) en wordt het handmatige commando weergegeven als geen van beide werkt; op Windows wordt gevraagd voordat libmpv voor de huidige gebruiker wordt gedownload (ongeveer 32 MB).

### Vereiste profielen

| Bestand | Doel |
|------|---------|
| `requirements.txt` | Volledige, achterwaarts compatibele runtime-installatie. |
| `requirements-core.txt` | Standaard pijplijnpakketten die worden gebruikt door GUI/CLI. |
| `requirements-optional.txt` | XTTS, MarianMT-tokenizers, dagboekregistratie, VAD, sleutelhanger. |
| `requirements-wav2lip.txt` | Wav2Lip runtime en gezichtsdetectiestack (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch-stack getest met NVIDIA CUDA 12.4-wielen. |
| `requirements-player.txt` | Geïntegreerde videospeler: python-mpv (vereist libmpv van het systeem of van het Windows-installatieprogramma). |
| `requirements-dev.txt` | Lichtgewicht afhankelijkheden die worden gebruikt door CI/unit-tests. |

## Verwijderen

### Windows

Voer `setup_windows.bat` uit (klik met de rechtermuisknop → **Als administrator uitvoeren**) en kies `[3] Uninstall` in het menu. Er worden drie verwijderingssubmodi aangeboden:

| Modus | Beheerder vereist | Reikwijdte |
|------|----------------|-------|
| **[1] Volledige verwijdering - één klik** | ✅ | Verwijdert de app-map, de openbare bureaublad-snelkoppeling, ffmpeg uit machine-PATH, de HF-modelcache van elke gebruiker (Whisper/XTTS) en configuratie (`HF token`) en alle Python AI-pakketten die door het installatieprogramma zijn geïnstalleerd. Aan het einde wordt ook gevraagd (opt-in) of **Python 3.11** en **Git for Windows** stilzwijgend moeten worden verwijderd via de stille verwijderingsreeksen in het register. |
| **[2] Alleen huidige gebruiker** | ❌ | Verwijdert alleen de VTAI-configuratie, de HF/XTTS-cache en de verouderde installatie per gebruiker van de huidige gebruiker. **Laat de systeembrede installatie intact** zodat andere Windows-accounts op de pc de app kunnen blijven gebruiken. |
| **[3] Aangepast - gedetailleerd** | ✅ voor systeemitems, ❌ voor gebruikersitems | J/N-prompt voor elke categorie: app-map, snelkoppeling, machine-PATH, verouderde installaties per gebruiker, configuraties/caches per gebruiker, vervolgens gegroepeerde Python-pakketten (TTS, PyTorch-stack, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, pijplijnhulpprogramma's) en ten slotte optionele Python 3.11 en Git. |

**Nooit automatisch verwijderd:** Visual Studio C++ Build Tools (indien aanwezig in oudere versies). Gebruik *Apps en functies* in Windows-instellingen om ze desgewenst handmatig te verwijderen.

### Linux/macOS

Geen speciaal verwijderprogramma - handmatig verwijderen:

```bash
# Python-pakketten geïnstalleerd door het automatische installatieprogramma van de GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Gebruikersgegevens en modelcaches
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (thema's, paneelvolgorde, instellingen)
rm -f  ~/.videotranslatorai_config.json     # verouderde configuratie van versies <= 1.9, indien aanwezig
```

## Gebruik

### Diagnostiek

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Voert lokale omgevingsdiagnostiek uit zonder de vertaling te starten of iets te installeren. `--preflight-lipsync` behandelt Wav2Lip-gezichtspakketten zoals vereist, wat handig is voordat **Lip Sync** wordt ingeschakeld. De GUI geeft dezelfde basiscontrole weer via de knop **Diagnostiek** in het logpaneel. `--preflight-player` behandelt de geïntegreerde videospeler (python-mpv en een laadbare libmpv) zoals vereist. `python -m videotranslator.libmpv_runtime check` onderzoekt alleen libmpv (afrit 0 gereed, 2 niet beschikbaar).

### GUI

```bash
python video_translator_gui.py
```

**Lay-out:** batchvertaalinstellingen staan in de kolom aan de rechterkant, als een stapel instellingenpanelen: **Invoer**, **Vertaling**, **Werkstroomprofiel**, **Start** en de opvouwbare geavanceerde secties (model, vertaalengine, audio, stemklonen, lipsynchronisatie, dagboekschrijven, opties, hotwords). Het grote gebied aan de linkerkant is de **geïntegreerde videospeler** (transport, afspeellijst, A/B origineel versus nagesynchroniseerde audio, ondertitels, momentopname, volledig scherm), met daaronder de **real-time vertaling**balk. Sleep een kaart aan de hand van de titel of aan de **≡**-greep om deze omhoog of omlaag in de kolom te verplaatsen; de bestelling wordt opgeslagen (`ui_panel_order`) en bij de volgende start hersteld. Het logboekpaneel aan de onderkant kan worden verborgen met **Verberg logboek**. Bij het opstarten wordt het venster geopend, gecentreerd op de huidige monitor (die onder de aanwijzer) en gemaximaliseerd, zodat het zich goed gedraagt ​​in een opstelling met meerdere monitoren.

**Besturingselementen video-videospeler:** pictogrammen gebruiken consistente functionele kleuren in elk thema, onafhankelijk van de geselecteerde accentkleur:

| Controle | Kleur |
|---------|--------|
| Speel video af | Groen |
| Pauzeren (vervangt afspelen tijdens het spelen) | Amber |
| Stop het afspelen | Koraal rood |
| Vorige / terug 10 s / vooruit 10 s / volgende | Blauw |
| Momentopname | Violet |
| Map openen | Goud |

Door te zweven wordt een subtiel getinte achtergrond toegevoegd. Niet-beschikbare bedieningselementen zijn neutraal; afspeellijstnavigatie blijft bruikbaar na Stop. Tooltips en toetsenbordfocusindicatoren blijven beschikbaar, dus kleur is niet de enige manier om acties te identificeren.

**Van lokale bestanden:**
1. Klik op **Toevoegen** om een of meer videobestanden te selecteren
2. Kies bron- en doeltaal
3. Open de sectie **Model** en selecteer een Whisper-model (`small` is een goede balans tussen snelheid en nauwkeurigheid)
4. Kies een stem en pas indien nodig de TTS-snelheid aan
5. *(Optioneel)* Selecteer in **Vertaalengine** **Google** (standaard), **MarianMT** (lokaal/offline), **DeepL Free** of **Ollama LLM** (lokaal, aanbevolen voor spraaknasynchronisatie)
6. *(Optioneel)* **Voice Cloning** (XTTS v2) en/of **identificatie van sprekende mensen inschakelen**
7. *(Optioneel)* **Lipsynchronisatie** inschakelen (Wav2Lip)
8. Klik op **Vertaling starten**

**Van YouTube (of een ondersteunde site):**
1. Plak een of meer URL's in het veld **URL** (één per regel)
2. Configureer taal, model en stem zoals gewoonlijk
3. Klik op **⬇ Downloaden en vertalen**

> yt-dlp ondersteunt YouTube, Vimeo, Twitter/X, TikTok en [1000+ andere sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Verklaring over redelijk gebruik:** Het downloaden van video's via yt-dlp wordt beschouwd als geautomatiseerde toegang door platforms zoals YouTube en kan in strijd zijn met hun Servicevoorwaarden. Zwaar of herhaald gebruik vanaf hetzelfde IP-adres kan resulteren in tijdelijke blokkeringen (HTTP 429/aanmelding vereist fouten). Gebruik een VPN of verander uw IP als u downloadfouten tegenkomt. Deze tool is uitsluitend bedoeld voor persoonlijk, niet-commercieel gebruik. Herdistributie van vertaalde inhoud kan inbreuk maken op het auteursrecht. Respecteer altijd de rechten van de oorspronkelijke maker.

### Realtime vertaling (ondertiteling en experimentele nasynchronisatie)

Bekijk een lokaal bestand of een opgeloste on-demand videolink met vertaalde ondertitels en optionele gesproken vertaling. Gebruik de balk onder de speler:

**Van een link:**

1. Plak een link in het veld **URL**
2. Stel de bron- en doeltaal in, kies een stem en pas de schuifregelaar **Vertraging** aan
3. Selecteer **Nagesynchroniseerde stem** en/of **Ondertiteling**
4. Als u alleen de vertaalde stem wilt horen, selecteert u **Originele audio dempen** voordat u begint (in het Italiaans: **Silenzia originale**, naast het selectievakje voor ondertitels)
5. Klik op **In realtime vertalen** - de link is opgelost en de vertaling begint

**Vanuit een geladen bestand:** laad een video in de speler (Invoer -> Toevoegen en selecteer deze), laat het URL-veld leeg, kies dezelfde live-instellingen en klik op **Vertalen in realtime**. Een URL heeft voorrang als het veld niet leeg is.

- **Engine:** MarianMT (offline, standaard), Google, DeepL of Ollama. Spraakherkenning (Whisper) wordt lokaal uitgevoerd. Offline modellen hebben een eerste download nodig.
- **Voice dubbing:** experimentele Edge-TTS-spraakweergave via een tweede mpv-instantie. Het vereist internettoegang en staat los van batch-spraakklonen.
- **Originele audio dempen:** beschikbaar zowel vóór het starten als tijdens de vertaling. Het legt de volledige originele soundtrack stil, inclusief muziek en effecten, maar laat de vertaalde stem hoorbaar. Het isoleert niet de persoon die in de originele audio spreekt. Schakel het uit om de soundtrack te herstellen; het wordt gereset wanneer de livesessie eindigt. De luidsprekerknop van de speler is de algemene mute-knop, niet deze onafhankelijke bediening.
- **Pauzeer en zoek:** de bedieningselementen van de videospeler zijn verbonden met de livesessie; end-to-end audiosynchronisatie vereist nog steeds platformspecifieke acceptatietests.
- **Huidige limieten:** verwerking van clipoverlap/fade, kalibratie van audiotiming en Windows-acceptatie blijven open. Groeiende live-uitzendingen worden nog niet ondersteund; het live-moduslabel impliceert geen ondersteuning voor het opnemen van een uitzending naarmate deze groeit. Zie de [implementatiestatus en resterende werkzaamheden](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Voor een opgeslagen nagesynchroniseerde video gebruikt u **Downloaden en vertalen** / **Vertaling starten** in plaats van het realtime voorbeeld.

### Vertaalmachineblokken en VPN

Er kunnen twee verschillende blokkades optreden, met verschillende oplossingen:

| Blok | Symptoom | Repareren |
|-------|---------|-----|
| **Download** (yt-dlp) | "Meld u aan om te bevestigen dat u geen bot bent", HTTP 429 | **VPN** / IP roteren, of ingelogd zijn op YouTube in je browser (cookies worden automatisch gelezen) |
| **Vertaling** (gratis eindpunt van Google) | "Google Translate kon niet vertalen... verzoeksnelheid beperkt/geblokkeerd" | Gebruik **MarianMT** (offline) of **Ollama** (lokaal) - geen limiet voor het aantal verzoeken. Een VPN helpt ook. De batchstroom valt nu **automatisch terug naar MarianMT** wanneer Google wordt geblokkeerd. |

### Thema's en uitstraling

Klik op het tandwielpictogram in de koptekst om **Instellingen** te openen:

- **Thema**: Automatisch (volgt de donker/licht-modus van het besturingssysteem), Graphite (standaard), Slate, Light, Neon.
- **Accentkleur**: standaard per thema, of blauw, groenblauw, violet, groen, amber, roze.
- **Tekstgrootte**: klein, normaal, groot, extra groot.
- **Interfacetaal**: 26 talen.

Wijzigingen zijn onmiddellijk van toepassing, zonder opnieuw op te starten, en worden opgeslagen in het configuratiebestand (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Standaardwaarden herstellen** brengt het Graphite-thema, het standaardaccent, de normale tekstgrootte en de standaardvolgorde van de instellingenpanelen terug.

### Commandoregel

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Alle opties:**

| CLI-optie | Beschrijving | Standaard |
|------|-------------|---------|
| `--lang-source` | Brontaal (`auto` voor automatische detectie) | `auto` |
| `--lang-target` | Doeltaalcode (bijv. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS-stemnaam | auto |
| `--model` | Whisper-model (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS-snelheidsaanpassing (bijv. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` of `deepl` | `google` |
| `--deepl-key` | DeepL Free API-sleutel | - |
| `--diarize` | Identificatie van sprekende mensen mogelijk maken (diariseren) (pyannote) | - |
| `--hf-token` | HuggingFace-token voor dagboekschrijven | - |
| `--lipsync` | Pas Wav2Lip-lipsynchronisatie toe na het nasynchroniseren van stemmen | - |
| `--subs-only` | Genereer alleen `.srt`, sla spraaknasynchronisatie over | - |
| `--no-subs` | Sla de `.srt`-generatie over | - |
| `--no-demucs` | Stem-/muziekscheiding overslaan | - |
| `--output` / `-o` | Pad voor uitvoerbestand | auto |
| `--output-dir` | Map voor vertaalde bestanden (één plaats, Windows en Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Verwerk meerdere bestanden | - |

### integratietesten met echte modellen

De standaardtestsuite vermijdt echte modeldownloads en lang GPU-werk. Om empirische opt-in-controles uit te voeren voor de geïnstalleerde lokale stack:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Deze controles valideren echte Wav2Lip-importen, Torch CUDA-beschikbaarheid, Ollama-daemon-beschikbaarheid en faster-Whisper op synthetische spraak. Ze mislukken opzettelijk of slaan over wanneer de lokale driver/daemon/modelstatus niet gereed is.

**Voorbeelden:**

```bash
# Vertaal Italiaanse video naar het Engels met lokale MarianMT
# (downloadt een model van ~298 MB bij het eerste gebruik, daarna volledig offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Vertalen met stemklonen + identificatie van sprekende mensen (diariseren)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Vertalen met lipsynchronisatie
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Alleen ondertiteling (geen gesproken nasynchronisatie)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper-modellen

| Model | Grootte | Snelheid | Nauwkeurigheid |
|-------|------|-------|----------|
| tiny | 75MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` is een gedistilleerde versie van `large-v3` (4 decoderlagen versus 32) - bijna grote kwaliteit met een snelheid van ongeveer `medium`-niveau. Aanbevolen standaard op een moderne GPU als transcriptiesnelheid belangrijk is; De kwaliteitsdaling bij meertalig materiaal is gering.

> Modellen worden automatisch gedownload bij het eerste gebruik.

## Stand-alone module-CLI's

Het modulaire pakket bevat vier gebruikersgerichte tools die direct kunnen worden aangeroepen zonder de volledige pijplijn te lanceren:

```bash
# Pre-flight een video voor aanwezigheid van gezichten (Wav2Lip zou overslaan als deze afwezig is).
python3 -m videotranslator.face_detector path/to/video.mp4
# uitgang 0 = gezicht aanwezig, uitgang 1 = geen gezicht

# Analyseer een *_metrics.csv geproduceerd door build_dubbed_track.
# Rapporteert P50/P75/P90/P95 van pre_stretch_ratio, uitsplitsing van de hoorbaarheidsband,
# uitgebreid enginegebruik en de top-N slechtste uitschieters met hun doeltekst.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Tekst opschonen voor TTS (herschrijft dubbele punten, puntkomma's, weglatingstekens, streepjes).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Schat de moeilijkheidsgraad bij het nasynchroniseren van spraak op basis van een .srt- of .json-segmentbestand VOORDAT u TTS uitvoert.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Elk gereedschap heeft `-h`/`--help` voor volledige opties. Ze zijn op zichzelf staand en hergebruiken dezelfde modules waar de pijplijn voor stemnasynchronisatie op vertrouwt, zodat hun uitvoer consistent blijft met de runtime.

## Licentie

MIT

### Componenten van derden

De repositorycode is MIT. De installatieprogramma's downloaden de onderstaande componenten tijdens de installatie uit hun eigen bronnen; het project herdistribueert ze niet.

- **libmpv** (https://github.com/mpv-player/mpv), de engine van de geïntegreerde videospeler. Windows: eerst wordt de LGPL-build van zhongfly (https://github.com/zhongfly/mpv-winbuild) geprobeerd; een vastgezette GPL gebouwd door shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) is de fallback. `mpv-runtime\BUILD.txt` registreert de broncode, de licentievariant en de mpv-commit, en de licentietekst bevindt zich naast de DLL. Linux: het distributiepakket (`libmpv2`, `libmpv1`, `mpv-libs` of `mpv`).
- **FFmpeg** binnen libmpv (LGPL of GPL, volgens de libmpv-build).
- **python-mpv** (`mpv` op PyPI), GPLv2+ of LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), gebruikt door het Windows-installatieprogramma om libmpv uit te pakken en daarna verwijderd.
- **Vulkan loader** (Khronos, MIT en Apache-2.0), alleen gedownload op Windows als `vulkan-1.dll` ontbreekt.
- **edge-tts** (LGPLv3), gebruikt door de pijplijn voor spraaknasynchronisatie.
- **MarianMT-modellen** (Helsinki-NLP), bij eerste gebruik gedownload van de Hugging Face Hub onder hun eigen licenties (Apache-2.0 voor de `opus-mt`-modellen, CC-BY-4.0 voor `opus-mt-tc-big`).
