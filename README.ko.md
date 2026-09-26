# Video Translator AI

[전체 언어](README_LANGUAGES.md) | [English](README.md)

26개 언어로 동영상을 받아쓰고 번역하며 더빙하는 오픈 소스 도구입니다.
Whisper 음성 인식은 로컬에서 실행되며 번역과 음성 합성은 선택한 엔진에 따라 달라집니다.

## 빠른 시작

Windows에서는 `setup_windows.bat`을 관리자 권한으로 실행하고 `[1] Install`을
선택하세요. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

파일이나 링크를 추가하고 언어, 음성, 번역 엔진을 선택한 뒤 시작하세요.
**Silenzia originale**는 음악과 효과음을 포함한 전체 원본 오디오를 음소거합니다.
실시간 더빙은 실험 기능이며 진행 중인 라이브 방송은 아직 지원하지 않습니다.
전체 문서는 [영문 README](README.md)를 참조하세요.
