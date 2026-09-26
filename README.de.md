# Video Translator AI

[Alle Sprachen](README_LANGUAGES.md) | [English](README.md)

Open-Source-Werkzeug zum Transkribieren, Übersetzen und Vertonen von Videos in
26 Sprachen. Whisper läuft lokal; Übersetzung und Sprachsynthese hängen von der
gewählten Engine ab.

## Schnellstart

Windows: `setup_windows.bat` als Administrator ausführen und `[1] Install`
wählen. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Datei oder Link hinzufügen, Sprachen, Stimme und Engine auswählen und starten.
**Silenzia originale** schaltet die gesamte Originaltonspur stumm, einschließlich
Musik und Effekten. Live-Vertonung ist experimentell; Livestreams werden noch
nicht unterstützt. Technische Details stehen in der [englischen README](README.md).
