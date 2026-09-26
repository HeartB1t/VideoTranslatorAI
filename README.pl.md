# Video Translator AI

[Wszystkie języki](README_LANGUAGES.md) | [English](README.md)

Otwarty program do transkrypcji, tłumaczenia i dubbingu filmów w 26 językach.
Rozpoznawanie mowy Whisper działa lokalnie; tłumaczenie i synteza mowy zależą od
wybranego silnika.

## Szybki start

Windows: uruchom `setup_windows.bat` jako administrator i wybierz `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Dodaj plik lub link, wybierz języki, głos i silnik tłumaczenia, a następnie
rozpocznij. **Silenzia originale** wycisza cały oryginalny dźwięk, w tym muzykę
i efekty. Dubbing na żywo jest eksperymentalny; trwające transmisje nie są jeszcze
obsługiwane. Pełna dokumentacja znajduje się w [README po angielsku](README.md).
