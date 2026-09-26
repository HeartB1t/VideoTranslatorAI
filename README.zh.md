# Video Translator AI

[所有语言](README_LANGUAGES.md) | [English](README.md)

开源视频转录、翻译和配音工具，支持 26 种语言。Whisper 语音识别在本地运行；翻译和语音合成取决于所选引擎。

## 快速开始

Windows：以管理员身份运行 `setup_windows.bat`，选择 `[1] Install`。Linux/macOS：

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

添加视频或链接，选择语言、语音和翻译引擎，然后开始翻译。**Silenzia
originale** 会静音整条原始音轨，包括音乐和音效。实时配音仍属实验功能，暂不支持正在进行的直播。完整技术说明、硬件要求和许可证请见[英文 README](README.md)。
