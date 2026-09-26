# 🎬 Video Translator AI

[Tutte le lingue](README_LANGUAGES.md) | [English](README.md)

[![test](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Strumento open source per trascrivere, tradurre e doppiare video in 26 lingue.
Il riconoscimento vocale Whisper viene eseguito localmente. Traduzione e sintesi
vocale possono usare servizi online oppure modelli locali, secondo il motore
scelto. Non serve una chiave API per iniziare; DeepL e la diarizzazione degli
speaker sono funzioni opzionali che possono richiederla.

Questa pagina è una guida rapida in italiano. Il [README inglese](README.md)
contiene il riferimento tecnico completo, le tabelle hardware, le opzioni CLI,
i requisiti dettagliati e le licenze delle dipendenze.

## Funzionalità

- Interfaccia grafica Tkinter disponibile in 26 lingue, con temi e pannelli
  riordinabili.
- Elaborazione di file video, batch e link supportati da yt-dlp, incluso YouTube.
- Sottotitoli tradotti e doppiaggio vocale con Edge-TTS; clonazione opzionale
  della voce con Coqui XTTS v2.
- Separazione di voce e musica con Demucs, diarizzazione opzionale e sincronizzazione
  labiale opzionale con Wav2Lip.
- Traduzione con Google, MarianMT locale, DeepL Free oppure Ollama locale.
- Player mpv integrato con playlist, sottotitoli, fullscreen e confronto A/B.
- Traduzione in tempo reale sperimentale per file locali e video on-demand
  risolti da URL. Le dirette in corso non sono ancora supportate.
- Comando **Silenzia originale** per evitare il fastidio della doppia voce:
  silenzia l'intera colonna sonora originale, non soltanto il parlato.

I controlli del player sono colorati per funzione: Play verde, Pausa ambra, Stop
corallo, navigazione blu, snapshot viola e apertura cartella oro. La sincronizzazione
audio live è ancora sperimentale; consulta lo [stato dei lavori](docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

## Lingue di traduzione

Arabo, cinese, ceco, danese, olandese, inglese, finlandese, francese, tedesco,
greco, hindi, ungherese, indonesiano, italiano, giapponese, coreano, norvegese,
polacco, portoghese, rumeno, russo, spagnolo, svedese, turco, ucraino e vietnamita.
Le voci disponibili dipendono dal motore di sintesi scelto.

## Installazione rapida

### Windows

1. Scarica o clona il repository.
2. Avvia `setup_windows.bat` come amministratore.
3. Scegli `[1] Install` e avvia l'app dal collegamento creato.

### Linux e macOS

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Per usare il player integrato su Linux installa anche libmpv e i requisiti del
player. La GPU NVIDIA è consigliata, ma non obbligatoria; senza GPU l'elaborazione
può essere molto più lenta. Un'installazione completa richiede circa 20 GB liberi.

## Uso rapido

1. Aggiungi un file alla sezione **Input**, oppure incolla un link nel campo URL.
2. Seleziona le lingue, la voce e il motore di traduzione.
3. Facoltativamente, attiva sottotitoli, doppiaggio, clonazione vocale o lip sync.
4. Avvia **Traduci** per creare il file, oppure **Traduci in tempo reale** per
   ascoltare la traduzione durante la riproduzione.

Per sentire meglio il doppiaggio attiva **Silenzia originale** prima o durante
la sessione live. Il comando silenzia anche musica ed effetti originali; il
pulsante altoparlante del player, invece, è il mute generale.

## Motori di traduzione

| Motore | Elaborazione | Note |
|---|---|---|
| Google Translate | Online | Nessuna configurazione; può essere limitato. |
| MarianMT | Locale | Scarica il modello della coppia linguistica al primo uso. |
| DeepL Free | Online | Richiede una chiave API e rispetta i limiti del piano. |
| Ollama | Locale | Richiede spazio disco e risorse hardware per il modello. |

Edge-TTS richiede Internet. XTTS v2 è locale e clona la voce, ma supporta solo
una parte delle lingue; per i dettagli consulta il [README completo](README.md).

## Diagnostica

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-player
```

Il controllo verifica l'ambiente senza avviare una traduzione. Per istruzioni
complete su GPU, dipendenze, disinstallazione, CLI e licenze consulta il
[README inglese](README.md).

## Licenza

MIT. Modelli e dipendenze scaricati mantengono le rispettive licenze e condizioni.
