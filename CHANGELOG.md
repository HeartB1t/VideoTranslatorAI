# Changelog — VideoTranslatorAI

Registro cronologico di tutto il lavoro svolto sul progetto.

> ⚠️ **REGOLA FONDAMENTALE — PRIORITÀ ASSOLUTA**
> Ogni feature deve funzionare su **Windows E Linux**.
> Prima di implementare qualsiasi libreria verificare la compatibilità Windows.
> Se richiede compilatori o dipendenze native, gestirla in `install_windows.bat` con wheel pre-compilate.

---

## [1.2] — 2026-04-19

### Fix — dipendenze MarianMT (`sacremoses`)
- Aggiunto `sacremoses>=0.1.1` a `requirements.txt` e `install_windows.bat`: era mancante e causava `ModuleNotFoundError` al caricamento di `MarianTokenizer`, forzando il fallback su Google Translate anche quando MarianMT era selezionato.

### GUI — check dipendenze MarianMT alla selezione
- Quando l'utente seleziona il radiobutton **MarianMT**, viene eseguito un check immediato di `sacremoses` e `sentencepiece` via `importlib.util.find_spec()`.
- Se uno o entrambi mancano: popup informativo con lista pacchetti mancanti e avviso pip. L'utente può accettare l'installazione automatica (con progress nel log) o rifiutare (il motore torna su Google automaticamente).
- Nessuna modifica ai dizionari i18n — il messaggio riusa le chiavi esistenti `msg_deps_missing` e `msg_deps_install`.

---

## [1.1] — 2026-04-18

### Lip Sync — Wav2Lip GAN
- Nuovo step opzionale **[+]** nella pipeline: sincronizza il movimento delle labbra al doppiaggio tradotto.
- **GUI:** checkbox `💋 Lip Sync (Wav2Lip — prima esecuzione: download ~416MB)` nelle opzioni.
- Funzione `_ensure_wav2lip_assets()`: clona il repo `Rudrabha/Wav2Lip` in `~/.local/share/wav2lip/Wav2Lip/` (git `--depth 1`) e scarica il modello GAN `wav2lip_gan.pth` (~416 MB) da HuggingFace al primo utilizzo. Download atomico via file `.part` (nessun file corrotto in caso di interruzione). Installa automaticamente le dipendenze del repo (`pip install -r requirements.txt` del repo Wav2Lip).
- Funzione `apply_lipsync(video_path, audio_path, tmp_dir)`: esegue `inference.py` via `subprocess.Popen` con streaming output riga per riga (feedback in tempo reale nel log GUI). CUDA se disponibile, fallback CPU.
- Audio passato a Wav2Lip: traccia vocale TTS **senza background musicale** (`bg_path=None`) per massima accuratezza del lip sync.
- `torch.cuda.empty_cache()` eseguito **prima** del subprocess, così Wav2Lip trova la GPU più libera possibile.
- Fallback automatico: se Wav2Lip fallisce per qualsiasi motivo, il video doppiato senza lipsync viene restituito senza crash.
- Disponibile via CLI: `--lipsync`.
- **Linux/Windows:** ✓ cross-platform (subprocess con lista args, senza shell=True).
- `requirements.txt`: rimossi `basicsr`/`facexlib` (incompatibili con torchvision≥0.17); dipendenze Wav2Lip installate dall'interno del repo clonato.

---

## [1.0] — 2026-04-18

