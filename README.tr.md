# Video Translator AI

[Tüm diller](README_LANGUAGES.md) | [English](README.md)

Videoları 26 dilde yazıya dökmek, çevirmek ve seslendirmek için açık kaynaklı
araç. Whisper konuşma tanıma yerel olarak çalışır; çeviri ve ses sentezi seçilen
altyapıya bağlıdır.

## Hızlı başlangıç

Windows: `setup_windows.bat` dosyasını yönetici olarak çalıştırıp `[1] Install`
seçeneğini seçin. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Dosya veya bağlantı ekleyin, dilleri, sesi ve çeviri motorunu seçip başlatın.
**Silenzia originale**, müzik ve efektler dahil tüm özgün sesi kapatır. Canlı
seslendirme deneyseldir; devam eden canlı yayınlar henüz desteklenmiyor. Tam teknik
belgeler için [İngilizce README'ye](README.md) bakın.
