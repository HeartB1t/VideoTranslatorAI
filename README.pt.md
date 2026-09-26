# Video Translator AI

[Todos os idiomas](README_LANGUAGES.md) | [English](README.md)

Ferramenta de código aberto para transcrever, traduzir e dobrar vídeos em 26
idiomas. O reconhecimento de fala Whisper é executado localmente; a tradução e a
síntese de voz dependem do mecanismo escolhido.

## Início rápido

Windows: execute `setup_windows.bat` como administrador e escolha `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Adicione um arquivo ou link, escolha idiomas, voz e mecanismo de tradução e
inicie. **Silenzia originale** silencia toda a faixa de áudio original, incluindo
música e efeitos. A dublagem em tempo real é experimental; transmissões ao vivo
ainda não são compatíveis. Consulte o [README em inglês](README.md).
