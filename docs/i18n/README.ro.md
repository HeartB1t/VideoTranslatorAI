# 🎬 Video Translator AI

[Engleză](../../README.md) | [Toate traducerile](README.md)

**Citiți această pagină în:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Instrument de dublare a vocii video bazat pe inteligență artificială, care transcrie, traduce și redublează automat videoclipurile în 26 de limbi, cu opțiuni de procesare locale și fără chei API necesare în mod implicit. Whisper recunoașterea vorbirii rulează local; Edge-TTS, Google Translate și DeepL necesită o conexiune la internet. Funcțiile opționale (DeepL, identificarea persoanelor care vorbesc (diarizare)) pot necesita o cheie API sau un token de acces.

> **v2.0** - pachet modular, traducere locală Ollama, orchestrare a profilului de calitate, metadate Python instalabile și teste de integrare opt-in cu modele reale. Consultați [Versiunile GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases) și istoricul de comitere pentru lista completă a modificărilor.

## Cum funcționează

1. **Transcriere** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcrie sunetul (accelerat GPU)
2. **Separare voce/muzică** - [Demucs](https://github.com/facebookresearch/demucs) izolează vocea de muzica de fundal
3. **Traducere** - MarianMT (local, offline), Google Translate, DeepL Free sau **Ollama LLM** (Qwen3, traduceri concise compatibile cu slotul)
4. **identificarea persoanelor care vorbesc (diarizare)** *(opțional)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifică cine vorbește în fiecare segment
5. **dublarea vocii** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ voci) sau [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (clonarea vocii, pentru fiecare vorbitor din conversație)
6. **Mixing** - voce dublată amestecată cu muzică de fundal originală
7. **Normalizare** - audio final normalizat la -23 LUFS (standard de difuzare EBU R128)
8. **Lip Sync** *(opțional)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) sincronizează mișcările gurii cu sunetul dublat

## Caracteristici