### Speaker Diarization — pyannote-audio 3.1
- Nuovo step opzionale **[3b]** nella pipeline: riconosce chi parla in ogni segmento prima della traduzione.
- Funzione `diarize_audio()`: carica `pyannote/speaker-diarization-3.1` da HuggingFace, gira su GPU (CUDA) o CPU.
- Funzione `assign_speakers()`: assegna a ogni segmento Whisper il parlante con la maggiore sovrapposizione temporale.
- L'informazione `speaker` si propaga attraverso `translate_segments()` e `build_dubbed_track()` → XTTS clona la voce giusta per ciascun parlante.
- **GUI:** checkbox `👥 Diarization multi-speaker (pyannote)` + campo HF token mascherato (appare solo quando attivato).
- HF token salvato persistentemente in `~/.config/videotranslatorai/config.json` via `load_config()` / `save_config()` — non viene richiesto ad ogni avvio.
- Fallback automatico: se la diarization fallisce per qualsiasi errore, la pipeline continua senza informazioni speaker (nessun crash).
- **Limite:** richiede token HuggingFace gratuito (una tantum, registrazione su huggingface.co/settings/tokens) — dopo il download è 100% offline.
- **Linux/Windows:** ✓ pyannote-audio 3.1 funzionante su entrambi (ffmpeg già presente dall'installer).
- Disponibile anche via CLI: `--diarize --hf-token TOKEN`.

### GUI — adattamento automatico schermo
- `_fit_to_screen()`: al lancio, la finestra si ridimensiona automaticamente per non superare le dimensioni del monitor (con margine 40×80 px) e viene centrata.
- Utile su monitor piccoli o configurazioni multi-monitor con risoluzioni diverse.

---

## [0.9] — 2026-04-18

### MarianMT — traduzione locale offline (Helsinki-NLP)
- Nuovo motore di traduzione completamente locale e offline via HuggingFace Transformers.
- Selezionabile in GUI come terzo radiobutton: `Google (default) / DeepL Free / MarianMT (locale)`.
- Disponibile anche via CLI: `--translation-engine marian`.
- Modelli `Helsinki-NLP/opus-mt-{src}-{tgt}` (~298 MB per coppia), scaricati automaticamente al primo uso dalla HuggingFace Hub e cachati localmente.
- Normalizzazione codici lingua: `zh-CN → zh`, `no → nb` (Bokmål), altri codici troncati al prefisso ISO 639-1.
- Batch processing da 8 segmenti per volta; preserva indici dei segmenti vuoti.
- Gira su CUDA o CPU — modello e tokenizer scaricati dalla VRAM dopo ogni uso (`torch.cuda.empty_cache()`).
- Import lazy: `transformers` non viene importato allo startup, nessun impatto sui tempi di avvio.
- Fallback automatico a Google Translate se: lingua sorgente = `auto`, modello non disponibile su HF, o qualsiasi errore runtime.
- **Limite:** richiede lingua sorgente esplicita (auto-detect non supportato da MarianMT).
- **Linux/Windows:** ✓ `sentencepiece>=0.2.0` ha wheel pre-compilate su PyPI — nessun compilatore richiesto.
- `requirements.txt` aggiornato: `transformers>=4.40.0`, `sentencepiece>=0.2.0`.

---

## [0.8] — 2026-04-18

### UI multilingua — 26 lingue
- Menu a tendina "Lingua UI" ora include tutte le 26 lingue supportate dal tool (prima solo IT/EN).
- 24 nuove lingue aggiunte: AR, ZH, CS, DA, NL, FI, FR, DE, EL, HI, HU, ID, JA, KO, NO, PL, PT, RO, RU, ES, SV, TR, UK, VI.
- Tutte le 61 stringhe UI tradotte automaticamente via Google Translate e incorporate nel codice.
- Nessuna chiamata API a runtime — le traduzioni sono statiche nel dict `UI_STRINGS`.
- **Linux/Windows:** ✓ solo dict Python, zero dipendenze aggiuntive.
- Backup locale: `video_translator_gui.py.bak` (in `.gitignore`).

---

## [0.7] — 2026-04-18

### Normalizzazione audio — pyloudnorm
- Doppiaggio finale normalizzato automaticamente a **-23 LUFS** (standard broadcast EBU R128).
- Applicato in `build_dubbed_track()` dopo il mix, trasparente all'utente.
- Skip automatico se il segnale è silenzio (loudness < -70 LUFS).
- **Linux/Windows:** ✓ solo NumPy + SciPy.

### DeepL Free — motore traduzione opzionale
- Nuovo checkbox "DeepL Free" nelle Opzioni + campo API key mascherato.
- Se attivato e key presente → usa DeepL Free API (500k char/mese gratuiti).
- Se key mancante o errore → fallback automatico a Google Translate con avviso nel log.
- **⚠️ Limite:** 500k caratteri/mese gratuiti — richiede registrazione su deepl.com.
- **Linux/Windows:** ✓ puro REST via deep-translator (già dipendenza).
- `translate_segments()` e `translate_video()` accettano `engine` e `deepl_key`.

### Fix Whisper — allucinazioni e ripetizioni
- `condition_on_previous_text=False`: elimina loop di frasi ripetute.
- `repetition_penalty=1.3` + `no_repeat_ngram_size=3`: penalizza token ripetuti.
- `compression_ratio_threshold=2.4`: scarta segmenti allucinati.
- VAD più morbido (`threshold=0.3`, `min_silence_duration_ms=300`): meno parole tagliate.
- Dedup post-processing: rimuove segmenti consecutivi identici.

---

## [ROADMAP] — Feature da implementare (post-test XTTS v2)

> Obiettivo: tool completamente gratuito, locale, senza rate limit. Funziona su **Linux e Windows**.
> Se un servizio ha limiti o richiede registrazione, l'utente viene informato con spunta dedicata in GUI.
> Aggiornare questa sezione dopo i test di v0.6. Implementare nell'ordine indicato.

### Compatibilità Windows/Linux — panoramica rapida
| Feature | Linux | Windows | Note Windows |
|---------|-------|---------|--------------|
| MarianMT (transformers) | ✓ | ✓ | sentencepiece ha wheel pre-compilate su PyPI da v0.2.0+ |
| DeepL API | ✓ | ✓ | Puro REST, zero dipendenze native |
| pyannote-audio 3.1 | ✓ | ✓ | ffmpeg già gestito dall'installer |
| pyloudnorm | ✓ | ✓ | Solo NumPy + SciPy, zero problemi |
| Wav2Lip (dlib) | ✓ | ⚠️ | dlib richiede wheel pre-compilata su Windows (vedi §4) |

---

### PROBLEMA ATTUALE: Google Translate (deep-translator)
- **Stato:** scraping non ufficiale — bloccabile da Google, rate limit reale ~100 req/giorno
- **Rischio:** su video lunghi con centinaia di segmenti può essere bloccato silenziosamente
- **Funziona su Windows?** Sì (è puro HTTP), ma i blocchi di Google si applicano ugualmente
- **Azione:** sostituire con MarianMT come default + DeepL opzionale

---

### 1. ~~Traduzione — MarianMT locale (Helsinki-NLP)~~ — ✅ IMPLEMENTATO in v0.9
- **Cosa:** modelli di traduzione neurali completamente locali via HuggingFace Transformers
- **Perché:** zero rate limit, zero API key, offline completo dopo primo download
- **Come:** `pip install transformers sentencepiece` — modelli `Helsinki-NLP/opus-mt-{src}-{tgt}`, ~298MB per coppia (scaricati automaticamente al primo uso)
- **Linux:** ✓ nessun problema
- **Windows:** ✓ `sentencepiece` ha wheel pre-compilate su PyPI da v0.2.0+ — `pip install` funziona senza compilatori
- **Effort:** ~1-2 ore — opzione GUI "Motore traduzione: MarianMT (locale) / DeepL / Google"
- **Limiti:** nessuno — completamente offline e illimitato
- **Lingue:** 1000+ coppie, copre tutte le 26 lingue del progetto

### 1b. ~~DeepL~~ — ✅ IMPLEMENTATO in v0.7
- **Cosa:** API DeepL Free come alternativa opzionale a MarianMT
- **Perché:** qualità superiore a MarianMT su testi tecnici e dialogo naturale
- **Come:** `pip install deepl` + campo API key nelle impostazioni GUI
- **Linux/Windows:** ✓ completamente cross-platform, puro REST
- **Limiti:** ⚠️ 500.000 caratteri/mese gratuiti — registrazione su deepl.com necessaria
- **GUI:** spunta "Usa DeepL (500k char/mese gratuiti)" + stima caratteri mostrata prima della traduzione
- **Effort:** ~30 minuti aggiuntivi dopo MarianMT

---

### 2. ~~Speaker Diarization — pyannote-audio 3.1~~ — ✅ IMPLEMENTATO in v1.0
- **Cosa:** riconosce chi parla in ogni segmento → XTTS clona la voce giusta per ciascun parlante
- **Perché:** video con più persone → doppiaggio realistico, ogni voce clonata separatamente
- **Come:** `pip install pyannote-audio` — modello `pyannote/speaker-diarization-3.1`
- **Linux:** ✓ nessun problema
- **Windows:** ✓ versione 3.1 confermata funzionante su Windows (ffmpeg già presente dall'installer)
- **Limiti:** ⚠️ HuggingFace token GRATUITO richiesto (una tantum, registrazione su huggingface.co) — dopo download è 100% offline
- **GUI:** spunta "Diarization multi-speaker" + campo HF token (salvato localmente in un file config)
- **Effort:** ~2-3 ore
- **Nota:** quasi nessun competitor web fa diarization + voice cloning per speaker — forte differenziatore

---

### 3. ~~Normalizzazione audio — pyloudnorm~~ — ✅ IMPLEMENTATO in v0.7
- **Cosa:** normalizza il volume del doppiaggio finale allo standard broadcast (-23 LUFS EBU R128)
- **Perché:** XTTS genera audio a volume variabile; il mix finale suona più professionale e uniforme
- **Come:** `pip install pyloudnorm` — applicato automaticamente in `build_dubbed_track()`
- **Linux/Windows:** ✓ solo NumPy + SciPy, zero dipendenze native, zero problemi cross-platform
- **Limiti:** nessuno
- **GUI:** nessuna modifica — trasparente, sempre attivo
- **Effort:** ~30 minuti

---

### 5. UI multilingua — tutte le 26 lingue ⭐ PRIORITÀ MEDIA
- **Cosa:** aggiungere tutte le 26 lingue supportate dal tool anche come lingua dell'interfaccia grafica (attualmente solo IT e EN)
- **Perché:** utenti internazionali possono usare il tool nella propria lingua madre
- **Come:** auto-traduzione delle ~40 stringhe UI con `deep-translator` (già dipendenza) → generazione del dict `UI_STRINGS` per tutte le lingue → aggiunta al menu a tendina "Lingua UI"
- **Linux/Windows:** ✓ nessun problema cross-platform — è solo un dict Python
- **Limiti:** nessuno — le stringhe vengono tradotte una volta e incorporate nel codice, nessuna chiamata API a runtime
- **Approccio:** script one-shot che traduce tutte le stringhe e genera il codice Python, poi revisione manuale se necessario
- **Effort:** ~1 ora

---

### 4. ~~Lip Sync — Wav2Lip~~ — ✅ IMPLEMENTATO in v1.1
- **Cosa:** sincronizza il movimento delle labbra al doppiaggio → il soggetto sembra parlare la lingua tradotta
- **Perché:** unico gap rimasto rispetto a HeyGen
- **Come:** modello Wav2Lip ~700MB, inference GPU, applicato come step finale dopo mux video
- **Linux:** ✓ nessun problema, dlib si installa normalmente via pip
- **Windows:** ⚠️ dlib richiede wheel pre-compilata — l'installer scarica automaticamente il `.whl` corretto da GitHub (z-mahmud22/Dlib_Windows_Python3.x) in base alla versione Python rilevata
- **Limiti:** nessuno — completamente locale e gratuito
- **GUI:** spunta "Lip Sync (Wav2Lip)" nelle opzioni — aumenta i tempi di elaborazione
- **Effort:** ~4-6 ore — da fare per ultima, dopo che tutto il resto è stabile e testato

---

## [0.6] — 2026-04-18

### Voice Cloning con Coqui XTTS v2
- Nuovo motore TTS opzionale: **Coqui XTTS v2** affianca Edge-TTS.
- Checkbox in GUI: "🎙 Voice Cloning (Coqui XTTS v2)" — disabilitato di default.
- Con XTTS attivo, la voce del parlante originale viene estratta dal video (traccia vocals di Demucs) e usata come riferimento per clonare la voce nella lingua di destinazione.
- Clip di riferimento: 30 secondi di audio vocale pulito (resampla a 22050 Hz mono).
- Lingue supportate da XTTS v2: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26). Per le restanti 9 lingue, fallback automatico a Edge-TTS con avviso nel log.
- Fallback robusto: se XTTS fallisce per qualsiasi errore, il sistema torna automaticamente a Edge-TTS.
- Modello XTTS v2: ~1.8 GB, scaricato automaticamente alla prima esecuzione in `~/.local/share/tts/`.
- Gira su CUDA (RTX 3090) o CPU — memoria VRAM liberata dopo ogni batch.
- `requirements.txt` aggiornato: `TTS>=0.22.0`.
- `install_windows.bat` aggiornato: `TTS` aggiunto alla lista pacchetti.

---

## [0.5] — 2026-04-18

### Output URL → ~/Videos
- Quando il video di input viene da un download temporaneo (`/tmp/`), il file tradotto viene salvato automaticamente in `~/Videos/` su Linux e `%USERPROFILE%\Videos\` su Windows.
- Per file locali il comportamento è invariato: output nella stessa cartella del video sorgente.
- Logica in `translate_video()`: confronto `input_dir.relative_to(tmp_root)` per rilevare path temporanei.

---

## [0.4] — 2026-04-17

### YouTube / URL download integrato
- Aggiunto supporto download diretto da YouTube e 1000+ siti tramite `yt-dlp`.
- Nuovo widget **URL** nella GUI: incolla uno o più link (uno per riga), pulsante **⬇ Scarica e Traduci**.
- Fix **YouTube 403 Forbidden**: yt-dlp web client bloccato da YouTube SABR streaming. Risolto con `"extractor_args": {"youtube": {"player_client": ["ios", "android"]}}`.
- Download in cartella temporanea (`tempfile.TemporaryDirectory`), poi spostato su file stabile con `tempfile.mkstemp` prima di passare alla pipeline.
- Cleanup garantito nel blocco `try/finally` anche in caso di errore.
- `yt-dlp` aggiunto a `requirements.txt` e `install_windows.bat`.

### Sicurezza temp file
- Sostituito `tempfile.mktemp` (insicuro) con `tempfile.mkstemp` + `os.close(fd)`.

---

## [0.3] — 2026-04-16

### Architettura single-file
- `video_translator.py` (pipeline) e `video_translator_gui.py` (GUI) fusi in un unico file `video_translator_gui.py`.
- CLI disponibile se vengono passati argomenti (`if len(sys.argv) > 1: _cli()`), altrimenti si avvia la GUI.
- Eliminato `subprocess` per il batch: i thread chiamano direttamente `translate_video()`.
- Log in tempo reale via `_TkStreamRedirect` che redirige `sys.stdout/stderr` al widget di log della GUI.

### Thread safety
- `_snapshot_params()` legge tutte le variabili Tkinter sul thread principale prima di avviare il worker.
- Tutti gli aggiornamenti ai widget usano `self.after(0, ...)`.

### Controllo dipendenze
- `check_dependencies()` chiamato all'avvio sia in modalità GUI che CLI.

---

## [0.2] — 2026-04-15

### Switcher lingua UI (IT / EN)
- `UI_STRINGS` dict con chiavi `"it"` e `"en"` per tutta l'interfaccia.
- Pulsante toggle IT/EN in alto a destra; tutti i widget vengono aggiornati on-the-fly.
- Fix placeholder URL: usato flag `_url_placeholder_active` (booleano) invece del confronto con stringa, per compatibilità con il cambio lingua.

### Installer Windows riscritto
- `install_windows.bat` completamente riscritto in inglese.
- Check privilegi Amministratore via `net session` all'inizio.
- Installa PyTorch cu124, poi fallback CPU se CUDA non disponibile.
- Download automatico di ffmpeg (~90 MB) via PowerShell + aggiunta al PATH utente.
- Creazione shortcut Desktop tramite `WScript.Shell`.
- `yt-dlp` incluso nella lista pacchetti.

---

## [0.1] — 2026-04-14

### Setup iniziale progetto
- Struttura base: `video_translator.py` (pipeline) + `video_translator_gui.py` (GUI Tkinter dark theme).
- Pipeline: estrazione audio (ffmpeg) → separazione voce/musica (Demucs htdemucs) → trascrizione (faster-Whisper) → traduzione (deep-translator GoogleTranslator) → TTS (edge-tts con retry esponenziale) → mix audio → mux video.
- 26 lingue supportate con voci Edge-TTS multiple per lingua.
- Editor sottotitoli integrato: revisione e correzione prima del doppiaggio.
- Batch processing: più file o URL contemporaneamente.
- Accelerazione GPU via CUDA 12.4 (fallback automatico CPU).
- Export opzionale `.srt`.
- `requirements.txt` con tutti i pacchetti; `audioop-lts` condizionale per Python 3.13+.

### Pubblicazione GitHub
- Repository creato: https://github.com/HeartB1t/VideoTranslatorAI
- `README.md` completo con istruzioni Linux/Windows, tabella flag CLI, tabella modelli Whisper.

---

## Architettura attuale

```
video_translator_gui.py   ← unico file: pipeline + GUI + CLI
install_windows.bat       ← installer Windows (Admin, ffmpeg, PyTorch, shortcut)
requirements.txt          ← dipendenze Python
README.md                 ← documentazione utente
CHANGELOG.md              ← questo file
```

### Dipendenze principali
| Pacchetto | Ruolo |
|-----------|-------|
| faster-whisper | Trascrizione audio (GPU/CPU) |
| demucs | Separazione voce / musica di sottofondo |
| deep-translator | Traduzione testo (Google Translate) |
| edge-tts | Text-to-speech generico (400+ voci Microsoft) |
| TTS (Coqui) | Voice cloning XTTS v2 — opzionale, ~1.8GB |
| pydub | Assemblaggio tracce audio |
| yt-dlp | Download video da YouTube e 1000+ siti |
| torch / torchaudio | Backend CUDA per Whisper, Demucs e XTTS |

### Modelli Whisper supportati
| Modello | Dimensione | Velocità | Accuratezza |
|---------|-----------|----------|-------------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1.5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
