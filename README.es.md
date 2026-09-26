# Video Translator AI

[Todos los idiomas](README_LANGUAGES.md) | [English](README.md)

Herramienta de código abierto para transcribir, traducir y doblar vídeos en 26
idiomas. El reconocimiento de voz Whisper se ejecuta localmente; la traducción y
la síntesis de voz dependen del motor elegido.

## Inicio rápido

Windows: ejecuta `setup_windows.bat` como administrador y selecciona
`[1] Install`. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Añade un archivo o enlace, elige idiomas, voz y motor de traducción, y comienza.
**Silenzia originale** silencia toda la pista original, incluida la música y los
efectos. El doblaje en directo es experimental; todavía no se admiten emisiones
en curso. Consulta el [README en inglés](README.md) para la guía completa.
