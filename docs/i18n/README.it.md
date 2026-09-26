# 🎬 Video Translator AI

[Inglese](../../README.md) | [Tutte le traduzioni](README.md)

**Leggi questa pagina in:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Strumento di doppiaggio video basato sull'intelligenza artificiale che trascrive, traduce e ridoppia automaticamente i video in 26 lingue, con opzioni di elaborazione locale e nessuna chiave API richiesta per impostazione predefinita. Il riconoscimento vocale Whisper viene eseguito localmente; Edge-TTS, Google Translate e DeepL richiedono una connessione Internet. Le funzionalità opzionali (DeepL, diarizzazione dei parlanti) possono richiedere una chiave API o un token di accesso.

> **v2.0**: pacchetto modulare, traduzione Ollama locale, orchestrazione del profilo di qualità, metadati Python installabili e test di integrazione opt-in con modelli reali. Vedi [Versioni GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases) e la cronologia dei commit per l'elenco completo delle modifiche.

## Come funziona

1. **Trascrizione** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) trascrive l'audio (accelerato tramite GPU)
2. **Separazione voce/musica** - [Demucs](https://github.com/facebookresearch/demucs) isola la voce dalla musica di sottofondo
3. **Traduzione** - MarianMT (locale, offline), Google Translate, DeepL Free o **Ollama LLM** (Qwen3, traduzioni concise adattate agli intervalli temporali)
4. **Diarizzazione dei parlanti** *(opzionale)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifica chi sta parlando in ogni segmento
5. **Doppiaggio vocale** - [Edge-TTS](https://github.com/rany2/edge-tts) (oltre 400 voci) o [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (clonazione vocale, per ciascun interlocutore nella conversazione)
6. **Missaggio** - la voce doppiata viene unita alla musica di sottofondo originale
7. **Normalizzazione**: audio finale normalizzato su -23 LUFS (standard di trasmissione EBU R128)
8. **Sincronizzazione labiale** *(opzionale)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) sincronizza i movimenti della bocca con l'audio doppiato

## Caratteristiche

- 🖥️ Interfaccia grafica con temi (Tkinter): non è necessaria alcuna riga di comando; temi Graphite, Slate, Light e Neon, colori principali, dimensioni del testo e pannelli delle impostazioni che puoi riordinare trascinando
- 🌍 **26 lingue di destinazione** con più voci per lingua
- 🌐 **UI in 26 lingue**: l'interfaccia stessa si adatta alla tua lingua
- 🎬 **Supporto YouTube e URL**: incolla qualsiasi collegamento YouTube e traduci direttamente (con tecnologia yt-dlp)
- ▶️ **Lettore video integrato** (libmpv/mpv) - controlli di riproduzione colorati per funzione, playlist, confronto A/B tra audio originale e doppiato, attivazione/disattivazione sottotitoli, istantanea, schermo intero, apertura cartella
- ⏱️ **Traduzione in tempo reale**: guarda un file locale o un collegamento video on-demand risolto con sottotitoli tradotti e uno slider di ritardo in stile YouTube; motori MarianMT/Google/DeepL/Ollama. Il doppiaggio vocale sperimentale utilizza Edge-TTS e una seconda istanza mpv. La gestione della sovrapposizione vocale e il collaudo con audio reale e su Windows sono ancora in corso; le trasmissioni live ancora in corso non sono ancora supportate. Consulta lo [stato dell'implementazione in tempo reale](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Separazione voce/musica tramite Demucs (mantiene la musica di sottofondo)
- 🔇 **Silenzia originale**, disponibile prima e durante la traduzione dal vivo, silenzia la colonna sonora del video mantenendo udibile la voce tradotta. Disattivalo per ripristinare l'audio originale; si reimposta al termine della sessione live.
- 🧠 **MarianMT** - traduzione neurale offline completamente locale (Helsinki-NLP, nessun limite di richieste, nessuna chiave API)
- 🤖 **Traduzione Ollama LLM** *(novità nella v2.0)* - LLM locale (Qwen3, Llama, Mistral) che produce traduzioni concise adattate agli intervalli temporali per il doppiaggio vocale naturale, rileva, installa e avvia Ollama e scarica il modello automaticamente al primo utilizzo
- 🎙️ **Clonazione vocale** - Coqui XTTS v2 clona la voce della persona che parla nell'audio originale nella lingua di destinazione (modello da ~1,8 GB), con velocità adattiva per segmento e tentativi multi-seed in caso di allucinazioni
- 👥 **Diarizzazione dei parlanti** - pyannote-audio 3.1 identifica più persone che parlano; XTTS clona ciascuna voce separatamente
- 💋 **Sincronizzazione labiale** - Wav2Lip GAN sincronizza i movimenti della bocca con l'audio doppiato (modello da ~416 MB)
- 🔊 **Normalizzazione audio** - normalizzazione automatica del volume -23 LUFS (EBU R128)
- ✏️ Editor di sottotitoli: rivedi e correggi i sottotitoli prima del doppiaggio vocale
- 📦 Elaborazione in batch: traduci più video o URL contemporaneamente
- ⚡ Accelerazione GPU tramite CUDA (ritorna automaticamente alla CPU)
- 📄 Esportazione sottotitoli `.srt` opzionale
- 🔁 Motore di traduzione **DeepL Free** (opzionale - 500.000 caratteri/mese, richiede chiave API gratuita)
- 🔧 **Installazione automatica**: i pacchetti Python mancanti e ffmpeg vengono installati automaticamente al primo avvio

## Lingue supportate

Arabo, cinese, ceco, danese, olandese, inglese, finlandese, francese, tedesco, greco, hindi, ungherese, indonesiano, italiano, giapponese, coreano, norvegese, polacco, portoghese, rumeno, russo, spagnolo, svedese, turco, ucraino, vietnamita

## Catalogo vocale

Il catalogo vocale Edge-TTS è definito in `LANGUAGES` nella parte superiore di `video_translator_gui.py`. Tale dizionario è la fonte di verità per i nomi delle lingue di destinazione, i pulsanti di opzione della voce della GUI e la voce di fallback della CLI quando `--voice` viene omesso.

Le note di manutenzione di Claude/progetto rispecchiano questa posizione in `CLAUDE.md` sotto **Voice Catalog Source Of Truth**, in modo che i futuri agenti del codice sappiano dove aggiornare le voci e dove il README indirizza gli utenti.

## Motori di traduzione

| Motore | Installazione | Limiti | Qualità |
|--------|-------|--------|---------|
| **Google Translate** *(predefinito)* | Nessuno | Scraping non ufficiale: potrebbe essere limitato su video di grandi dimensioni | ★★★★ |
| **MarianMT** | Nessuno: scarica circa 298 MB per coppia linguistica al primo utilizzo | Nessuno: completamente offline dopo il download | ★★★★ |
| **DeepL Free** | Chiave API gratuita su [deepl.com](https://www.deepl.com/pro-api) | 500.000 caratteri/mese | ★★★★★ |
| **Ollama LLM** *(consigliato per il doppiaggio vocale - nuovo nella v2.0)* | Installazione automatica al primo utilizzo (~1 GB per Ollama + 5 GB per il modello) | Nessuno: completamente locale | ★★★★★ |

> **MarianMT** utilizza i modelli [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP), memorizzati nella cache locale dopo il primo download. Richiede una lingua di origine esplicita (rilevamento automatico non supportato: seleziona manualmente la lingua di origine). I pacchetti Python richiesti (`sacremoses`, `sentencepiece`) vengono installati automaticamente alla prima selezione, se mancanti.

> **Ollama LLM** *(nuovo nella v2.0)* è il motore consigliato per il doppiaggio vocale perché produce traduzioni adattate alla durata dell'intervallo di destinazione. Laddove MarianMT traduce letteralmente e produce testi in italiano, spagnolo e francese circa il 25% più lunghi dell'inglese (rendendo udibile la compressione temporale della voce TTS), all'LLM viene richiesto di mantenere ogni segmento conciso e naturale per la lettura ad alta voce, ottenendo un rapporto caratteri tipico di 0,85-0,95 rispetto alla fonte. Il modello predefinito è `qwen3:8b` (5,2 GB su disco, ~6 GB VRAM); `qwen3:4b` (~3 GB) è l'opzione leggera, `qwen3:14b` quella di qualità superiore. La pipeline rileva automaticamente il binario Ollama, lo installa automaticamente tramite il programma di installazione ufficiale al primo utilizzo (con popup di consenso), avvia il demone e scarica il modello scelto: non è richiesta alcuna configurazione manuale. Passa automaticamente a Google Translate se manca qualcosa.

## Clonazione vocale (XTTS v2)

Quando abilitata, l'app estrae la voce di chi parla dal video originale e la utilizza come riferimento per clonare la voce nella lingua di destinazione.

- Lingue supportate: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Per le restanti 9 lingue, Edge-TTS viene utilizzato automaticamente come fallback
- Modello (~1,8 GB) scaricato automaticamente al primo utilizzo su `~/.local/share/tts/`
- **Riferimento filtrato con VAD** (v1.4): 10-15 s di parlato continuo selezionato dall'audio originale tramite [silero-vad](https://github.com/snakers4/silero-vad) per una migliore qualità di clonazione della voce
- **Velocità di generazione** configurabile (`xtts_speed`, predefinito `1.25`): valori più alti riducono gli artefatti di compressione audio post-elaborazione quando il testo tradotto è più lungo dell'intervallo originale. Regolabile tramite `~/.config/videotranslatorai/config.json` o CLI `--xtts-speed`
- Funziona su CUDA o CPU

## Diarizzazione dei parlanti (pyannote-audio)

Quando abilitata, l'app identifica chi sta parlando in ciascun segmento. In combinazione con la clonazione vocale, la voce di ciascun parlante viene clonata separatamente, ideale per interviste, podcast e video con più persone.

- Richiede un [token HuggingFace](https://huggingface.co/settings/tokens) gratuito (registrazione una tantum)
- **Token archiviato in modo sicuro** (v1.4) tramite il portachiavi del sistema operativo: Windows Credential Manager, macOS Keychain, Linux Secret Service. Migrazione automatica dal precedente archivio JSON in chiaro
- Dopo il primo download, funziona completamente offline
- Modello: `pyannote/speaker-diarization-3.1`

## Sincronizzazione labiale (Wav2Lip)

Se abilitata, l'app applica Wav2Lip GAN per sincronizzare i movimenti della bocca del soggetto con l'audio doppiato: la persona sembra parlare la lingua tradotta.

- Modello (~416 MB) e repository clonati automaticamente al primo utilizzo su `~/.local/share/wav2lip/`
- Funziona su CUDA (consigliato) o CPU
- Aumenta significativamente il tempo di elaborazione
- Funziona meglio con i video con un unico volto chiaramente visibile

## Requisiti

- Python 3.10+ (il programma di installazione di Windows fornisce automaticamente la versione 3.11.9)
- Windows 10/11 (x64), Linux o macOS
- **GPU NVIDIA fortemente consigliata**: vedere la tabella GPU di seguito
- 20 GB di spazio libero su disco per un'installazione completa (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg e tutti i pacchetti Python vengono installati automaticamente** al primo avvio, se mancanti. Non è richiesta alcuna configurazione manuale.

**Dipendenza di sistema opzionale** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Una volta installato, viene utilizzato per modificare la durata dell'audio senza alterarne l'intonazione nella banda di qualità controllata dal profilo (predefinito 1,15-1,50, fino a 1,65 per contenuti difficili), rimuovendo l'effetto "chipmunk" residuo sulle voci XTTS clonate. La pipeline funziona invariata senza di essa (fallback automatico su ffmpeg `atempo`). I profili di qualità ora preferiscono ulteriori tentativi per ottenere traduzioni più brevi rispetto all'accelerazione audio estrema.

### Supporto GPU

La pipeline utilizza cinque componenti accelerati da GPU (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). La copertura della GPU non è uniforme tra i produttori:

| GPU | Windows | Linux | Note |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx o versione successiva, driver CUDA 12.4) | ✅ piena accelerazione | ✅ piena accelerazione | **Consigliato.** Tutti e 5 i componenti vengono eseguiti su GPU. |
| **AMD** (Radeon) | ⚠️ incompleto (DirectML non supporta XTTS e faster-whisper) | ⚠️ parziale (ROCm funziona per Demucs/XTTS/pyannote ma faster-whisper supporta solo CUDA) | Funziona ma la trascrizione Whisper rimane sulla CPU e domina il tempo totale. |
| **Intel Arc** | ⚠️ supporto immaturo di PyTorch XPU | ⚠️ stesso | Non testato. |
| **Nessuno (solo CPU)** | ✅ funziona | ✅ funziona | Prevedi tempi di elaborazione **10-20 volte più lunghi** della durata del video. Una clip di 5 minuti può richiedere più di 50 minuti solo per essere trascritta con Whisper large-v3. |

**VRAM NVIDIA consigliata:**

| VRAM | Schede grafiche comuni | Esperienza |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Utilizzabile, non è possibile eseguire XTTS + Wav2Lip contemporaneamente |
| 8 GB | RTX 3060 Ti, 4060 | Pipeline completa, nessun margine |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Consigliato - buon margine** |
| 24 GB | RTX 3090, 4090 | Margine per batch di grandi dimensioni |

## Installazione

### Windows

1. Clona o scarica questo repository
2. Fai clic con il tasto destro su `setup_windows.bat` → **Esegui come amministratore** → il menu mostra `[1] Install`
3. Il programma di installazione esegue automaticamente queste operazioni:
   - Installa Python 3.11 se non presente (a livello di sistema)
   - Installa Git for Windows se non presente
   - Installa tutte le dipendenze Python (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps, ecc.)
   - Scarica e installa ffmpeg
   - Installa il lettore video integrato (python-mpv più una build libmpv in `mpv-runtime`). Il passaggio è facoltativo: se fallisce, tutto il resto funziona e il riquadro del lettore spiega cosa manca
   - Crea un **collegamento sul desktop pubblico** (visibile a ogni account Windows sul PC)

> Il programma di installazione è **multiutente**: tutto è installato a livello di sistema sotto `%ProgramFiles%\VideoTranslatorAI` e qualsiasi utente Windows sulla macchina trova il collegamento pronto per l'uso. Gli strumenti di compilazione VS C++ **non sono più necessari**: il fork `coqui-tts` mantenuto fornisce pacchetti Python wheel precompilati.

### Linux/macOS

```bash
# Clona il repository
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Opzionale: installare in anticipo lo stack NVIDIA CUDA 12.4 PyTorch testato
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Facoltativo: preinstalla tutti i pacchetti Python invece di lasciare alla GUI
# il compito di installare quelli mancanti al primo avvio
pip install --break-system-packages -r requirements.txt

# Opzionale: il lettore video integrato (libmpv dalla distribuzione, python-mpv da PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Facoltativo: installa il progetto come pacchetto Python modificabile
pip install --break-system-packages --no-deps -e .

# Avvia dal codice sorgente
python video_translator_gui.py

# Oppure, dopo l'installazione modificabile/del pacchetto
videotranslatorai
videotranslatorai --preflight
```

> Al primo avvio la GUI rileva eventuali pacchetti mancanti (faster-whisper, Demucs, Edge-TTS, ecc.) e li installa automaticamente, trasmettendo l'output alla finestra di registro. ffmpeg viene anche installato automaticamente tramite `apt-get` / `dnf` / `pacman` (Linux) o scaricato da GitHub (Windows).

> L'intestazione mostra il badge **Player**. Quando manca libmpv o python-mpv, il riquadro di sinistra indica cosa manca e offre **Installa player**: su Linux utilizza il gestore pacchetti tramite pkexec (quindi `sudo -n`) e mostra il comando manuale quando nessuno dei due funziona; su Windows chiede prima di scaricare libmpv per l'utente corrente (circa 32 MB).

### Profili dei requisiti

| File | Scopo |
|------|---------|
| `requirements.txt` | Installazione runtime completa e compatibile con le versioni precedenti. |
| `requirements-core.txt` | Pacchetti pipeline predefiniti utilizzati da GUI/CLI. |
| `requirements-optional.txt` | XTTS, tokenizzatori MarianMT, diarizzazione, VAD, portachiavi. |
| `requirements-wav2lip.txt` | Runtime Wav2Lip e stack di rilevamento volti (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Stack PyTorch verificato con pacchetti wheel per NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Lettore video integrato: python-mpv (richiede libmpv dal sistema o dal programma di installazione di Windows). |
| `requirements-dev.txt` | Dipendenze leggere utilizzate dai test CI/unità. |

## Disinstallazione

### Windows

Esegui `setup_windows.bat` (fai clic con il pulsante destro del mouse → **Esegui come amministratore**) e seleziona `[3] Uninstall` dal menu. Sono disponibili tre modalità secondarie di disinstallazione:

| Modalità | È richiesto l'amministratore | Ambito |
|------|----------------|-------|
| **[1] Disinstallazione completa con un clic** | ✅ | Rimuove la cartella dell'app, il collegamento sul desktop pubblico, ffmpeg dal PATH di sistema, la cache del modello HF di ogni utente (Whisper/XTTS) e la configurazione (`HF token`) e tutti i pacchetti AI Python installati dal programma di installazione. Alla fine chiede anche, con consenso esplicito, se disinstallare silenziosamente **Python 3.11** e **Git for Windows** tramite le stringhe di disinstallazione silenziosa del registro. |
| **[2] Solo utente attuale** | ❌ | Rimuove solo la configurazione VTAI dell'utente corrente, la cache HF/XTTS e l'installazione legacy per utente. **Lascia intatta l'installazione a livello di sistema** in modo che altri account Windows sul PC possano continuare a utilizzare l'app. |
| **[3] Personalizzato - granulare** | ✅ per gli componenti di sistema, ❌ per gli componenti dell'utente | Richiesta Y/N per ogni categoria: cartella dell'app, collegamento, PATH di sistema, installazioni legacy per utente, configurazioni/cache per utente, quindi pacchetti Python raggruppati (TTS, stack PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, utilità pipeline) e infine Python 3.11 e Git opzionali. |

**Mai rimosso automaticamente:** Visual Studio C++ Build Tools (se presente nelle versioni precedenti). Utilizza *App e funzionalità* nelle Impostazioni di Windows per rimuoverle manualmente, se lo desideri.

### Linux/macOS

Nessun programma di disinstallazione dedicato: rimuovi manualmente:

```bash
# Pacchetti Python installati dal programma di installazione automatica della GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Dati utente e cache dei modelli
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # configurazione (temi, ordine dei pannelli, impostazioni)
rm -f  ~/.videotranslatorai_config.json     # configurazione legacy delle versioni <= 1.9, se presente
```

## Utilizzo

### Diagnostica

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Esegue la diagnostica dell'ambiente locale senza avviare la traduzione o installare nulla. `--preflight-lipsync` tratta i pacchetti di rilevamento del volto per Wav2Lip come dipendenze obbligatorie, il che è utile prima di abilitare **Sincronizzazione labiale**. La GUI espone lo stesso controllo di base dal pulsante **Diagnostica** del pannello di registro. `--preflight-player` tratta il lettore video integrato (python-mpv e un libmpv caricabile) come dipendenza obbligatoria. `python -m videotranslator.libmpv_runtime check` analizza solo libmpv (uscita 0 pronta, 2 non disponibile).

### GUI

```bash
python video_translator_gui.py
```

**Layout:** le impostazioni di traduzione batch si trovano nella colonna a destra, come una serie di pannelli delle impostazioni: **Input**, **Traduzione**, **Profilo flusso di lavoro**, **Avvio** e le sezioni avanzate comprimibili (modello, motore di traduzione, audio, clonazione vocale, sincronizzazione labiale, diarizzazione, opzioni, hotword). L'ampia area a sinistra è il **lettore video integrato** (trasporto, playlist, confronto A/B tra audio originale e doppiato, sottotitoli, istantanea, schermo intero), con la barra di **traduzione in tempo reale** sottostante. Trascina una scheda dal titolo o dalla maniglia **≡** per spostarla verso l'alto o verso il basso nella colonna; l'ordine viene salvato (`ui_panel_order`) e ripristinato al successivo avvio. Il pannello di registro in basso può essere nascosto con **Nascondi log**. All'avvio la finestra si apre centrata sul monitor corrente (quello sotto il puntatore) e ingrandita, quindi si comporta bene su una configurazione multi-monitor.

**Controlli del lettore video:** le icone utilizzano colori funzionali coerenti in ogni tema, indipendentemente dal colore principale selezionato:

| Controllo | Colore |
|---------|--------|
| Riproduci video | Verde |
| Pausa (sostituisce Riproduci durante la riproduzione) | Ambra |
| Stop | Rosso corallo |
| Precedente / indietro 10 s / avanti 10 s / successivo | Blu |
| Istantanea | Viola |
| Apri cartella | Oro |

Il passaggio del mouse aggiunge uno sfondo leggermente colorato. I controlli non disponibili sono neutrali; la navigazione nella playlist rimane utilizzabile dopo Stop. Le descrizioni comandi e gli indicatori del focus da tastiera rimangono disponibili, quindi il colore non è l'unico modo per identificare le azioni.

**Da file locali:**
1. Fai clic su **Aggiungi** per selezionare uno o più file video
2. Scegli la lingua di partenza e quella di destinazione
3. Apri la sezione **Modello** e seleziona un modello Whisper (`small` è un buon equilibrio tra velocità/precisione)
4. Scegli una voce e regola la velocità TTS se necessario
5. *(Facoltativo)* Nel **Motore di traduzione** seleziona **Google** (predefinito), **MarianMT** (locale/offline), **DeepL Free** o **Ollama LLM** (locale, consigliato per il doppiaggio vocale)
6. *(Facoltativo)* Abilita la **Clonazione vocale** (XTTS v2) e/o **Diarizzazione dei parlanti**
7. *(Facoltativo)* Abilita **Sincronizzazione labiale** (Wav2Lip)
8. Fai clic su **Avvia traduzione**

**Da YouTube (o qualsiasi sito supportato):**
1. Incolla uno o più URL nel campo **URL** (uno per riga)
2. Configura lingua, modello e voce come al solito
3. Fai clic su **⬇ Scarica e traduci**

> yt-dlp supporta YouTube, Vimeo, Twitter/X, TikTok e [oltre 1000 altri siti](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Avviso sul fair use:** Il download di video tramite yt-dlp è considerato accesso automatizzato da piattaforme come YouTube e potrebbe violare i loro Termini di servizio. L'uso intenso o ripetuto dello stesso indirizzo IP può causare blocchi temporanei (errori HTTP 429/accesso richiesto). Utilizza una VPN o ruota il tuo IP se riscontri errori di download. Questo strumento è destinato esclusivamente all'uso personale e non commerciale. La ridistribuzione del contenuto tradotto può violare il diritto d'autore: rispetta sempre i diritti del creatore originale.

### Traduzione in tempo reale (sottotitoli e doppiaggio vocale sperimentale)

Guarda un file locale o un collegamento video on-demand risolto con sottotitoli tradotti e traduzione parlata opzionale. Usa la barra sotto il player:

**Da un collegamento:**

1. Incolla un collegamento nel campo **URL**
2. Imposta la lingua di origine e di destinazione, scegli una voce e regola il dispositivo di scorrimento **Ritardo**
3. Seleziona **Voce doppiata** e/o **Sottotitoli**
4. Per ascoltare solo la voce tradotta, seleziona **Silenzia originale** prima di iniziare (in italiano: **Silenzia originale**, accanto alla casella di controllo dei sottotitoli)
5. Fai clic su **Traduci in tempo reale**: il collegamento viene risolto e la traduzione inizia

**Da un file caricato:** carica un video nel player (Input -> Aggiungi, quindi selezionalo), lascia vuoto il campo URL, scegli le stesse impostazioni live e fai clic su **Traduci in tempo reale**. Un URL ha la priorità quando il campo non è vuoto.

- **Motore:** MarianMT (offline, predefinito), Google, DeepL o Ollama. Il riconoscimento vocale (Whisper) viene eseguito localmente. I modelli offline richiedono un download iniziale.
- **Doppiaggio vocale:** riproduzione vocale sperimentale Edge-TTS tramite una seconda istanza mpv. Richiede l'accesso a Internet ed è separato dalla clonazione vocale batch.
- **Silenzia originale:** disponibile sia prima di iniziare che durante la traduzione. Silenzia l'intera colonna sonora originale, inclusa la musica e gli effetti, ma lascia udibile la voce tradotta. Non isola la persona che parla nell'audio originale. Disattivalo per ripristinare la colonna sonora; si reimposta al termine della sessione live. Il pulsante dell'altoparlante del lettore è il silenziamento generale, non questo controllo indipendente.
- **Pausa e spostamento nel video:** i controlli del lettore video sono collegati alla sessione live; la sincronizzazione audio end-to-end necessita ancora di test di accettazione specifici della piattaforma.
- **Limiti attuali:** la gestione della sovrapposizione/dissolvenza delle clip, la calibrazione della temporizzazione dell'audio e il collaudo su Windows restano da completare. Le trasmissioni live ancora in corso non sono ancora supportate; l'etichetta della modalità live non implica il supporto per l'acquisizione progressiva di una trasmissione ancora in corso. Consultare lo [stato di implementazione e lavoro rimanente](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Per un video doppiato salvato, utilizza **Scarica e traduci** / **Avvia traduzione** invece dell'anteprima in tempo reale.

### Blocchi del motore di traduzione e VPN

Possono verificarsi due blocchi diversi, con soluzioni diverse:

| Blocco | Sintomo | Soluzione |
|-------|---------|-----|
| **Download** (yt-dlp) | "Accedi per confermare che non sei un bot", HTTP 429 | **VPN** / ruota l'IP o accedi a YouTube nel tuo browser (i cookie vengono letti automaticamente) |
| **Traduzione** (endpoint gratuito di Google) | "Google Translate non è riuscito a tradurre... limite di richieste raggiunto o servizio bloccato" | Utilizza **MarianMT** (offline) o **Ollama** (locale) - nessun limite di richieste. Anche una VPN aiuta. Il flusso batch ora **ritorna automaticamente a MarianMT** quando Google viene bloccato. |

### Temi e aspetto

Fai clic sull'icona a forma di ingranaggio nell'intestazione per aprire **Impostazioni**:

- **Tema**: Automatico (segue la modalità scuro/chiaro del sistema operativo), Graphite (predefinito), Slate, Light, Neon.
- **Colore d'accento**: predefinito per tema, oppure blu, verde acqua, viola, verde, ambra, rosa.
- **Dimensione del testo**: piccolo, normale, grande, extra grande.
- **Lingua dell'interfaccia**: 26 lingue.

Le modifiche si applicano immediatamente, senza riavviare, e vengono salvate nel file di configurazione (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Ripristina impostazioni predefinite** ripristina il tema Graphite, l'accento predefinito, la dimensione normale del testo e l'ordine predefinito dei pannelli delle impostazioni.

### Riga di comando

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Tutte le opzioni:**

| Opzione CLI | Descrizione | Predefinito |
|------|-------------|---------|
| `--lang-source` | Lingua di origine (`auto` per rilevamento automatico) | `auto` |
| `--lang-target` | Codice della lingua di destinazione (es. `it`, `fr`, `de`) | `it` |
| `--voice` | Nome della voce Edge-TTS | auto |
| `--model` | Modello Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Regolazione velocità TTS (es. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` o `deepl` | `google` |
| `--deepl-key` | Chiave API DeepL Free | - |
| `--diarize` | Abilita la diarizzazione dei parlanti (pyannote) | - |
| `--hf-token` | Token HuggingFace per la diarizzazione | - |
| `--lipsync` | Applica la sincronizzazione labiale Wav2Lip dopo il doppiaggio vocale | - |
| `--subs-only` | Genera solo `.srt`, salta il doppiaggio vocale | - |
| `--no-subs` | Salta la generazione `.srt` | - |
| `--no-demucs` | Salta la separazione voce/musica | - |
| `--output` / `-o` | Percorso del file di output | auto |
| `--output-dir` | Cartella per i file tradotti (un posto, Windows e Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Elabora più file | - |

### test di integrazione con modelli reali

La suite di test predefinita evita download di modelli reali e lunghi lavori della GPU. Per eseguire verifiche empiriche facoltative per lo stack locale installato:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Questi controlli convalidano le importazioni Wav2Lip reali, la disponibilità di Torch CUDA, la disponibilità del demone Ollama e faster-Whisper sul parlato sintetico. Falliscono o vengono saltati intenzionalmente quando lo stato del driver/demone/modello locale non è pronto.

**Esempi:**

```bash
# Traduci video dall'italiano all'inglese con MarianMT locale
# (scarica il modello da ~298 MB al primo utilizzo, quindi completamente offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Traduci con clonazione della voce + diarizzazione dei parlanti
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Traduci con la sincronizzazione labiale
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Solo sottotitoli (nessun doppiaggio vocale)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Modelli Whisper

| Modello | Dimensioni | Velocità | Precisione |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` è una versione distillata di `large-v3` (4 livelli di decodificatore contro 32): qualità vicina a large con velocità simile a `medium`. Impostazione predefinita consigliata su una GPU moderna quando la velocità di trascrizione è importante; il calo di qualità del materiale multilingue è lieve.

> I modelli vengono scaricati automaticamente al primo utilizzo.

## CLI dei moduli indipendenti

Il pacchetto modulare espone quattro strumenti rivolti all'utente che possono essere richiamati direttamente senza avviare la pipeline completa:

```bash
# Verifica preliminare della presenza di un volto (Wav2Lip salta il video se assente).
python3 -m videotranslator.face_detector path/to/video.mp4
# uscita 0 = volto presente, uscita 1 = nessun volto

# Analizzare un file *_metrics.csv prodotto da build_dubbed_track.
# Riporta P50/P75/P90/P95 di pre_stretch_ratio, scomposizione della banda udibile,
# utilizzo del motore stretch e i primi N peggiori valori anomali con il relativo testo di destinazione.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Normalizza il testo per TTS (riscrive i due punti, il punto e virgola, i puntini di sospensione, i trattini).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Stima la difficoltà del doppiaggio vocale da un file di segmenti .srt o .json PRIMA di eseguire TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Ogni strumento ha `-h`/`--help` per opzioni complete. Sono autonomi e riutilizzano gli stessi moduli su cui si basa la pipeline del doppiaggio vocale, quindi il loro output rimane coerente con il runtime.

## Licenza

MIT

### Componenti di terze parti

Il codice del repository è MIT. I programmi di installazione scaricano i componenti seguenti dalle proprie fonti al momento dell'installazione; il progetto non li ridistribuisce.

- **libmpv** (https://github.com/mpv-player/mpv), il motore del lettore video integrato. Windows: viene provata per prima la build LGPL di zhongfly (https://github.com/zhongfly/mpv-winbuild); una build GPL di shinchiro con versione fissata (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) è il fallback. `mpv-runtime\BUILD.txt` registra l'origine, il tipo di licenza e il commit mpv e il testo della licenza si trova accanto alla DLL. Linux: il pacchetto di distribuzione (`libmpv2`, `libmpv1`, `mpv-libs` o `mpv`).
- **FFmpeg** all'interno di libmpv (LGPL o GPL, seguendo la build di libmpv).
- **python-mpv** (`mpv` su PyPI), GPLv2+ o LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), utilizzato dal programma di installazione di Windows per estrarre libmpv e successivamente eliminato.
- **Vulkan loader** (Khronos, MIT e Apache-2.0), scaricato su Windows solo quando manca `vulkan-1.dll`.
- **edge-tts** (LGPLv3), utilizzato dalla pipeline del doppiaggio vocale.
- **Modelli MarianMT** (Helsinki-NLP), scaricati da Hugging Face Hub al primo utilizzo con le rispettive licenze (Apache-2.0 per i modelli `opus-mt`, CC-BY-4.0 per `opus-mt-tc-big`).
