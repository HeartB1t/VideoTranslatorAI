# Video Translator AI

[Alle språk](README_LANGUAGES.md) | [English](README.md)

Åpen kildekode-verktøy for transkripsjon, oversettelse og dubbing av videoer på
26 språk. Whisper talegjenkjenning kjøres lokalt; oversettelse og talesyntese
avhenger av valgt motor.

## Hurtigstart

Windows: kjør `setup_windows.bat` som administrator og velg `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Legg til en fil eller lenke, velg språk, stemme og oversettelsesmotor, og start.
**Silenzia originale** demper hele det opprinnelige lydsporet, inkludert musikk og
effekter. Direktedubbing er eksperimentell; direktesendinger støttes ikke ennå.
Se [README på engelsk](README.md) for full dokumentasjon.
