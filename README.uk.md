# Video Translator AI

[Усі мови](README_LANGUAGES.md) | [English](README.md)

Інструмент із відкритим кодом для транскрибування, перекладу й озвучення відео
26 мовами. Розпізнавання мовлення Whisper працює локально; переклад і синтез
мовлення залежать від вибраного рушія.

## Швидкий старт

Windows: запустіть `setup_windows.bat` від імені адміністратора та виберіть
`[1] Install`. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Додайте файл або посилання, виберіть мови, голос і рушій перекладу та почніть.
**Silenzia originale** вимикає всю оригінальну звукову доріжку, включно з музикою
та ефектами. Дубляж наживо експериментальний; поточні трансляції поки не
підтримуються. Повна документація є в [README англійською](README.md).
