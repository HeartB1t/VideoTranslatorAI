# Video Translator AI

[Alle talen](README_LANGUAGES.md) | [English](README.md)

Open-sourcetool om video's naar 26 talen te transcriberen, vertalen en nasynchroniseren.
Whisper-spraakherkenning draait lokaal; vertaling en spraaksynthese hangen af van
de gekozen engine.

## Snel starten

Windows: voer `setup_windows.bat` als beheerder uit en kies `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Voeg een bestand of link toe, kies talen, stem en vertaalengine en start de taak.
**Silenzia originale** dempt de volledige originele soundtrack, inclusief muziek
en effecten. Live-nasynchronisatie is experimenteel; livestreams worden nog niet
ondersteund. Zie de [Engelse README](README.md) voor alle details.
