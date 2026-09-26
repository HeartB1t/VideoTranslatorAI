# Video Translator AI

[Semua bahasa](README_LANGUAGES.md) | [English](README.md)

Alat sumber terbuka untuk mentranskripsikan, menerjemahkan, dan mengisi suara
video dalam 26 bahasa. Pengenalan ucapan Whisper berjalan secara lokal; terjemahan
dan sintesis suara bergantung pada mesin yang dipilih.

## Mulai cepat

Windows: jalankan `setup_windows.bat` sebagai administrator lalu pilih
`[1] Install`. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Tambahkan file atau tautan, pilih bahasa, suara, dan mesin terjemahan, lalu mulai.
**Silenzia originale** membisukan seluruh audio asli, termasuk musik dan efek.
Dubbing langsung masih eksperimental; siaran langsung belum didukung. Lihat
[README bahasa Inggris](README.md) untuk dokumentasi lengkap.
