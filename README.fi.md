# Video Translator AI

[Kaikki kielet](README_LANGUAGES.md) | [English](README.md)

Avoimen lähdekoodin työkalu videoiden litterointiin, kääntämiseen ja jälkiäänitykseen
26 kielellä. Whisper-puheentunnistus toimii paikallisesti; käännös ja puhesynteesi
riippuvat valitusta moottorista.

## Pika-aloitus

Windows: suorita `setup_windows.bat` järjestelmänvalvojana ja valitse
`[1] Install`. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Lisää tiedosto tai linkki, valitse kielet, ääni ja käännösmoottori ja käynnistä.
**Silenzia originale** mykistää koko alkuperäisen ääniraidan, myös musiikin ja
tehosteet. Reaaliaikainen jälkiäänitys on kokeellinen eikä suoria lähetyksiä vielä
tueta. Katso [englanninkielinen README](README.md) teknisistä tiedoista.
