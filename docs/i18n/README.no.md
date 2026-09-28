# 🎬 Video Translator AI

[Engelsk](../../README.md) | [Alle oversettelser](README.md)

**Les denne siden i:** [Bahasa Indonesia](README.id.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Nederlands](README.nl.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Suomi](README.fi.md) · [Svenska](README.sv.md) · [Tiếng Việt](README.vi.md) · [Türkçe](README.tr.md) · [Ελληνικά](README.el.md) · [Русский](README.ru.md) · [Українська](README.uk.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

AI-drevet videostemmedubbingsverktøy som automatisk transkriberer, oversetter og redubber videoer til 26 språk, med lokale behandlingsalternativer og ingen API-nøkler kreves som standard. Whisper talegjenkjenning kjører lokalt; Edge-TTS, Google Translate og DeepL krever en internettforbindelse. Valgfrie funksjoner (DeepL, identifikasjon av personer som snakker (diarisering)) kan kreve en API-nøkkel eller tilgangstoken.

![Hovedvinduet til Video Translator AI: videospiller og oversettelsespaneler](../../assets/screenshot.png)

> **v2.0** - modulær pakke, lokal Ollama-oversettelse, kvalitetsprofilorkestrering, installerbare Python-metadata og opt-in-integrasjonstester med ekte modeller. Se [GitHub-utgivelser](https://github.com/HeartB1t/VideoTranslatorAI/releases) og forpliktelseshistorikken for den fullstendige listen over endringer.

> **v2.1.0** - Windows-installasjonsprogrammet er herdet (Microsoft Visual C++-kjøretidsmiljø, en tydelig oppsettslogg, selvoppdatering fra GitHub-utgivelser), renere logger (én fremadskridende fremdriftslinje per nedlasting), programvarebasert videodekoding på maskiner uten GPU, og hevede transportknapper. Se [GitHub-utgivelser](https://github.com/HeartB1t/VideoTranslatorAI/releases).

## Hvordan det fungerer

1. **Transkripsjon** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transkriberer lyden (GPU-akselerert)
2. **Stemme/musikk-separasjon** - [Demucs](https://github.com/facebookresearch/demucs) isolerer vokal fra bakgrunnsmusikk
3. **Oversettelse** - MarianMT (lokalt, offline), Google Translate, DeepL Free eller **Ollama LLM** (Qwen3, kortfattede oversettelser som er klar over spor)
4. **identifikasjon av personer som snakker (diarisering)** *(valgfritt)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifiserer hvem som snakker i hvert segment
5. **stemmedubbing** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ stemmer) eller [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (stemmekloning, for hver høyttaler i samtalen)
6. **Mixing** - dubbet stemme mikset tilbake med original bakgrunnsmusikk
7. **Normalisering** - endelig lyd normalisert til -23 LUFS (EBU R128 kringkastingsstandard)
8. **Lip Sync** *(valgfritt)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synkroniserer munnbevegelser til den dubbede lyden

## Funksjoner

- 🖥️ Tema GUI (Tkinter) - ingen kommandolinje nødvendig; Graphite, Slate, Light og Neon temaer, aksentfarger, tekststørrelse og innstillingspaneler kan du omorganisere ved å dra
- 🕹️ **Skins** - lekne utseender fra innstillingene: Dex og Handheld minner om en lommekonsoll (pikselskrift, tykke rammer), CRT og CRT Amber om en fosforskjerm fra 80-tallet, med krumning og skannelinjer også på videoen
- 🔊 **Lytt før du velger** - et høyttalerikon ved stemmen spiller av en prøvesetning på målspråket (Edge-TTS) eller den gratis prøven av en ElevenLabs-stemme
- 🌍 **26 målspråk** med flere stemmer per språk
- 🌐 **UI på 26 språk** - selve grensesnittet tilpasser seg språket ditt
- 🎬 **YouTube- og URL-støtte** - lim inn en hvilken som helst YouTube-kobling og oversett direkte (drevet av yt-dlp)
- ▶️ **Integrert videospiller** (libmpv/mpv) - fargekodede transportkontroller, spilleliste, A/B-original vs dubbet lyd, undertekstveksling, øyeblikksbilde, fullskjerm, åpen mappe
- ⏱️ **Oversettelse i sanntid** - se en lokal fil eller en videolenke på forespørsel med oversatte undertekster og en forsinkelsesglidebryter; motorer MarianMT / Google / DeepL / Ollama. Dubbingen bruker Edge-TTS eller, valgfritt, ElevenLabs-stemmer via en andre mpv-instans; overlappende setninger venter, øker farten eller tones ut. Pågående direktesendinger støttes ikke ennå.
- 🎵 Stemme-/musikkseparasjon via Demucs (beholder bakgrunnsmusikk)
- 🔇 **Demp originallyd**, tilgjengelig før og under direkteoversettelse, demper videoens lydspor mens den oversatte stemmen holdes hørbar. Slå den av for å gjenopprette den originale lyden; den tilbakestilles når live-økten avsluttes.
- 🧠 **MarianMT** - fullstendig lokal, offline nevral oversettelse (Helsinki-NLP, ingen grenser for forespørselshastighet, ingen API-nøkkel)
- 🤖 **Ollama LLM-oversettelse** *(ny i versjon 2.0)* - lokal LLM (Qwen3, Llama, Mistral) som produserer sporbevisste konsise oversettelser for naturlig stemmedubbing, automatisk oppdager/installerer/starter/trekker modell ved første gangs bruk
- 🎙️ **Stemmekloning** - Coqui XTTS v2 kloner personen som snakker med den originale lydens stemme på målspråket (~1,8 GB-modell), med adaptiv hastighet per segment og flerfrøforsøk på hallusinasjoner
- 👥 **identifikasjon av personer som snakker (diarisering)** - Pyannote-audio 3.1 identifiserer flere personer som snakker; XTTS kloner hver stemme separat
- 💋 **Lip Sync** - Wav2Lip GAN synkroniserer munnbevegelser til den dubbede lyden (~416 MB modell)
- 🔊 **Lydnormalisering** - automatisk -23 LUFS loudness normalisering (EBU R128)
- ✏️ Tekstredigering - gjennomgå og korriger undertekster før stemmedubbing
- 📦 Batchbehandling - oversett flere videoer eller URL-er samtidig
- ⚡ GPU-akselerasjon via CUDA (faller tilbake til CPU automatisk)
- 📄 Valgfri `.srt` underteksteksport
- 🔁 **DeepL Free** oversettelsesmotor (valgfritt - 500 000 tegn/måned, krever gratis API-nøkkel)
- 🔧 **Autoinstaller** - manglende Python-pakker og ffmpeg installeres automatisk ved første oppstart
- 🧮 **Modeller for denne PC-en** - oppdager CPU, RAM, GPU, VRAM og ledig diskplass, anbefaler modeller for talegjenkjenning, oversettelse og stemme etter hastighet, balanse eller kvalitet, laster ned og kontrollerer Whisper-modeller og måler dem på din egen video
- 🗣️ **ElevenLabs-stemmer** *(valgfritt, på nett, betalt)* - naturlige flerspråklige stemmer til direktedubbingen med din egen API-nøkkel; svikter nøkkelen eller kvoten, tar Edge-TTS over
- 🧬 **Stemmekloning med Voicebox** *(valgfritt)* - kloner stemmen til den som snakker via en egen lokal [Voicebox](https://github.com/jamiepine/voicebox)-server; kjører den ikke, bruker videoen Edge-TTS

## Støttede språk

Arabisk, kinesisk, tsjekkisk, dansk, nederlandsk, engelsk, finsk, fransk, tysk, gresk, hindi, ungarsk, indonesisk, italiensk, japansk, koreansk, norsk, polsk, portugisisk, rumensk, russisk, spansk, svensk, tyrkisk, ukrainsk, vietnamesisk

## Stemmekatalog

Edge-TTS stemmekatalogen er definert i `LANGUAGES` nær toppen av `video_translator_gui.py`. Den ordboken er kilden til sannhet for målspråknavn, GUI-stemmeradioknapper og CLI-tilbakestemmen når `--voice` er utelatt.

Claude/prosjekt-vedlikeholdsnotater speiler denne plasseringen i `CLAUDE.md` under **Voice Catalog Source Of Truth**, slik at fremtidige kodeagenter vet hvor de skal oppdatere stemmer og hvor README peker brukere.

## Oversettelsesmotorer

| Motor | Oppsett | Grenser | Kvalitet |
|--------|-------|--------|---------|
| **Google Translate** *(standard)* | Ingen | Uoffisiell skraping - kan strupes på store videoer | ★★★★ |
| **MarianMT** | Ingen - laster ned ~298 MB per språkpar ved første gangs bruk | Ingen - helt offline etter nedlasting | ★★★★ |
| **DeepL Free** | Gratis API-nøkkel på [deepl.com](https://www.deepl.com/pro-api) | 500 000 tegn/måned | ★★★★★ |
| **Ollama LLM** *(anbefalt for stemmedubbing - nytt i v2.0)* | Automatisk installert ved første gangs bruk (~1 GB Ollama + 5 GB-modell) | Ingen - helt lokalt | ★★★★★ |

> **MarianMT** bruker [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP)-modeller, bufret lokalt etter den første nedlastingen. Krever eksplisitt kildespråk (auto-deteksjon støttes ikke - velg kildespråk manuelt). Nødvendige Python-pakker (`sacremoses`, `sentencepiece`) installeres automatisk ved første valg hvis de mangler.

> **Ollama LLM** *(ny i v2.0)* er den anbefalte motoren for stemmedubbing fordi den produserer oversettelser som er klar over måltidsluken. Der MarianMT oversetter bokstavelig og produserer italiensk / spansk / fransk ~25 % lenger enn engelsk (tvinger hørbar lydkomprimering på TTS), blir LLM bedt om å holde hvert segment kortfattet og naturlig for muntlig levering, og oppnå et typisk char-forhold på 0,85-0,95 vs kilde. Standardmodellen er `qwen3:8b` (5,2 GB på disk, ~6 GB VRAM); `qwen3:4b` (~3 GB) er det lette alternativet, `qwen3:14b` det høyere kvalitet. Rørledningen oppdager automatisk Ollama-binæren, installerer den automatisk via det offisielle installasjonsprogrammet ved første gangs bruk (med samtykke popup), starter daemonen og trekker den valgte modellen - ingen manuell oppsett kreves. Bytter automatisk til Google Translate hvis noe mangler.

## Stemmekloning (XTTS v2)

Når den er aktivert, trekker appen ut talerens stemme fra den originale videoen og bruker den som referanse for å klone stemmen på målspråket.

- Støttede språk: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- For de resterende 9 språkene brukes Edge-TTS automatisk som reserve
- Modell (~1,8 GB) lastes ned automatisk ved første gangs bruk til `~/.local/share/tts/`
- **VAD-filtrert referanse** (v1.4): 10-15 s kontinuerlig tale valgt fra originallyden via [silero-vad](https://github.com/snakers4/silero-vad) for bedre stemmekloningskvalitet
- **Generasjonshastighet** konfigurerbar (`xtts_speed`, standard `1.25`): Høyere verdier reduserer etterbehandlingslydkomprimeringsartefakter når den oversatte teksten er lengre enn kildesporet. Still inn via `~/.config/videotranslatorai/config.json` eller CLI `--xtts-speed`
- Kjører på CUDA eller CPU

## identifikasjon av personer som snakker (diarisering) (pyannote-lyd)

Når den er aktivert, identifiserer appen hvem som snakker i hvert segment. Kombinert med stemmekloning klones hver høyttalers stemme separat - ideelt for intervjuer, podcaster og videoer med flere personer.

- Krever et gratis [HuggingFace-token](https://huggingface.co/settings/tokens) (engangsregistrering)
- **Token lagret sikkert** (v1.4) via OS-nøkkelringen: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatisk migrering fra tidligere JSON-lagring i ren tekst
- Etter den første nedlastingen, fungerer helt offline
- Modell: `pyannote/speaker-diarization-3.1`

## Lip Sync (Wav2Lip)

Når den er aktivert, bruker appen Wav2Lip GAN for å synkronisere motivets munnbevegelser med den dubbede lyden - personen ser ut til å snakke det oversatte språket.

- Modell (~416 MB) og repo klonet automatisk ved første gangs bruk til `~/.local/share/wav2lip/`
- Kjører på CUDA (anbefalt) eller CPU
- Øker behandlingstiden betraktelig
- Fungerer best på videoer med ett enkelt, godt synlig ansikt

## Modeller for denne PC-en

Avanserte innstillinger > Modell > **Modeller for denne PC-en** åpner et vindu som leser maskinvaren (CPU, RAM, GPU og brukbar VRAM, ledig diskplass) uten å endre noe og anbefaler én modell for hvert trinn: talegjenkjenning for filer og direkte, oversettelse og stemme.

- Velg **Hastighet**, **Balansert** eller **Kvalitet**: hver anbefaling oppgir sine grunner.
- Alle andre valg kan fortsatt velges og vurderes for denne PC-en: passer, i grenseland, for stor, for lite diskplass eller nettjeneste.
- **Last ned** henter en manglende Whisper-modell med fremdrift og Avbryt og kontrollerer hver fil mot sjekksummene fra Hugging Face; ingenting lastes ned før du trykker på knappen.
- **Ytelsestest** måler den valgte modellen på den innlastede videoen (lasting, første setning, hastighet); lyden forlater aldri PC-en.
- **Bruk** setter modellene; **Gjenopprett forrige** henter tilbake det tidligere valget. NVIDIA-GPU-er brukes via CUDA; AMD- (ROCm) og Apple-GPU-er vises, men der kjører talemodellene på CPU-en.

## Voicebox (stemmekloning via en lokal server)

[Voicebox](https://github.com/jamiepine/voicebox) (MIT) er et eget program som kloner stemmer. Installer og start det selv; denne appen kaller bare det lokale API-et og installerer det aldri.

- Avanserte innstillinger > Stemmekloning > **Voicebox**: angi adressen (standard `http://127.0.0.1:17493`), motoren (`chatterbox` som standard) og trykk **Kontroller**.
- For hver video klones en midlertidig stemme fra en ren prøve av den som snakker (én per taler med talerskille), og den slettes etterpå.
- Bare en adresse på denne PC-en godtas, fordi Voicebox-API-et ikke har autentisering.
- Svarer ikke Voicebox eller støtter det ikke målspråket, dubbes videoen med Edge-TTS.

## Krav

- Python 3.10+ (Windows-installasjonsprogrammet gir 3.11.9 automatisk)
- Windows 10/11 (x64), Linux eller macOS
- **NVIDIA GPU anbefales på det sterkeste** - se GPU-tabellen nedenfor
- 20 GB ledig diskplass for full installasjon (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg og alle Python-pakker installeres automatisk** ved første oppstart hvis de mangler. Ingen manuell oppsett nødvendig.

**Valgfri systemavhengighet** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Når den er installert, brukes den for å bevare tonehøyde-bevarende tidsutstrekning i det profilkontrollerte kvalitetsbåndet (standard 1,15-1,50, opp til 1,65 for hardt innhold), og fjerner den gjenværende "chipmunk"-effekten på klonede XTTS-stemmer. Rørledningen kjører uendret uten den (automatisk fallback til ffmpeg `atempo`). Kvalitetsprofiler foretrekker nå ekstra korte oversettelsesforsøk fremfor ekstrem lydhastighet.

### GPU-støtte

Rørledningen bruker fem GPU-akselererte komponenter (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). GPU-dekning er ikke ensartet på tvers av leverandører:

| GPU | Windows | Linux | Notater |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx eller nyere, CUDA 12.4-driver) | ✅ full akselerasjon | ✅ full akselerasjon | **Anbefalt.** Alle 5 komponentene kjører på GPU. |
| **AMD** (Radeon) | ⚠️ ufullstendig (DirectML støtter ikke XTTS og faster-whisper) | ⚠️ delvis (ROCm fungerer for Demucs/XTTS/pyannote, men faster-whisper støtter bare CUDA) | Fungerer, men Whisper-transkripsjonen forblir på CPU og dominerer den totale tiden. |
| **Intel Arc** | ⚠️ umoden PyTorch XPU-støtte | ⚠️ samme | Ikke testet. |
| **Ingen (kun CPU)** | ✅ fungerer | ✅ fungerer | Forvent **10-20× tregere** enn sanntid. Et 5-minutters klipp kan ta mer enn 50 minutter bare å transkribere med Whisper large-v3. |

**Anbefalt NVIDIA VRAM:**

| VRAM | Typiske skjermkort | Erfaring |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Brukbar, kan ikke kjøre XTTS + Wav2Lip samtidig |
| 8 GB | RTX 3060 Ti, 4060 | Full pipeline, ingen margin |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Anbefalt - behagelig** |
| 24 GB | RTX 3090, 4090 | Reservekapasitet for store partier |

## Installasjon

### Windows

Trinn for trinn, ingen kommandolinje nødvendig. Testet på en ren Windows 11-PC.

1. **Last ned** prosjektet: den grønne **Kode**-knappen → **Last ned ZIP**, eller den nyeste zip-filen fra [GitHub-utgivelser](https://github.com/HeartB1t/VideoTranslatorAI/releases). Pakk den ut i en hvilken som helst mappe, for eksempel skrivebordet.
2. **Installer**: høyreklikk `setup_windows.bat` → **Kjør som administrator** → trykk `1` (Install). Hvis SmartScreen sier «Windows beskyttet PC-en din», klikk **Mer informasjon** → **Kjør likevel**: skriptet er ren tekst, du kan åpne det med Notisblokk.
3. **Vent**: på en ren PC med rask internettforbindelse tar det rundt 15 minutter og 8 GB diskplass. Installasjonsprogrammet laster ned og setter opp, i denne rekkefølgen:
   - Python 3.11 (systemomfattende) og Microsoft Visual C++-kjøretidsmiljøet, hvis det mangler
   - Python-pakkene: PyTorch (CUDA 12.4 med et NVIDIA-skjermkort, ellers CPU-versjonen), faster-whisper, Demucs, coqui-tts, pyannote og Wav2Lip-stakken
   - Git for Windows (for Wav2Lip), ffmpeg og den integrerte videospilleren (libmpv i `mpv-runtime`; valgfritt, alt annet fungerer uten den)
   - en **snarvei på skrivebordet** for hver Windows-konto på PC-en og en **Start-meny**-mappe med applikasjonen og **Oppdater Video Translator AI**
4. **Start** den fra skrivebordssnarveien eller Start-menyen. Uten et NVIDIA-GPU fungerer appen på CPU-en, bare tregere: velg en liten Whisper-modell.

> Alt er installert systemomfattende under `%ProgramFiles%\VideoTranslatorAI`, slik at alle Windows-brukere på maskinen finner snarveien klar. Hver kjøring av `setup_windows.bat` skriver en logg til `%USERPROFILE%\VideoTranslatorAI-setup.log`: legg den ved når du melder inn et problem. Hvis installasjonsprogrammet avslutter med **INSTALLASJON UFULLSTENDIG**, kjør det på nytt og velg `[2] Repair / Update`. VS C++ byggeverktøy er ikke nødvendig: den vedlikeholdte `coqui-tts`-gaffelen leverer forhåndskompilerte hjul.

### Linux / macOS

```bash
# Klone repoen
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Valgfritt: installer den testede NVIDIA CUDA 12.4 PyTorch-stabelen foran
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Valgfritt: forhåndsinstaller alle Python runtime-pakker i stedet for å la GUI
# installer manglende pakker ved første kjøring
pip install --break-system-packages -r requirements.txt

# Valgfritt: den integrerte videospilleren (libmpv fra distribusjonen, python-mpv fra PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Valgfritt: installer prosjektet som en redigerbar Python-pakke
pip install --break-system-packages --no-deps -e .

# Start fra kilden
python video_translator_gui.py

# Eller etter redigerbar/pakkeinstallasjon
videotranslatorai
videotranslatorai --preflight
```

> Ved første oppstart oppdager GUI eventuelle manglende pakker (faster-whisper, Demucs, Edge-TTS, etc.) og installerer dem automatisk, og strømmer utdataene til loggvinduet. ffmpeg installeres også automatisk via `apt-get` / `dnf` / `pacman` (Linux) eller lastet ned fra GitHub (Windows).

> Overskriften viser et **Spiller**-merke. Når libmpv eller python-mpv mangler, sier den venstre ruten hva som mangler og tilbyr **Installer spiller**: på Linux bruker den pakkebehandlingen gjennom pkexec (deretter `sudo -n`) og viser den manuelle kommandoen når ingen av dem fungerer; på Windows spør den før nedlasting av libmpv for gjeldende bruker (ca. 32 MB).

### Kravprofiler

| Fil | Formål |
|------|---------|
| `requirements.txt` | Full, bakoverkompatibel kjøretidsinstallasjon. |
| `requirements-core.txt` | Standard pipeline-pakker brukt av GUI/CLI. |
| `requirements-optional.txt` | XTTS, MarianMT-tokenizers, diarisering, VAD, nøkkelring. |
| `requirements-wav2lip.txt` | Wav2Lip kjøretid og ansiktsgjenkjenningsstabel (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch stack testet med NVIDIA CUDA 12.4 hjul. |
| `requirements-player.txt` | Integrert videospiller: python-mpv (trenger libmpv fra systemet eller fra Windows-installasjonsprogrammet). |
| `requirements-dev.txt` | Lette avhengigheter brukt av CI/enhetstester. |

## Oppdatering

### Windows

Start-meny → **Video Translator AI** → **Oppdater Video Translator AI** (dette krever administratorrettigheter), eller kjør `setup_windows.bat` som administrator og velg `[2] Repair / Update`. Installasjonsprogrammet sjekker [GitHub-utgivelser](https://github.com/HeartB1t/VideoTranslatorAI/releases): hvis det finnes en nyere versjon, laster det ned utgivelsen, verifiserer SHA256-sjekksummen og installerer den; ellers reparerer det de gjeldende filene. Innstillingene dine, lagrede nøkler, nedlastede modeller og oversatte videoer beholdes. Uten internettforbindelse hoppes oppdateringen over, og reparasjonen fortsetter.

### Linux / macOS

```bash
cd VideoTranslatorAI
git pull
pip install --break-system-packages -r requirements.txt
```

## Avinstaller

### Windows

Kjør `setup_windows.bat` (høyreklikk → **Kjør som administrator**) og velg `[3] Uninstall` fra menyen. Tre undermoduser for avinstallering tilbys:

| Modus | Admin kreves | Omfang |
|------|----------------|-------|
| **[1] Full avinstallering - ett klikk** | ✅ | Fjerner app-mappen, skrivebordssnarveien og oppføringene i Start-menyen, ffmpeg fra maskinen PATH, hver brukers HF-modellbuffer (Whisper/XTTS) og config (`HF token`), og alle Python AI-pakker installert av installasjonsprogrammet. På slutten spør den også (opt-in) om de skal avinstallere **Python 3.11** og **Git for Windows** i stillhet via deres registerstrenger for stille avinstallering. |
| **[2] Kun nåværende bruker** | ❌ | Fjerner bare kjørende brukers VTAI-konfigurasjon, HF/XTTS-buffer og eldre installasjon per bruker. **Gjør installasjonen for hele systemet intakt** slik at andre Windows-kontoer på PC-en kan fortsette å bruke appen. |
| **[3] Egendefinert - granulert** | ✅ for systemelementer, ❌ for brukerelementer | Y/N-spørsmål for hver kategori: appmappe, snarvei, systemets PATH, eldre installasjoner per bruker, brukerkonfigurasjoner og hurtigbuffere, deretter grupper av Python-pakker (TTS, PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip-avhengigheter, pyannote og verktøy for behandlingskjeden) og til slutt valgfri fjerning av Python 3.11 og Git. |

Hver modus fjerner også det programmet lagrer for brukeren: konfigurasjon og daglige logger (`%APPDATA%\VideoTranslatorAI`), programdata med kjøretidene for spiller, JavaScript og Wav2Lip (`%LOCALAPPDATA%\VideoTranslatorAI`), midlertidige filer fra sanntid (`%TEMP%\VideoTranslatorAI`), MarianMT-modellene og de lagrede nøklene (HF-token, ElevenLabs) fra Windows Legitimasjonsbehandling. Nøkler lagres per Windows-konto: hver konto fjerner sine egne med `[2]`.

**Aldri fjernet automatisk:** Visual Studio C++ Build Tools (hvis de finnes fra eldre kjøringer) og Microsoft Visual C++-kjøretidsmiljøet, som andre programmer deler. Bruk *Apper og funksjoner* i Windows-innstillinger for å fjerne dem manuelt hvis ønskelig. Oppsettsloggen `%USERPROFILE%\VideoTranslatorAI-setup.log` beholdes med hensikt.

### Linux / macOS

Ingen dedikert avinstalleringsprogram - fjern manuelt:

```bash
# Python-pakker installert av GUIs autoinstallasjonsprogram
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Brukerdata og modellcacher
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip ~/.cache/wav2lip
rm -rf ~/.config/videotranslatorai          # config (temaer, panelrekkefølge, innstillinger)
rm -rf ~/.local/share/fonts/VideoTranslatorAI   # skrifttyper for skins
rm -rf ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt*   # MarianMT-oversettelsesmodeller
rm -rf ~/.local/share/VideoTranslatorAI                          # programdata (JavaScript-kjøretid for yt-dlp)
rm -rf "${TMPDIR:-/tmp}/VideoTranslatorAI"                       # midlertidige filer fra sanntid
# lagrede nøkler (HF-token, ElevenLabs)
python3 -c "import keyring; [keyring.delete_password('VideoTranslatorAI', u) for u in ('hf_token', 'elevenlabs_api_key') if keyring.get_password('VideoTranslatorAI', u)]"
rm -f  ~/.videotranslatorai_config.json     # eldre konfigurasjon av versjoner <= 1.9, hvis den finnes
```

## Bruk

### Diagnostikk

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Kjører lokalmiljødiagnostikk uten å starte oversettelse eller installere noe. `--preflight-lipsync` behandler Wav2Lip-ansiktspakker etter behov, noe som er nyttig før du aktiverer **Lip Sync**. GUI avslører den samme basekontrollen fra loggpanelets **Diagnostikk**-knapp. `--preflight-player` behandler den integrerte videospilleren (python-mpv og en lastbar libmpv) etter behov. `python -m videotranslator.libmpv_runtime check` sonderer libmpv alene (utgang 0 klar, 2 utilgjengelig).

**Loggfil:** alt loggpanelet viser (hvert klikk og valg, resultater, behandlingstrinn, feil med detaljer) lagres også i `logs/videotranslator.log` ved siden av konfigurasjonen: `~/.config/videotranslatorai/logs/` på Linux, `%APPDATA%\VideoTranslatorAI\logs\` på Windows. Én fil per dag, de siste 7 dagene beholdes; knappen **Diagnostikk** viser banen. Legg den ved når du melder et problem. API-nøkler og tekst skrevet i feltene skrives aldri. Hver linje viser tid, nivå (info, advarsel, feil, på grensesnittets språk, med advarsler og feil farget i panelet) og område, for eksempel [ui] for klikk, [job] for oversettelser, [live] for sanntid; hver oppstart skriver et hode med versjon, system, GPU og innstillinger.

### GUI

```bash
python video_translator_gui.py
```

**Layout:** batch-oversettelsesinnstillinger vises i kolonnen til høyre, som en bunke med innstillingspaneler: **Inndata**, **Oversettelse**, **Arbeidsflytprofil**, **Start** og de sammenleggbare avanserte delene (modell, oversettelsesmotor, lyd, stemmekloning, leppesynkronisering, diaarisering, alternativer, hotwords). Det store området til venstre er den **integrerte videospilleren** (transport, spilleliste, A/B-original vs dubbet lyd, undertekster, øyeblikksbilde, fullskjerm), med **sanntidsoversettelse**-linjen under. Dra et kort etter tittelen eller **≡**-håndtaket for å flytte det opp eller ned i kolonnen; ordren lagres (`ui_panel_order`) og gjenopprettes ved neste start. Loggpanelet nederst kan skjules med **Skjul logg**. Ved start åpnes vinduet sentrert på den gjeldende skjermen (den under pekeren) og maksimert, så det oppfører seg bra på et flerskjermoppsett.

**Video-videospillerkontroller:** ikoner bruker konsekvente funksjonelle farger i hvert tema, uavhengig av den valgte aksentfargen:

| Kontroll | Farge |
|---------|--------|
| Spill av video | Grønn |
| Pause (erstatter Play mens du spiller) | Amber |
| Stopp avspillingen | Korallrød |
| Forrige / tilbake 10 s / frem 10 s / neste | Blått |
| Øyeblikksbilde | Fiolett |
| Åpne mappen | Gull |

Holding legger til en subtil farget bakgrunn. Utilgjengelige kontroller er nøytrale; spillelistenavigasjon forblir brukbar etter stopp. Verktøytips og tastaturfokusindikatorer forblir tilgjengelige, så farger er ikke den eneste måten å identifisere handlinger på.

**Fra lokale filer:**
1. Klikk på **Legg til** for å velge én eller flere videofiler
2. Velg kilde- og målspråk
3. Åpne **Modell**-delen og velg en Whisper-modell (`small` er en god balanse mellom hastighet/nøyaktighet)
4. Velg en stemme og juster TTS-hastigheten om nødvendig
5. *(Valgfritt)* I **Oversettelsesmotoren** velger du **Google** (standard), **MarianMT** (lokalt/frakoblet), **DeepL Free** eller **Ollama LLM** (lokalt, anbefalt for stemmedubbing)
6. *(Valgfritt)* Aktiver **Stemmekloning** (XTTS v2) og/eller **identifikasjon av personer som snakker (diarisering)**
7. *(Valgfritt)* Aktiver **Lip Sync** (Wav2Lip)
8. Klikk på **Start oversettelse**

**Fra YouTube (eller et annet støttet nettsted):**
1. Lim inn én eller flere nettadresser i **URL**-feltet (én per linje)
2. Konfigurer språk, modell og stemme som vanlig
3. Klikk **⬇ Last ned og oversett**

> yt-dlp støtter YouTube, Vimeo, Twitter/X, TikTok og [1000+ andre nettsteder](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Merknad om rettferdig bruk:** Nedlasting av videoer via yt-dlp anses som automatisert tilgang av plattformer som YouTube og kan bryte deres vilkår for bruk. Tung eller gjentatt bruk fra samme IP-adresse kan resultere i midlertidige blokkeringer (HTTP 429 / påloggingsfeil). Bruk en VPN eller roter IP-en din hvis du støter på nedlastingsfeil. Dette verktøyet er kun beregnet for personlig, ikke-kommersiell bruk. Videredistribusjon av oversatt innhold kan krenke opphavsretten - respekter alltid den opprinnelige skaperens rettigheter.

### Sanntidsoversettelse (undertekster og eksperimentell stemmedubbing)

Se en lokal fil eller en løst videolenke på forespørsel med oversatte undertekster og valgfri taleoversettelse. Bruk linjen under spilleren:

**Fra en lenke:**

1. Lim inn en lenke i **URL**-feltet
2. Angi kilde- og målspråk, velg en stemme og juster glidebryteren **Delay**
3. Velg **Dubbet stemme** og/eller **Teksting**
4. For å høre bare den oversatte stemmen, velg **Demp originallyd** før start (på italiensk: **Silenzia originale**, ved siden av undertekstboksen)
5. Klikk på **Oversett i sanntid** - koblingen er løst og oversettelsen starter

**Fra en lastet fil:** last inn en video i spilleren (Input -> Legg til, velg den), la URL-feltet stå tomt, velg de samme liveinnstillingene og klikk på **Oversett i sanntid**. En URL har prioritet når feltet ikke er tomt.

- **Motor:** MarianMT (frakoblet, standard), Google, DeepL eller Ollama. Talegjenkjenning (Whisper) kjører lokalt. Frakoblede modeller trenger en første nedlasting.
- **Forsinkelse:** på en fil i forsinket modus, hvor mange sekunder oversettelse som bufres før bildet fortsetter etter en pause (minst 8 s med stemme, 4 s med bare undertekster). Stopper bildet gang på gang, vokser bufferen med 4 s opp til 30 s, og linjen sier fra.
- **Stemmedubbing:** eksperimentell Edge-TTS-taleavspilling gjennom en andre mpv-forekomst. Den krever internettilgang og er atskilt fra batch-stemmekloning.
- **ElevenLabs-stemme:** valgfri, under Avanserte innstillinger > Stemmekloning > **ElevenLabs direktestemme**. Skriv inn API-nøkkelen, kontroller den, velg en modell som snakker målspråket og en stemme. Den oversatte teksten sendes til ElevenLabs (betales per tegn); nøkkelen blir i systemets nøkkelring. Svikter nøkkelen eller kvoten, fortsetter Edge-TTS. Den åpnes også fra knappen **ElevenLabs…** i sanntidslinjen, der linjen viser hvilken stemme dubbingen bruker.
  - Gratis ElevenLabs-abonnement (kontrollert 27. september 2026): via API-et fungerer bare standardstemmene (Roger, Sarah, George, River...), med 10 000 tegn i måneden og høyst 4 forespørsler samtidig. Vinduet merker stemmene som krever et betalt abonnement.
  - Stemmer fra ElevenLabs-biblioteket, klonede stemmer og flere tegn krever et betalt ElevenLabs-abonnement, kjøpt hos ElevenLabs etter deres egne priser og vilkår ([ElevenLabs pricing](https://elevenlabs.io/pricing)). VideoTranslatorAI er fortsatt gratis, er ikke tilknyttet ElevenLabs og trenger det ikke: Edge-TTS er den gratis standardstemmen.
  - Modeller for sanntid, første lyd etter omtrent: Flash v2.5 0,2 s, Turbo v2.5 0,2 s, v3 Conversational 0,4 s. Multilingual v2 (0,9 s) og v3 (1-2 s) låter fyldigere, men henger etter videoen; Turbo v2 og Flash v2 snakker bare engelsk.
  - Når ElevenLabs avviser en replikk (nøkkel, abonnement, stemme eller modell finnes ikke, språk, tegn brukt opp, for mange forespørsler), sier sanntidslinjen hvorfor, og loggen tar vare på ElevenLabs' egen melding.
- **Demp originallyd:** tilgjengelig både før start og under oversettelsen. Den demper hele det originale lydsporet, inkludert musikk og effekter, men lar den oversatte stemmen være hørbar. Det isolerer ikke personen som snakker i den originale lyden. Slå den av for å gjenopprette lydsporet; den tilbakestilles når live-økten avsluttes. Spillerens høyttalerknapp er den generelle dempingen, ikke denne uavhengige kontrollen.
- **Pause og søk:** videospillerkontroller er koblet til live-økten; ende-til-ende lydsynkronisering trenger fortsatt plattformspesifikke aksepttester.
- **Nåværende begrensninger:** kalibrering av lydtimingen og godkjenning på Windows gjenstår. Direktesendinger som fortsatt vokser støttes ikke; betegnelsen på direktemodusen betyr ikke at en pågående sending leses inn fortløpende.

For en lagret dubbet video, bruk **Last ned og oversett** / **Start oversettelse** i stedet for forhåndsvisningen i sanntid.

### Oversettelsesmotorblokker og VPN

To forskjellige blokkeringer kan skje, med forskjellige rettelser:

| Blokkér | Symptom | Fix |
|-------|---------|-----|
| **Last ned** (yt-dlp) | "Logg på for å bekrefte at du ikke er en bot", HTTP 429 | **VPN** / roter IP, eller vær logget på YouTube i nettleseren din (informasjonskapsler leses automatisk) |
| **Oversettelse** (Google gratis endepunkt) | "Google Translate kunne ikke oversette ... forespørselshastighet begrenset/blokkert" | Bruk **MarianMT** (frakoblet) eller **Ollama** (lokalt) - ingen forespørselsgrense. En VPN hjelper også. Batchflyten **faller automatisk tilbake til MarianMT** når Google blir blokkert. |

### Temaer og utseende

Klikk på tannhjulikonet i overskriften for å åpne **Innstillinger**:

- **Tema**: Automatisk (følger OS mørk/lys-modus), Graphite (standard), Slate, Light, Neon.
- **Skins**: Dex og Handheld (lommekonsoll, pikselskrift, tykke rammer), CRT og CRT Amber (fosforskjerm fra 80-tallet; videoen får også krumning og skannelinjer via en mpv-shader). Graphite er fortsatt standard.
- **Aksentfarge**: standard per tema, eller blå, blågrønn, fiolett, grønn, rav, rosa.
- **Tekststørrelse**: liten, normal, stor, ekstra stor.
- **Grensesnittspråk**: 26 språk.

Endringer gjelder umiddelbart, uten å starte på nytt, og lagres i konfigurasjonsfilen (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Gjenopprett standardinnstillinger** bringer tilbake Graphite-temaet, standardaksenten, normal tekststørrelse og standardrekkefølgen til innstillingspanelene.

### Kommandolinje

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Alle alternativer:**

| CLI-alternativ | Beskrivelse | Standard |
|------|-------------|---------|
| `--lang-source` | Kildespråk (`auto` for automatisk gjenkjenning) | `auto` |
| `--lang-target` | Målspråkkode (f.eks. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS stemmenavn | auto |
| `--model` | Whisper-modell (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS-hastighetsjustering (f.eks. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` eller `deepl` | `google` |
| `--deepl-key` | DeepL Free API-nøkkel | - |
| `--diarize` | Aktiver identifikasjon av personer som snakker (diarisering) (pyannote) | - |
| `--hf-token` | HuggingFace token for diarisering | - |
| `--lipsync` | Bruk Wav2Lip lip sync etter stemmedubbing | - |
| `--subs-only` | Generer kun `.srt`, hopp over stemmedubbing | - |
| `--no-subs` | Hopp over `.srt` generasjon | - |
| `--no-demucs` | Hopp over stemme/musikk-separasjon | - |
| `--output` / `-o` | Utdatafilbane | auto |
| `--output-dir` | Mappe for oversatte filer (ett sted, Windows og Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Behandle flere filer | - |
| `--voicebox` | Kloner stemmen via en kjørende Voicebox-server | - |
| `--voicebox-url` | Voicebox-adresse | `http://127.0.0.1:17493` |
| `--voicebox-engine` | Voicebox-motor (`chatterbox`, `qwen`, ...) | `chatterbox` |

### integrasjonstester med ekte modeller

Standard testpakken unngår nedlastinger av ekte modeller og langt GPU-arbeid. Slik kjører du empiriske kontroller for den installerte lokale stabelen:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Disse sjekkene validerer ekte Wav2Lip-import, Torch CUDA-tilgjengelighet, Ollama-demon-tilgjengelighet og faster-Whisper på syntetisk tale. De mislykkes med vilje eller hopper over når den lokale driveren/demonen/modellen ikke er klar.

**Eksempler:**

```bash
# Oversett italiensk video til engelsk med lokale MarianMT
# (laster ned ~298 MB-modell ved første gangs bruk, deretter helt offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Oversett med stemmekloning + identifikasjon av personer som snakker (diarisering)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Oversett med leppesynkronisering
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Bare undertekster (ingen stemmedubbing)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper-modeller

| Modell | Størrelse | Hastighet | Nøyaktighet |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` er en destillert versjon av `large-v3` (4 dekoderlag vs 32) - nesten stor kvalitet med omtrent `medium`-laghastighet. Anbefalt standard på en moderne GPU når transkripsjonshastighet er viktig; Kvalitetsfallet på flerspråklig materiale er mindre.

> Modeller lastes ned automatisk ved første gangs bruk.

> Usikker på hvilken modell som passer PC-en din? Åpne **Modeller for denne PC-en** i modellinnstillingene: den anbefaler en ut fra maskinvaren og kan måle den.

## Frittstående modul CLI-er

Den modulære pakken viser fire brukervendte verktøy som kan påkalles direkte uten å starte hele pipelinen:

```bash
# Pre-flight en video for ansikt tilstedeværelse (Wav2Lip vil hoppe over hvis fraværende).
python3 -m videotranslator.face_detector path/to/video.mp4
# utgang 0 = ansikt til stede, utgang 1 = ingen ansikt

# Analyser en *_metrics.csv produsert av build_dubbed_track.
# Rapporterer P50/P75/P90/P95 av pre_stretch_ratio, nedbryting av hørbarhetsbånd,
# bruk av strekkmotorer og de verste avvikene i topp-N med målteksten.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Rens tekst for TTS (skriver om kolon, semikolon, ellipser, bindestreker).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Estimer stemmedubbingsvansker fra en .srt- eller .json-segmentfil FØR du kjører TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Hvert verktøy har `-h`/`--help` for fulle alternativer. De er selvstendige og gjenbruker de samme modulene som pipeline for stemmedubbing er avhengig av, slik at utdataene deres forblir i samsvar med kjøretiden.

## Lisens

MIT

### Tredjepartskomponenter

Lagringskoden er MIT. Installatørene laster ned komponentene nedenfor fra sine egne kilder ved installasjonstidspunktet; prosjektet omdistribuerer dem ikke.

- **libmpv** (https://github.com/mpv-player/mpv), motoren til den integrerte videospilleren. Windows: LGPL bygget av zhongfly (https://github.com/zhongfly/mpv-winbuild) prøves først; en festet GPL bygget av shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) er reserven. `mpv-runtime\BUILD.txt` registrerer kilden, lisenssmaken og mpv-commit, og lisensteksten sitter ved siden av DLL-en. Linux: distribusjonspakken (`libmpv2`, `libmpv1`, `mpv-libs` eller `mpv`).
- **FFmpeg** inne i libmpv (LGPL eller GPL, etter libmpv-bygget).
- **python-mpv** (`mpv` på PyPI), GPLv2+ eller LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), brukt av Windows-installasjonsprogrammet for å pakke ut libmpv og slettet etterpå.
- **Vulkan-laster** (Khronos, MIT og Apache-2.0), lastet ned på Windows kun når `vulkan-1.dll` mangler.
- **edge-tts** (LGPLv3), brukt av pipeline for stemmedubbing.
- **MarianMT-modeller** (Helsinki-NLP), lastet ned fra Hugging Face Hub ved første gangs bruk under egne lisenser (Apache-2.0 for `opus-mt`-modellene, CC-BY-4.0 for `opus-mt-tc-big`).
- **Voicebox** (MIT, https://github.com/jamiepine/voicebox), valgfritt, installeres separat av brukeren; motorene har egne lisenser (Chatterbox MIT med lydvannmerke, TADA-vekter under Llama 3.2 Community License).
- **ElevenLabs** (https://elevenlabs.io), valgfri nettjeneste som brukes med brukerens egen konto og API-nøkkel på tjenestens egne vilkår.
- Skrifttypene **Pixelify Sans** og **VT323** (SIL Open Font License 1.1), som brukes av skins: de eneste tredjepartsfilene i depotet, i `assets/fonts` ved siden av lisenstekstene.
