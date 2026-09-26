# Video Translator AI

[Toate limbile](README_LANGUAGES.md) | [English](README.md)

Instrument open-source pentru transcrierea, traducerea și dublarea videoclipurilor
în 26 de limbi. Recunoașterea vocală Whisper rulează local; traducerea și sinteza
vocală depind de motorul ales.

## Pornire rapidă

Windows: rulează `setup_windows.bat` ca administrator și alege `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Adaugă un fișier sau link, alege limbile, vocea și motorul de traducere, apoi
pornește. **Silenzia originale** dezactivează întreaga pistă originală, inclusiv
muzica și efectele. Dublarea live este experimentală; transmisiunile în direct
nu sunt încă acceptate. Documentația completă este în [README-ul englez](README.md).
