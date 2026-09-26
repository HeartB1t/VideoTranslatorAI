# Video Translator AI

[Alle sprog](README_LANGUAGES.md) | [English](README.md)

Open source-værktøj til transskription, oversættelse og dubbing af videoer på 26
sprog. Whisper-talegenkendelse kører lokalt; oversættelse og talesyntese afhænger
af den valgte motor.

## Hurtig start

Windows: kør `setup_windows.bat` som administrator, og vælg `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Tilføj en fil eller et link, vælg sprog, stemme og oversættelsesmotor, og start.
**Silenzia originale** slår hele det oprindelige lydspor fra, også musik og effekter.
Live-dubbing er eksperimentelt; igangværende liveudsendelser understøttes ikke endnu.
Se [README på engelsk](README.md) for tekniske oplysninger og licenser.
