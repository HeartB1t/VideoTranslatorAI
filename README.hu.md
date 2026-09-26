# Video Translator AI

[Összes nyelv](README_LANGUAGES.md) | [English](README.md)

Nyílt forráskódú eszköz videók átírásához, fordításához és szinkronizálásához 26
nyelven. A Whisper beszédfelismerés helyben fut; a fordítás és a beszédszintézis
a kiválasztott motortól függ.

## Gyors indítás

Windows: futtasd rendszergazdaként a `setup_windows.bat` fájlt, majd válaszd a
`[1] Install` lehetőséget. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Adj hozzá fájlt vagy hivatkozást, válassz nyelvet, hangot és fordítómotort, majd
indítsd el a fordítást. A **Silenzia originale** a teljes eredeti hangsávot
elnémítja, zenével és effektekkel együtt. Az élő szinkron kísérleti; az élő
közvetítések még nem támogatottak. Teljes dokumentáció az [angol README-ben](README.md).
