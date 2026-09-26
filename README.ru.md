# Video Translator AI

[Все языки](README_LANGUAGES.md) | [English](README.md)

Открытый инструмент для расшифровки, перевода и озвучивания видео на 26 языках.
Распознавание речи Whisper выполняется локально; перевод и синтез речи зависят
от выбранного движка.

## Быстрый запуск

Windows: запустите `setup_windows.bat` от имени администратора и выберите
`[1] Install`. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Добавьте файл или ссылку, выберите языки, голос и движок перевода, затем начните.
**Silenzia originale** отключает всю исходную звуковую дорожку, включая музыку и
эффекты. Озвучивание в реальном времени экспериментальное; текущие трансляции
пока не поддерживаются. Полная документация в [README на английском](README.md).
