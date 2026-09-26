# Video Translator AI

[Alla språk](README_LANGUAGES.md) | [English](README.md)

Verktyg med öppen källkod för transkribering, översättning och dubbning av video
på 26 språk. Whisper-taligenkänning körs lokalt; översättning och talsyntes beror
på vald motor.

## Snabbstart

Windows: kör `setup_windows.bat` som administratör och välj `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Lägg till en fil eller länk, välj språk, röst och översättningsmotor och starta.
**Silenzia originale** stänger av hela originalljudspåret, även musik och effekter.
Live-dubbning är experimentell; pågående livesändningar stöds inte ännu. Se
[README på engelska](README.md) för fullständig dokumentation.
