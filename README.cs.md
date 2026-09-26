# Video Translator AI

[Všechny jazyky](README_LANGUAGES.md) | [English](README.md)

Open-source nástroj pro přepis, překlad a dabing videí do 26 jazyků. Rozpoznávání
řeči Whisper běží místně; překlad a syntéza hlasu závisí na zvoleném enginu.

## Rychlý start

Windows: spusťte `setup_windows.bat` jako správce a zvolte `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Přidejte soubor nebo odkaz, vyberte jazyky, hlas a překladač a spusťte překlad.
Volba **Silenzia originale** ztlumí celý původní zvuk včetně hudby a efektů.
Živý dabing je experimentální a probíhající vysílání zatím není podporováno.
Úplné informace jsou v [anglickém README](README.md).
