# TEST PLAN - Collaudo approfondito VideoTranslatorAI v2.1.5

Tracker unico di collaudo funzionale end-to-end di tutti i prodotti del tool.
Avviato 2026-10-21 su v2.1.5 (`4b733c8`, tag `v2.1.5` pubblicato).

## Come leggere questo tracker

**Stato:** `- [ ]` da fare · `- [~]` in corso · `- [x]` PASS · `- [!]` FAIL/anomalia · `- [b]` BLOCCATO (dipendenza mancante) · `- [n/a]` non applicabile su quella piattaforma.

**Piattaforma:** `L` = Linux qui (Kali, RTX 3090, GPU reale) · `W` = Windows sulla VM (CPU, nessuna GPU).

**Tipo:** `U` logica gia' coperta da test unitari (baseline) · `F` collaudo funzionale con input reali · `Q` giudizio di qualita' (ascolto/visione dell'output).

**Dipendenze esterne (dep):** `net` rete/YouTube · `hf` token HuggingFace (pyannote) · `deepl` API key DeepL · `11l` ElevenLabs (A PAGAMENTO, serve OK esplicito per ogni chiamata) · `vbox` server Voicebox in Docker · `ollama` daemon Ollama locale.

Principio guida: la logica e' gia' verde (2057 test unitari su CI, Linux e Windows). Qui si collauda il COMPORTAMENTO REALE con media e servizi veri.

---

## Baseline: logica (gia' verde, da riconfermare su 2.1.5)

- [x] Suite unitaria completa su Linux: 2057 OK, 15 skip (riconfermata su 2.1.5). (L, U)
- [ ] Suite unitaria completa su Windows VM: `python -m unittest discover -s tests`. (W, U)
- [x] CI su `main`: tutti i 5 job verdi, windows-tests compreso. (L+W, U)
- [x] Installer/updater: update 2.1.4 -> 2.1.5 via `setup_windows.bat [2]`, SHA256 verificato, handover ok, RESULT repair complete. (W, F)

---

## 1. Acquisizione input

- [ ] Download YouTube (yt-dlp, client tv/android_vr): scarica un VOD breve e lo traduce. (L+W, F, dep: net)
- [ ] **Diretta YouTube tempo reale** (il fix di 2.1.5): la modalita' live risolve lo stream (itag 18) invece di "Requested format is not available". (L+W, F, dep: net)
- [ ] Download da URL generico non-YouTube. (L, F, dep: net)
- [ ] File locale come sorgente (mp4/mkv/webm). (L+W, F)
- [ ] Nome file da titolo con caratteri strani: nessun path traversal, restrictfilenames. (L, F)

## 2. Estrazione audio

- [ ] Estrazione nei 6 formati (MP3/M4A/Opus/OGG/FLAC/WAV) con bitrate. (L+W, F)
- [ ] Modalita' "solo strumentale" (Demucs rimuove la voce) su video e URL. (L, F+Q)
- [ ] Sorgente non distrutta: suffisso "(extracted)" se output == input. (L+W, F)
- [ ] Batch di piu' input, uno fallito non ferma gli altri, exit code corretto. (L, F)

## 3. Separazione e trascrizione

- [ ] Demucs htdemucs separazione voce/musica, chunking anti-OOM su video lungo. (L, F, GPU)
- [ ] faster-whisper trascrizione GPU, piu' modelli (small/medium/large-v3-turbo). (L, F, GPU)
- [ ] Whisper su CPU (fallback). (W, F)
- [ ] Download modello Whisper con verifica checksum HuggingFace, Cancel. (L+W, F, dep: net)
- [ ] Benchmark modello (load, prima riga, velocita'). (L, F, GPU)
- [ ] Hotwords e hotwords-file. (L, F)
- [ ] Whisper sanity, difficulty detector/profile. (L, F)

## 4. Traduzione (4 motori)

- [ ] MarianMT offline (default): download modello ~298 MB, traduzione IT->EN e altra coppia. (L+W, F+Q, dep: net prima volta)
- [ ] Google Translator: traduzione + gestione rate limit (avviso, non testo lasciato muto). (L, F, dep: net)
- [ ] DeepL Free: con API key, context hint "dubbing register". (L, F, dep: deepl)
- [ ] Ollama (LLM locale): qwen3, slot-aware, length control, cove, thinking on/off. (L, F+Q, dep: ollama)
- [ ] Document context, slot expansion, sentence repair, overlap fade (flag --no-*). (L, F)

## 5. TTS e doppiaggio

- [ ] Edge-TTS: doppiaggio su file, voci multiple, tts-rate. (L+W, F+Q, dep: net)
- [x] XTTS v2 voice cloning: reference VAD, 17 lingue, parametri anti-hallucination, xtts-speed. (L, F+Q, GPU)
  2026-10-24: `zoo_short.mp4` (19 s, voce umana) EN->IT, `--xtts --model small --translation-engine marian`:
  XTTS su CUDA, reference VAD 17,3 s, nessun fallback a Edge-TTS, mp4 con traccia doppiata (-25,9 dB medi)
  + originale, srt IT corretto, 48 s totali. Ascolto: all'operatore (CK-09).
- [ ] XTTS fallback a Edge-TTS su errore. (L, F)
- [ ] ElevenLabs (file e live): chiave in keyring, verifica, scelta voce/modello, fallback a Edge-TTS. (L, F+Q, dep: 11l PAGAMENTO - serve OK)
- [ ] **Voicebox** (server locale): clona profilo, genera per frase, pulisce profili, fallback se server spento. (L, F+Q, dep: vbox)
- [ ] Normalizzazione pyloudnorm -23 LUFS, mix memmap streaming. (L, F)
- [ ] atempo chain, allineamento durata slot. (L, F+Q)

## 6. Diarization e lip sync

- [ ] pyannote 3.1 diarization, speaker propagato a XTTS (multi-voce). (L, F, GPU, dep: hf)
- [x] Wav2Lip GAN lip sync. 2026-10-24, GPU reale: modello `wav2lip_gan.pth` presente, SHA256
  `ca9ab7b7...` = quello fissato nel .bat; dlib 20.0.1 + cv2 4.13.0 OK; download verificato.
  BUG TROVATO E RISOLTO: il lip sync non produceva MAI output perche' `apply_lipsync` lanciava
  Wav2Lip con cwd=`~/.cache/wav2lip` senza creare la sottocartella `temp/` che inference.py usa
  hardcoded (`temp/result.avi`): cv2.VideoWriter falliva in silenzio, il mux finale abortiva
  ('temp/result.avi: No such file or directory', exit 0, nessun outfile) e l'app ripiegava a
  'senza lip sync'. Il test lo mascherava pre-creando `temp/`. Fix: `apply_lipsync` crea
  `work_dir/temp` prima di lanciare; test aggiornato per non pre-crearlo (uccide il mutante).
  Dopo il fix: su un talking-head H.264 il lip sync gira su CUDA (33/33 face + 5/5 inference),
  '-> Lip sync done', frame di output modificato nella bocca (md5 diverso dall'input).
  ALTRI 2 limiti: Wav2Lip non decodifica l'AV1 (0 frame -> ripiego); richiede un volto in OGNI
  frame (zoo panna sugli elefanti -> 'Face not detected' -> ripiego). Il fallback funziona in
  entrambi. (L, F+Q, GPU)
- [ ] Wav2Lip su Windows: path unico, stack dlib/basicsr/facexlib. (W, F)

## 7. Player integrato

- [ ] libmpv carica e riproduce (originale e doppiato), A/B, CC sottotitoli. (L+W, F)
- [ ] Trasporto completo, snapshot, volume, fullscreen, playlist. (L+W, F)
- [ ] Editor sottotitoli: preview, seek, debounce, clamp. (L, F)
- [ ] Auto-install libmpv (Linux apt / Windows dll). (L+W, F)

## 8. Modalita' tempo reale (live)

- [ ] Sottotitoli live su file (decode->VAD->Whisper->traduzione->overlay). (L, F+Q, GPU)
- [ ] Doppiaggio live Edge-TTS (seconda mpv). (L, F+Q, dep: net)
- [ ] Doppiaggio live ElevenLabs. (L, F+Q, dep: 11l PAGAMENTO)
- [ ] Modalita' ritardata con slider delay, crescita buffer 8->30 s. (L, F)
- [x] Switch motore a caldo, circuit breaker online, "Passa a MarianMT". 2026-10-24, GUI reale su Xvfb con Google VERO (audio sink nullo), scenario delayed_switch: Google rate-limited a 10.9 s -> banner `live_warn_rate_limited` + azione `live_btn_switch_marian`; switch a 27 s -> engine marian, traduzione riprende (53 tradotte, 10 doppiate), nessuna raffica 'kept original'. lost=1 su tutta la sessione (tollerato; non e' il repro specifico CR-B resume-under-load). CR-G/CR-B validati. (L, F)
- [x] Pausa/seek collegati alla sessione live, auto-stop a EOF. 2026-10-24, GUI reale su Xvfb (audio al sink nullo), delayed+dub+marian su zoo_short: player_ready, live_started, seek 6->2, pausa 3 s + ripresa (sessione viva), auto-stop pulito a EOF ('source finished and dubbing complete'), ended auto. RESULT tutti True (seeked/paused/resumed/ended/auto_stopped), 0 timeout. (L, F)
- [ ] Mute originale prima e durante. (L, F)
- [ ] Modello pesante Ollama: avviso che non copre gli errori. (L, F)

## 9. GUI, temi, i18n

- [x] Avvio GUI, screenshot, layout P0. 2026-10-24 su Xvfb: layout corretto (player a sinistra, card INPUT/Estrai audio/Traduzione/Profilo a destra), pallini GPU/Ollama/Wav2Lip/Player verdi, transport con CC/A/B/Playlist, log con header di sistema (RTX 3090, torch 2.6.0+cu124, pyannote 3.4.0, edge-tts 7.3.1, mpv 0.41). Screenshot in scratchpad t20/gui_default.png. (L, F)
- [ ] 4 skin (Dex/Handheld/CRT/CRT Amber) + temi auto/light, font OFL. (L+W, F+Q)
- [ ] i18n: cambio lingua, copertura 26 lingue, placeholder uguali. (L+W, F)
- [ ] Pannello log parlante: eventi in tempo reale, colori, dedup, mpv. (L+W, F)
- [ ] Dialoghi: Modelli per questo PC, voice preview, ElevenLabs, Voicebox. (L+W, F)
- [ ] Chiusura con la X di un window manager reale. (L, F)

## 10. CLI

- [ ] Traduzione da CLI con tutti i flag principali (lang, engine, model, voice). (L+W, F)
- [x] --preflight, --preflight-lipsync, --preflight-player: 2026-10-24 tutti Result OK (deps opzionali e required, ffmpeg/ffprobe, rubberband, ollama, libmpv, GPU). (L, F)
- [ ] --extract-audio, --instrumental, --batch, --subs-only, --no-subs. (L, F)

## 11. Modelli, hardware, segreti

- [ ] Selezione modello per questo PC (hardware profile GPU/CPU). (L+W, F)
- [ ] Catalogo modelli, verifica snapshot, pull Ollama. (L, F, dep: net/ollama)
- [ ] Secret in keyring: HF token, ElevenLabs, DeepL, migrazione da JSON. (L+W, F)
- [ ] GPU CUDA 12.4 con fallback CPU (intercetta libcublas). (L, F, GPU)

## 12. Installer / updater / uninstaller (Windows)

- [x] Update 2.1.4 -> 2.1.5 (fatto, pulito). (W, F)
- [ ] Install pulito da zero su Windows pulito. (W, F)
- [ ] Repair su installazione esistente. (W, F)
- [ ] Uninstall granulare (app / Python / Git / Ollama / per-utente). (W, F)
- [ ] Preflight: architettura, disco, internet. (W, F)
- [ ] Verifiche integrita': Wav2Lip SHA256, zip release SHA256. (W, F)

---

## Dipendenze da sbloccare prima del collaudo

- `net`: presente (eth0). YouTube puo' rate-limitare l'IP di casa.
- `hf`: serve un token HuggingFace per pyannote (modello gated). Presente nel keyring? Da verificare.
- `deepl`: serve una API key DeepL Free. Da fornire se si vuole collaudare DeepL.
- `11l`: ElevenLabs e' A PAGAMENTO per carattere. NESSUNA chiamata senza OK esplicito per ogni prova (regola operatore).
- `vbox`: serve un server Voicebox in esecuzione (Docker, engine chatterbox, porta 17493). Non attivo: da tirare su se si vuole il test reale.
- `ollama`: serve il daemon Ollama locale con un modello (es. qwen3:8b).

---

## Piano di esecuzione (parallelo Linux + Windows)

- **Linux (orchestratore, qui):** tutto cio' che e' GPU-bound e il grosso del funzionale (pipeline reale, Demucs, Whisper GPU, XTTS, pyannote, Wav2Lip, live mode su Xvfb, player libmpv, estrazione audio, traduzioni, CLI).
- **Windows (agente Opus 5.5 sulla VM):** suite unitaria, installer/repair/uninstall, GUI/temi/i18n, player su Windows, path/filename, Edge-TTS e Marian su CPU, diretta YouTube. Feature GPU solo in fallback CPU.
- **Consolidamento:** entrambi scrivono gli esiti in questo file (sezioni L e W), l'orchestratore unifica, marca PASS/FAIL/anomalie con evidenze.

## Decisioni aperte per l'operatore (prima del lancio pesante)

1. Budget: il collaudo completo e' multi-ora e multi-agente. Confermi di procedere a tappeto?
2. ElevenLabs (a pagamento): includere il test con chiamate reali (servira' OK puntuale) o saltarlo?
3. Voicebox: tiro su un server Docker reale per il test end-to-end, o lascio "coperto da unit, reale aperto"?
4. Credenziali: c'e' un token HF e una key DeepL utilizzabili, o quei due restano BLOCCATI?
5. Video di prova: usiamo un VOD YouTube breve concordato, o un file locale gia' sulle macchine?

---

## Risultati esecuzione 2026-10-21 (Linux, RTX 3090)

Input: clip generata EN 22 s (parlato edge-tts su immagine fissa). Scope: core senza-credenziali + Ollama + YouTube.

### PASS (Linux)
- [x] Pipeline completa EN->IT, motore Marian: estrai audio -> Demucs -> Whisper small GPU -> MarianMT -> Edge-TTS -> loudnorm -23 LUFS -> atempo/rubberband -> mux. Output video + srt, traduzione IT corretta ("L'antica biblioteca sorgeva ai margini della citta' vecchia..."). Valida in un colpo: estrazione, Demucs, Whisper GPU, Marian, Edge-TTS, loudnorm, stretch, mux, sottotitoli, CLI.
- [x] Traduzione via Ollama (qwen3:8b): motore connesso, slot-aware shrinkage -16%, output completo. NOTA QUALITA': la compressione aggressiva rende la resa piu' spezzata di Marian su questa clip.
- [x] Google Translate: rate-limited dall'IP (esterno, atteso), ma l'app fa FALLBACK automatico a MarianMT con output corretto. Comportamento anti-rate-limit validato.
- [x] Estrazione audio: MP3, OPUS (codec verificato), STRUMENTALE (Demucs rimuove la voce), con naming non distruttivo "(instrumental)".
- [x] Solo sottotitoli (--subs-only): produce solo l'srt, "mode complete".
- [x] Download YouTube reale via app (fix client tv/android_vr): video normale scaricato (22 MB -> mp3). yt-dlp dell'app = nightly 2026.10.10.233141. Il fix di 2.1.5 funziona per lo scaricamento.

### ANOMALIE TROVATE (Linux)
- [x] RISOLTO 2026-10-24 (ambiente): **XTTS voice cloning NON parte** - errore import Numba (`cannot import name '_typeconv' from 'numba.core.typeconv'`, dal numba di SISTEMA in `/usr/lib/python3/dist-packages`). L'app fa fallback a Edge-TTS (corretto), ma il voice cloning XTTS e' inutilizzabile su questa macchina dev finche' non si sistema numba (python3.13 carica il numba di sistema incompatibile, strascico migrazione venv/py3.14). NON e' un bug del prodotto (fallback ok), e' ambiente. Da fixare l'ambiente per poter collaudare XTTS.
- [!] **CLI: traduzione da URL rotta** - dare un URL YouTube alla traduzione da riga di comando stampa "File not found". Causa: `videotranslator/cli.py:325` controlla solo `os.path.exists(f)`, mentre il percorso `--extract-audio` (`cli.py:215`) controlla anche `is_probable_url`. Incoerenza reale: dalla CLI si puo' ESTRARRE audio da un URL ma non TRADURRE da un URL (la GUI invece scarica e traduce). Fix: aggiungere il ramo `is_probable_url` anche al percorso di traduzione.

### Note
- "Me at the zoo" (jNQXAC9IVRw, 2005): "No video formats found" - caso limite di quel video vecchio, non un bug del fix (un video normale scarica bene).
- Preflight CLI: invocazione da chiarire (senza input stampa l'usage); logica coperta dai test unitari.

### Non testato su Linux (motivo)
- Wav2Lip lip sync: serve un video con un VOLTO (la clip di test e' a immagine fissa). Da rifare con un video con volto.
- pyannote diarization: BLOCCATO, manca token HF.
- DeepL: BLOCCATO, manca API key.
- ElevenLabs: saltato (a pagamento, per scelta).
- Live mode / GUI interattiva / player: coperti dai gui-tests CI su Xvfb (verdi); l'acceptance interattiva sul desktop reale resta all'operatore.

### Voicebox reale via Docker (server costruito e healthy)
- [x] INTEGRAZIONE con server REALE: immagine costruita dal repo (nessuna prebuilt), container healthy su `127.0.0.1:17600` (CPU-only). Health check via `VoiceboxClient` OK, richiesta `/generate` inviata, errore HTTP classificato, fallback a Edge-TTS corretto. Chiude il buco "Voicebox validato solo con simulazione" per il layer integrazione/connettivita'.
- [!] GENERAZIONE vocale reale: NON completata. Il modello chatterbox non e' pre-scaricato sul server ("model is not downloaded yet"); l'app prende un HTTP 400 e cade in fallback a Edge-TTS invece di innescare/attendere il download. FINDING: con un Voicebox fresco il modello va pre-scaricato (UI Voicebox o primo generate completo) prima che l'app lo usi; l'app non auto-innesca il download. Download modello chatterbox su CPU = passo pesante, non eseguito in questo giro.

## Risultati Windows (VM, CPU, agente Opus 5.5)

- [x] Versione app installata = 2.1.5 (confermata). Update 2.1.4->2.1.5 gia' verificato in precedenza.
- [x] resolve_stream_url (fix YouTube di 2.1.5) su Windows: risolve il VOD ("Me at the zoo"), nessun "Requested format is not available". yt-dlp nudo invece FALLISCE sullo stesso video -> conferma diretta del valore del fix (la nuova lista client aggira il problema).
- [x] Pipeline CLI leggera (CPU): `--model small --no-demucs --translation-engine marian` en->it su clip generata: whisper-CPU -> Marian -> Edge-TTS -> mux, output mp4 con 2 tracce audio (originale + doppiata). Collaudato il percorso download-less su Windows.
- [x] Estrazione audio CLI mp3 (codec verificato).
- [n/a] Ollama su Windows: non installato sulla VM.
- [!] SUITE unitaria su Windows via SSH: ~2002 pass, ma 33 fail + 1 error TUTTI e SOLI nei moduli GUI/Tk (bevel, gear_icon, player_panel, ui_layout_p0, ui_theme, voice_preview, zz_teardown). Causa: window station non interattiva via SSH; i test GUI NON si auto-skippano headless su Windows (su Linux si'), quindi girano e falliscono. In CI (windows-latest con desktop via Set-DisplayResolution) la stessa suite e' VERDE. DECISIONE OPERATORE: accettare come limite dell'esecuzione via SSH, o trattarlo come gap della suite (dovrebbe skippare senza window station interattiva).
- [!] CONFERMATO anche su Windows: la CLI non accetta un URL come input per la traduzione (`File not found`). Stesso bug di `cli.py:325`.
- [!] MINORE: il flag `-o`/`--output` viene ignorato in modalita' `--extract-audio` (l'output e' salvato accanto all'input col nome derivato, non nel path passato).

## Sintesi findings (ranked)

1. [RISOLTO 2026-10-22] CLI non traduce da URL (`cli.py:325` controllava solo `os.path.exists`, mancava il ramo `is_probable_url` presente a `cli.py:215`). Confermato su Linux E Windows. Aggiunto il ramo `is_probable_url` al percorso di traduzione + 3 test.
2. [RISOLTO 2026-10-24, ambiente] XTTS voice cloning rotto sulla macchina Linux dev. Causa: python3.13 caricava da `/usr/lib/python3/dist-packages` pacchetti compilati solo per CPython 3.14 (numba 0.65.1, poi matplotlib 3.10.9 importato da `TTS/tts/utils/visual.py`; pyannote richiedeva anche pandas). Installati nel site utente di 3.13 `numba 0.63.1` + `llvmlite 0.46.0` e, con `--ignore-installed --no-deps` alle stesse versioni del sistema, `matplotlib 3.10.9`, `contourpy 1.3.3`, `kiwisolver 1.5.1`, `pandas 2.3.3`. numpy invariato (2.3.5). XTTS e pyannote ora si importano; collaudo XTTS reale PASS.
3. [DECISIONE, ambiente/suite] Suite Windows via SSH: 34 test GUI falliscono perche' non si skippano senza window station interattiva (verdi in CI con desktop). Accettare o aggiungere skip headless.
4. [FEATURE-GAP] Voicebox: integrazione col server reale validata; generazione reale bloccata dal modello non pre-scaricato e dall'app che non auto-innesca il download.
5. [RISOLTO 2026-10-22] `-o` ignorato con `--extract-audio`. `extract_music` ora accetta `out_file`; `_run_extract_audio` lo onora per un singolo input e con un batch lo scarta con un avviso esplicito + 1 test.

## Non testato (motivo)
- Wav2Lip: serve un video con un volto (clip di test a immagine fissa). Da rifare con video con volto.
- DeepL, pyannote: BLOCCATI, mancano key DeepL e token HF.
- ElevenLabs: saltato (a pagamento, per scelta operatore).
- GUI interattiva / live / player interattivo: logica verde in CI (gui-tests Xvfb); acceptance interattiva sul desktop reale resta all'operatore.