- 🖥️ GUI tematic (Tkinter) - nu este nevoie de linie de comandă; Teme Graphite, Slate, Light și Neon, culori de accent, dimensiunea textului și panouri de setări pe care le puteți reordona trăgând
- 🌍 **26 de limbi țintă** cu mai multe voci în fiecare limbă
- 🌐 **UI în 26 de limbi** - interfața în sine se adaptează limbii dvs
- 🎬 **Suport YouTube și URL** - inserați orice link YouTube și traduceți direct (produs de yt-dlp)
- ▶️ **Player video integrat** (libmpv/mpv) - comenzi de transport cu coduri de culoare, playlist, audio original A/B vs dublat, comutare subtitrări, instantaneu, ecran complet, dosar deschis
- ⏱️ **Traducere în timp real** - urmăriți un fișier local sau un link video la cerere rezolvat cu subtitrări traduse și un glisor de întârziere în stil YouTube; motoare MarianMT / Google / DeepL / Ollama. Dublarea vocală experimentală utilizează Edge-TTS și oa doua instanță mpv. Gestionarea suprapunerii vocale și acceptarea audio reală/Windows rămân în desfășurare; transmisiunile live în creștere nu sunt încă acceptate. Vedeți [starea implementării live](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Separare voce/muzică prin Demucs (păstrează muzica de fundal)
- 🔇 **Dezactivați sunetul original**, disponibil înainte și în timpul traducerii live, reduce la tăcere coloana sonoră a videoclipului, păstrând vocea tradusă audibilă. Dezactivați-l pentru a restabili sunetul original; se resetează când se termină sesiunea live.
- 🧠 **MarianMT** - traducere neuronală complet locală, offline (Helsinki-NLP, fără limite de rată de solicitare, fără cheie API)
- 🤖 **Traducere Ollama LLM** *(nou în v2.0)* - LLM local (Qwen3, Llama, Mistral) care produce traduceri concise compatibile cu slotul pentru dublarea vocală naturală, auto-detectează/instalează/pornește/extrage modelul la prima utilizare
- 🎙️ **Clonarea vocii** - Coqui XTTS v2 clonează persoana care vorbește cu vocea audio originală în limba țintă (model de ~1,8 GB), cu viteză de adaptare pe segment și reîncercare cu mai multe semințe asupra halucinațiilor
- 👥 **identificarea persoanelor care vorbesc (diarizarea)** - pyannote-audio 3.1 identifică mai multe persoane care vorbesc; XTTS clonează fiecare voce separat
- 💋 **Lip Sync** - Wav2Lip GAN sincronizează mișcările gurii cu sunetul dublat (model de ~416 MB)
- 🔊 **Normalizare audio** - normalizare automată a sunetului -23 LUFS (EBU R128)
- ✏️ Editor de subtitrări - revizuiți și corectați subtitrările înainte de dublarea vocală
- 📦 Procesare în lot - traduceți mai multe videoclipuri sau adrese URL simultan
- ⚡ Accelerarea GPU prin CUDA (reduce automat la CPU)
- 📄 Export opțional pentru subtitrare `.srt`
- 🔁 **DeepL Free** motor de traducere (opțional - 500.000 de caractere/lună, necesită cheia API gratuită)
- 🔧 **Auto-instalare** - pachetele Python și ffmpeg lipsă sunt instalate automat la prima lansare

## Limbi acceptate

arabă, chineză, cehă, daneză, engleză, finlandeză, franceză, germană, greacă, hindi, maghiară, indoneziană, italiană, japoneză, coreeană, norvegiană, poloneză, portugheză, română, rusă, spaniolă, suedeză, turcă, ucraineană, vietnameză

## Catalogul vocal

Catalogul vocal Edge-TTS este definit în `LANGUAGES` lângă partea de sus a `video_translator_gui.py`. Dicționarul respectiv este sursa adevărului pentru numele limbii țintă, butoanele radio pentru voce GUI și vocea de rezervă CLI atunci când `--voice` este omis.

Notele Claude/proiect-întreținere reflectă această locație în `CLAUDE.md` sub **Voice Catalog Source Of Truth**, astfel încât viitorii agenți de cod să știe unde să actualizeze vocile și unde README indică utilizatorii.

## Motoare de traducere

| Motor | Configurare | Limite | Calitate |
|--------|-------|--------|---------|
| **Google Translate** *(implicit)* | Niciuna | Scraping neoficial - poate fi redus la videoclipurile mari | ★★★★ |
| **MarianMT** | Niciuna - descarcă ~298 MB per pereche de limbi la prima utilizare | Nici unul - complet offline după descărcare | ★★★★ |
| **DeepL Free** | Cheie API gratuită la [deepl.com](https://www.deepl.com/pro-api) | 500.000 de caractere/lună | ★★★★★ |
| **Ollama LLM** *(recomandat pentru dublarea vocală - nou în v2.0)* | Instalat automat la prima utilizare (~1 GB Ollama + 5 GB model) | Nici unul - complet local | ★★★★★ |

> **MarianMT** folosește modele [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP), stocate în cache local după prima descărcare. Necesită limba sursă explicită (detecția automată nu este acceptată - selectați manual limba sursă). Pachetele Python necesare (`sacremoses`, `sentencepiece`) sunt instalate automat la prima selecție dacă lipsesc.

> **Ollama LLM** *(nou în v2.0)* este motorul recomandat pentru dublarea vocală, deoarece produce traduceri conștiente de intervalul de timp țintă. În cazul în care MarianMT se traduce literal și produce italiană / spaniolă / franceză cu aproximativ 25% mai mult decât engleză (forțând compresia audio audibilă pe TTS), LLM este solicitat să păstreze fiecare segment concis și natural pentru livrarea vorbită, realizând un raport tipic de caractere de 0,85-0,95 față de sursă. Modelul implicit este `qwen3:8b` (5,2 GB pe disc, ~6 GB VRAM); `qwen3:4b` (~3 GB) este opțiunea ușoară, `qwen3:14b` cea de calitate superioară. Conducta detectează automat binarul Ollama, îl instalează automat prin intermediul programului de instalare oficial la prima utilizare (cu pop-up de consimțământ), pornește demonul și trage modelul ales - nu este necesară configurarea manuală. Comută automat la Google Translate dacă lipsește ceva.

## Clonarea vocii (XTTS v2)

Când este activată, aplicația extrage vocea vorbitorului din videoclipul original și o folosește ca referință pentru a clona vocea în limba țintă.

- Limbi acceptate: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Pentru celelalte 9 limbi, Edge-TTS este utilizat automat ca alternativă
- Model (~1,8 GB) descărcat automat la prima utilizare pe `~/.local/share/tts/`
- **Referință filtrată prin VAD** (v1.4): 10-15 s de vorbire continuă selectată din audio original prin [silero-vad](https://github.com/snakers4/silero-vad) pentru o calitate mai bună a clonării vocii
- **Viteza de generare** configurabilă (`xtts_speed`, implicit `1.25`): valorile mai mari reduc artefactele de compresie audio post-procesare atunci când textul tradus este mai lung decât slotul sursă. Acordați prin `~/.config/videotranslatorai/config.json` sau CLI `--xtts-speed`
- Rulează pe CUDA sau CPU

## identificarea persoanelor care vorbesc (diarizare) (pyannote-audio)

Când este activată, aplicația identifică cine vorbește în fiecare segment. În combinație cu Voice Cloning, vocea fiecărui vorbitor este clonată separat - ideală pentru interviuri, podcasturi și videoclipuri cu mai multe persoane.

- Necesită un [token HuggingFace](https://huggingface.co/settings/tokens) gratuit (înregistrare unică)
- **Token stocat în siguranță** (v1.4) prin breloul de chei al sistemului de operare: Windows Credential Manager, macOS Keychain, Linux Secret Service. Migrare automată de la stocarea anterioară JSON de text simplu
- După prima descărcare, funcționează complet offline
- Model: `pyannote/speaker-diarization-3.1`

## Sincronizare buzelor (Wav2Lip)

Când este activată, aplicația aplică Wav2Lip GAN pentru a sincroniza mișcările gurii subiectului cu sunetul dublat - persoana pare să vorbească limba tradusă.

- Model (~416 MB) și repo clonat automat la prima utilizare în `~/.local/share/wav2lip/`
- Rulează pe CUDA (recomandat) sau CPU
- Mărește semnificativ timpul de procesare
- Funcționează cel mai bine pe videoclipuri cu o singură față, clar vizibilă

## Cerințe

- Python 3.10+ (instalatorul Windows prevede automat 3.11.9)
- Windows 10/11 (x64), Linux sau macOS
- **GPU NVIDIA recomandat** - consultați tabelul GPU de mai jos
- 20 GB spațiu liber pe disc pentru o instalare completă (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg și toate pachetele Python sunt instalate automat** la prima lansare dacă lipsesc. Nu este necesară configurarea manuală.

**Dependență opțională de sistem** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Atunci când este instalat, este folosit pentru întinderea timpului de păstrare a tonului în banda de calitate controlată de profil (implicit 1,15-1,50, până la 1,65 pentru conținutul hard), eliminând efectul rezidual de „chipmunk” pe vocile XTTS clonate. Conducta rulează neschimbată fără ea (return automat la ffmpeg `atempo`). Profilurile de calitate preferă acum reîncercări extra scurte de traducere decât accelerarea extremă a sunetului.

### Suport GPU

Conducta utilizează cinci componente accelerate de GPU (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). Acoperirea GPU nu este uniformă între furnizori:

| GPU | Windows | Linux | Note |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx sau mai nou, driver CUDA 12.4) | ✅ accelerație completă | ✅ accelerație completă | **Recomandat.** Toate cele 5 componente rulează pe GPU. |
| **AMD** (Radeon) | ⚠️ incomplet (DirectML nu acceptă XTTS și faster-whisper) | ⚠️ parțial (ROCm funcționează pentru Demucs/XTTS/pyannote, dar faster-whisper acceptă doar CUDA) | Funcționează, dar transcrierea Whisper rămâne pe CPU și domină timpul total. |
| **Intel Arc** | ⚠️ Suport imatur PyTorch XPU | ⚠️ la fel | Nu a fost testat. |
| **Niciuna (numai CPU)** | ✅ funcționează | ✅ funcționează | Așteptați-vă la **10-20× mai lent** decât în timp real. Un clip de 5 minute poate dura peste 50 de minute doar pentru a transcrie cu Whisper large-v3. |

**VRAM NVIDIA recomandat:**

| VRAM | Plăci grafice uzuale | Experiență |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Utilizabil, nu poate rula XTTS + Wav2Lip simultan |
| 8 GB | RTX 3060 Ti, 4060 | Conductă completă, fără marjă |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Recomandat - confortabil** |
| 24 GB | RTX 3090, 4090 | Capacitate de rezervă pentru loturi mari |

## Instalare

### Windows

1. Clonează sau descarcă acest depozit
2. Faceți clic dreapta pe `setup_windows.bat` → **Run ca administrator** → meniul arată `[1] Install`
3. Instalatorul automat:
   - Instalează Python 3.11 dacă nu este prezent (la nivelul întregului sistem)
   - Instalează Git for Windows dacă nu este prezent
   - Instalează toate dependențele Python (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps etc.)
   - Descărcă și instalează ffmpeg
   - Instalează playerul video integrat (python-mpv plus o versiune libmpv în `mpv-runtime`). Pasul este opțional: dacă nu reușește, totul funcționează, iar panoul playerului explică ce lipsește
   - Creează o **comandă rapidă Public Desktop** (vizibilă pentru fiecare cont Windows de pe computer)

> Programul de instalare este **multi-utilizator**: totul este instalat la nivelul întregului sistem sub `%ProgramFiles%\VideoTranslatorAI` și orice utilizator Windows de pe computer găsește comanda rapidă gata de funcționare. Instrumentele de compilare VS C++ **nu mai sunt necesare** - furca `coqui-tts` întreținută oferă pachete de roți Python precompilate.

### Linux / macOS

```bash
# Clonează repo-ul
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Opțional: instalați stiva NVIDIA CUDA 12.4 PyTorch testată în față
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Opțional: preinstalați toate pachetele de rulare Python în loc să lăsați GUI
# instalați pachetele lipsă la prima rulare
pip install --break-system-packages -r requirements.txt

# Opțional: playerul video integrat (libmpv din distribuție, python-mpv din PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Opțional: instalați proiectul ca pachet Python editabil
pip install --break-system-packages --no-deps -e .

# Lansați de la sursă
python video_translator_gui.py

# Sau, după instalarea editabilă/pachet
videotranslatorai
videotranslatorai --preflight
```

> La prima lansare, interfața grafică detectează orice pachete lipsă (faster-whisper, Demucs, Edge-TTS etc.) și le instalează automat, transmițând rezultatul în fereastra de jurnal. ffmpeg este, de asemenea, instalat automat prin `apt-get` / `dnf` / `pacman` (Linux) sau descărcat de pe GitHub (Windows).

> Antetul arată o insignă **Jucător**. Când libmpv sau python-mpv lipsește, panoul din stânga spune ce lipsește și oferă **Instalare player**: pe Linux folosește managerul de pachete prin pkexec (apoi `sudo -n`) și arată comanda manuală când niciunul nu funcționează; pe Windows se întreabă înainte de a descărca libmpv pentru utilizatorul actual (aproximativ 32 MB).

### Profiluri de cerințe

| Fișier | Scop |
|------|---------|
| `requirements.txt` | Instalare completă, compatibilă cu versiunea anterioară. |
| `requirements-core.txt` | Pachetele de conducte implicite utilizate de GUI/CLI. |
| `requirements-optional.txt` | XTTS, tokenizer MarianMT, diarizare, VAD, breloc. |
| `requirements-wav2lip.txt` | Timp de rulare Wav2Lip și stivă de detectare a feței (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Stiva PyTorch testată cu roți NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Player video integrat: python-mpv (necesită libmpv din sistem sau din programul de instalare Windows). |
| `requirements-dev.txt` | Dependențe ușoare utilizate de testele CI/unități. |

## Dezinstalează

### Windows

Rulați `setup_windows.bat` (clic dreapta → **Run ca administrator**) și alegeți `[3] Uninstall` din meniu. Sunt oferite trei submoduri de dezinstalare:

| Modul | Este necesar un administrator | Domeniul de aplicare |
|------|----------------|-------|
| **[1] Dezinstalare completă - un clic** | ✅ | Elimină folderul aplicației, scurtătura Public Desktop, ffmpeg din PATH-ul mașinii, cache-ul modelului HF al fiecărui utilizator (Whisper/XTTS) și configurația (`HF token`) și toate pachetele Python AI instalate de instalator. La sfârșit, întreabă și (înscrieți-vă) dacă să dezinstalați în mod silențios **Python 3.11** și **Git for Windows** prin șirurile lor de dezinstalare silențioasă a registrului. |
| **[2] Numai utilizatorul actual** | ❌ | Elimină numai configurația VTAI a utilizatorului care rulează, memoria cache HF/XTTS și instalarea moștenită per utilizator. **Lasă intactă instalarea la nivelul întregului sistem**, astfel încât alte conturi Windows de pe computer să poată continua să folosească aplicația. |
| **[3] Personalizat - granular** | ✅ pentru elementele de sistem, ❌ pentru articolele utilizator | Întrebare Y/N pentru fiecare categorie: folderul aplicației, comanda rapidă, PATH de sistem, instalări vechi per utilizator, configurări și memorii cache per utilizator, apoi grupuri de pachete Python (TTS, PyTorch, Whisper+ctranslate2, Demucs, dependențe Wav2Lip, pyannote și utilitare ale fluxului de procesare), iar la final eliminarea opțională a Python 3.11 și Git. |

**Nu a fost niciodată eliminat automat:** Instrumente de compilare Visual Studio C++ (dacă sunt prezente din versiuni mai vechi). Folosiți *Aplicații și funcții* în Setările Windows pentru a le elimina manual dacă doriți.

### Linux / macOS

Fără dezinstalare dedicată - eliminați manual:

```bash
# Pachetele Python instalate de instalatorul automat al GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Datele utilizatorului și cache-urile modelului
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (teme, ordinea panoului, setări)
rm -f  ~/.videotranslatorai_config.json     # configurație moștenită a versiunilor <= 1.9, dacă există
```

## Utilizare

### Diagnosticare

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Rulează diagnosticarea mediului local fără a începe traducerea sau a instala nimic. `--preflight-lipsync` tratează pachetele de față Wav2Lip după cum este necesar, ceea ce este util înainte de a activa **Lip Sync**. GUI expune aceeași verificare de bază din butonul **Diagnosticare** al panoului de jurnal. `--preflight-player` tratează playerul video integrat (python-mpv și libmpv încărcat) după cum este necesar. `python -m videotranslator.libmpv_runtime check` probează singur libmpv (ieșirea 0 gata, 2 indisponibilă).

### GUI

```bash
python video_translator_gui.py
```

**Aspect:** setările de traducere în lot sunt disponibile în coloana din dreapta, sub forma unui teanc de panouri de setări: **Intrare**, **Traducere**, **Profil flux de lucru**, **Start** și secțiunile avansate pliabile (model, motor de traducere, audio, clonare vocală, sincronizare buzelor, diarizare, opțiuni, cuvinte calde). Zona mare din stânga este **playerul video integrat** (transport, playlist, audio A/B original vs dublat, subtitrări, instantanee, ecran complet), cu bara de **traducere în timp real** dedesubt. Trageți un card după titlu sau de mânerul **≡** pentru a-l muta în sus sau în jos pe coloană; comanda este salvată (`ui_panel_order`) și restabilită la următoarea pornire. Panoul de jurnal din partea de jos poate fi ascuns cu **Ascunde jurnal**. La pornire, fereastra se deschide centrată pe monitorul curent (cel de sub indicator) și maximizată, astfel încât se comportă bine într-o configurație cu mai multe monitoare.

**Comenzile playerului video video:** pictogramele folosesc culori funcționale consecvente în fiecare temă, independent de culoarea de accent selectată:

| Control | Culoare |
|---------|--------|
| Redați videoclipul | verde |
| Pauză (înlocuiește Redarea în timpul redării) | chihlimbar |
| Opriți redarea | Roșu coral |
| Anterior / înapoi 10 s / înainte 10 s / următorul | Albastru |
| Instantaneu | violet |
| Deschide folderul | Aur |

Trecerea cu mouse-ul adaugă un fundal subtil colorat. Comenzile indisponibile sunt neutre; Navigarea în lista de redare rămâne utilizabilă după oprire. Sfaturile instrumentelor și indicatorii de focalizare de la tastatură rămân disponibili, așa că culoarea nu este singura modalitate de a identifica acțiunile.

**Din fișiere locale:**
1. Faceți clic pe **Adăugați** pentru a selecta unul sau mai multe fișiere video
2. Alegeți limba sursă și țintă
3. Deschideți secțiunea **Model** și selectați un model Whisper (`small` este un echilibru bun între viteză/precizie)
4. Alegeți o voce și ajustați viteza TTS dacă este necesar
5. *(Opțional)* În **Motorul de traducere**, selectați **Google** (implicit), **MarianMT** (local/offline), **DeepL Free** sau **Ollama LLM** (local, recomandat pentru dublarea vocală)
6. *(Opțional)* Activați **Clonarea vocii** (XTTS v2) și/sau **identificarea persoanelor care vorbesc (diarizare)**
7. *(Opțional)* Activați **Lip Sync** (Wav2Lip)
8. Faceți clic pe **Începe traducerea**

**De pe YouTube (sau orice site acceptat):**
1. Inserați una sau mai multe adrese URL în câmpul **URL** (una pe linie)
2. Configurați limba, modelul și vocea ca de obicei
3. Faceți clic pe **⬇ Descărcați și traduceți**

> yt-dlp acceptă YouTube, Vimeo, Twitter/X, TikTok și [1000+ alte site-uri](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Notă de utilizare loială:** Descărcarea videoclipurilor prin yt-dlp este considerată acces automat de către platforme precum YouTube și poate încălca Termenii și condițiile acestora. Utilizarea intensă sau repetată de la aceeași adresă IP poate duce la blocări temporare (HTTP 429 / erori de conectare necesare). Utilizați un VPN sau rotiți-vă IP-ul dacă întâmpinați erori de descărcare. Acest instrument este destinat exclusiv utilizării personale, necomerciale. Redistribuirea conținutului tradus poate încălca drepturile de autor - respectați întotdeauna drepturile creatorului original.

### Traducere în timp real (subtitrări și dublare vocală experimentală)

Vizionați un fișier local sau un link video la cerere rezolvat cu subtitrări traduse și traducere vocală opțională. Folosește bara de sub player:

**De pe un link:**

1. Inserați un link în câmpul **URL**
2. Setați limba sursă și țintă, alegeți o voce și reglați glisorul **Întârziere**
3. Selectați **Voce dublată** și/sau **Subtitrări**
4. Pentru a auzi doar vocea tradusă, selectați **Opriți sunetul original** înainte de a începe (în italiană: **Silenzia originale**, lângă caseta de selectare pentru subtitrare)
5. Faceți clic pe **Traduceți în timp real** - linkul este rezolvat și începe traducerea

**Din un fișier încărcat:** încărcați un videoclip în player (Intrare -> Adăugați, apoi selectați-l), lăsați câmpul URL gol, alegeți aceleași setări live și faceți clic pe **Traduceți în timp real**. O adresă URL are prioritate atunci când câmpul nu este gol.

- **Motor:** MarianMT (offline, implicit), Google, DeepL sau Ollama. Recunoașterea vorbirii (Whisper) rulează local. Modelele offline au nevoie de o descărcare inițială.
- **Dublare vocală:** redare experimentală a vorbirii Edge-TTS printr-o a doua instanță mpv. Necesită acces la internet și este separat de clonarea vocală în lot.
- **Dezactivați sunetul original:** disponibil atât înainte de începere, cât și în timpul traducerii. Opreste la tăcere întreaga coloană sonoră originală, inclusiv muzica și efectele, dar lasă vocea tradusă audibilă. Nu izolează persoana care vorbește în audio original. Dezactivați-l pentru a restabili coloana sonoră; se resetează când se termină sesiunea live. Butonul difuzorului jucătorului este sunetul general, nu acest control independent.
- **Pauză și caută:** comenzile playerului video sunt conectate la sesiunea live; sincronizarea audio end-to-end necesită încă teste de acceptare specifice platformei.
- **Limite curente:** gestionarea suprapunerii/decolorării clipurilor, calibrarea temporizării audio și acceptarea Windows rămân deschise. Transmisiunile live în creștere nu sunt încă acceptate; eticheta mod live nu implică suport pentru ingerarea unei emisiuni pe măsură ce crește. Consultați [starea implementării și lucrările rămase](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Pentru un videoclip dublat salvat, utilizați **Descărcați și traduceți** / **Începeți traducerea** în loc de previzualizarea în timp real.

### Blocuri de motor de traducere și VPN

Se pot întâmpla două blocuri diferite, cu remedieri diferite:

| Blocați | Simptom | Fix |
|-------|---------|-----|
| **Descărcare** (yt-dlp) | „Conectează-te pentru a confirma că nu ești un bot”, HTTP 429 | **VPN** / rotiți IP, sau fiți conectat la YouTube în browser (cookie-urile sunt citite automat) |
| **Traducere** (punct final gratuit Google) | „Google Translate nu a putut traduce... rata de solicitare limitată/blocata” | Utilizați **MarianMT** (offline) sau **Ollama** (local) - fără limită de solicitare. Un VPN ajută și el. Fluxul batch acum **revine automat la MarianMT** când Google este blocat. |

### Teme și aspect

Faceți clic pe pictograma roată din antet pentru a deschide **Setări**:

- **Temă**: automată (urmează modul întuneric/luminos al sistemului de operare), Graphite (implicit), Slate, Light, Neon.
- **Culoare de accent**: implicit pentru fiecare temă sau albastru, ceai, violet, verde, chihlimbar, trandafir.
- **Dimensiunea textului**: mic, normal, mare, foarte mare.
- **Limba interfeței**: 26 de limbi.

Modificările se aplică imediat, fără repornire și sunt salvate în fișierul de configurare (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Restabilire setări implicite** readuce tema Graphite, accentul implicit, dimensiunea normală a textului și ordinea implicită a panourilor de setări.

### Linia de comandă

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Toate opțiunile:**

| opțiunea CLI | Descriere | Implicit |
|------|-------------|---------|
| `--lang-source` | Limba sursă (`auto` pentru detectarea automată) | `auto` |
| `--lang-target` | Codul limbii țintă (de exemplu, `it`, `fr`, `de`) | `it` |
| `--voice` | Numele vocal Edge-TTS | auto |
| `--model` | Model Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Ajustarea vitezei TTS (de exemplu, `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` sau `deepl` | `google` |
| `--deepl-key` | DeepL Free cheie API | - |
| `--diarize` | Activați identificarea persoanelor care vorbesc (diarizare) (pyannote) | - |
| `--hf-token` | Jeton HuggingFace pentru diarizare | - |
| `--lipsync` | Aplicați sincronizarea buzelor Wav2Lip după dublarea vocală | - |
| `--subs-only` | Generați numai `.srt`, omiteți dublarea vocală | - |
| `--no-subs` | Omiteți generația `.srt` | - |
| `--no-demucs` | Omiteți separarea voce/muzică | - |
| `--output` / `-o` | Calea fișierului de ieșire | auto |
| `--output-dir` | Dosar pentru fișierele traduse (un singur loc, Windows și Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Procesați mai multe fișiere | - |

### teste de integrare cu modele reale

Suita de testare implicită evită descărcările reale de model și munca îndelungată a GPU-ului. Pentru a rula verificări empirice de înscriere pentru stiva locală instalată:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Aceste verificări validează importurile reale Wav2Lip, disponibilitatea Torch CUDA, disponibilitatea demonului Ollama și faster-Whisper pentru vorbirea sintetică. Ele eșuează în mod intenționat sau opresc atunci când starea driverului/demonului/modelului local nu este pregătită.

**Exemple:**

```bash
# Traduceți videoclipul italian în engleză cu MarianMT local
# (descărcă modelul de ~298 MB la prima utilizare, apoi complet offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Traduceți cu clonarea vocii + identificarea persoanelor care vorbesc (diarizare)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Traduceți cu sincronizarea buzelor
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Doar subtitrări (fără dublare vocală)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Modele Whisper

| Model | Dimensiune | Viteza | Precizie |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` este o versiune distilata a `large-v3` (4 straturi de decodor vs 32) - calitate aproape mare la viteza de nivel aproximativ `medium`. Implicit recomandat pe un GPU modern atunci când viteza de transcriere contează; scăderea calității materialelor multilingve este minoră.

> Modelele sunt descărcate automat la prima utilizare.

## CLI pentru modul autonom

Pachetul modular expune patru instrumente orientate spre utilizator care pot fi invocate direct fără a lansa întreaga conductă:

```bash
# Pre-flight un videoclip pentru prezența feței (Wav2Lip ar omite dacă este absent).
python3 -m videotranslator.face_detector path/to/video.mp4
# ieșire 0 = față prezentă, ieșire 1 = fără față

# Analizați un *_metrics.csv produs de build_dubbed_track.
# Rapoarte P50/P75/P90/P95 din pre_stretch_ratio, defalcarea benzii de audibilitate,
# extinde utilizarea motorului și top-N cele mai rele valori aberante cu textul lor țintă.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Dezinfectează textul pentru TTS (rescrie două puncte, punct și virgulă, puncte suspensie, liniuțe).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Estimați dificultatea de dublare vocală dintr-un fișier cu segmente .srt sau .json ÎNAINTE de a rula TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Fiecare instrument are `-h`/`--help` pentru opțiuni complete. Sunt autonome și reutiliza aceleași module pe care se bazează conducta de dublare vocală, astfel încât rezultatul lor rămâne în concordanță cu timpul de rulare.

## Licență

MIT

### Componente terțe

Codul depozitului este MIT. Instalatorii descarcă componentele de mai jos din propriile surse în momentul instalării; proiectul nu le redistribuie.

- **libmpv** (https://github.com/mpv-player/mpv), motorul playerului video integrat. Windows: LGPL construit de zhongfly (https://github.com/zhongfly/mpv-winbuild) este încercat mai întâi; o GPL fixată construită de shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) este soluția de rezervă. `mpv-runtime\BUILD.txt` înregistrează sursa, aroma licenței și comiterea mpv, iar textul licenței se află lângă DLL. Linux: pachetul de distribuție (`libmpv2`, `libmpv1`, `mpv-libs` sau `mpv`).
- **FFmpeg** în interiorul libmpv (LGPL sau GPL, după compilarea libmpv).
- **python-mpv** (`mpv` pe PyPI), GPLv2+ sau LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), folosit de programul de instalare Windows pentru a extrage libmpv și șters ulterior.
- **Încărcător Vulkan** (Khronos, MIT și Apache-2.0), descărcat pe Windows numai când `vulkan-1.dll` lipsește.
- **edge-tts** (LGPLv3), utilizat de canalul de dublare vocală.
- **Modele MarianMT** (Helsinki-NLP), descărcate de la Hugging Face Hub la prima utilizare sub propriile licențe (Apache-2.0 pentru modelele `opus-mt`, CC-BY-4.0 pentru `opus-mt-tc-big`).
