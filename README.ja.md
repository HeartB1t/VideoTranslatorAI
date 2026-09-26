# Video Translator AI

[全言語](README_LANGUAGES.md) | [English](README.md)

26言語の動画文字起こし、翻訳、吹き替えを行うオープンソースツールです。
Whisperによる音声認識はローカルで動作し、翻訳と音声合成は選択したエンジンによって異なります。

## クイックスタート

Windowsでは`setup_windows.bat`を管理者として実行し、`[1] Install`を選びます。
Linux/macOSの場合:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

ファイルまたはリンクを追加し、言語、音声、翻訳エンジンを選んで開始します。
**Silenzia originale**は音楽や効果音を含む元の音声全体をミュートします。
リアルタイム吹き替えは実験的機能で、配信中のライブ映像には未対応です。
詳しくは[英語版README](README.md)をご覧ください。
