# 🎬 Video Translator AI

[한국어](../../README.md) | [전체 번역](README.md)

**이 페이지를 읽어보세요:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

기본적으로 API 키가 필요하지 않고 로컬 처리 옵션을 사용하여 비디오를 26개 언어로 자동으로 전사, 번역 및 다시 더빙하는 AI 기반 비디오 음성 더빙 도구입니다. Whisper 음성 인식은 로컬에서 실행됩니다. Edge-TTS, Google Translate 및 DeepL에는 인터넷 연결이 필요합니다. 선택적 기능(DeepL, 말하는 사람 식별(분할))에는 API 키 또는 액세스 토큰이 필요할 수 있습니다.

> **v2.0** - 모듈식 패키지, 로컬 Ollama 번역, 품질 프로필 조정, 설치 가능한 Python 메타데이터 및 실제 모델과의 선택 통합 테스트. 전체 변경 목록은 [GitHub 릴리스](https://github.com/HeartB1t/VideoTranslatorAI/releases) 및 커밋 기록을 참조하세요.

## 작동 원리

1. **기록** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper)는 오디오를 기록합니다(GPU 가속).
2. **음성/음악 분리** - [Demucs](https://github.com/facebookresearch/demucs)는 배경 음악에서 보컬을 분리합니다.
3. **번역** - MarianMT(로컬, 오프라인), Google Translate, DeepL Free 또는 **Ollama LLM**(Qwen3, 슬롯 인식 간결 번역)
4. **말하는 사람 식별(분할)** *(선택 사항)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio)는 각 세그먼트에서 말하는 사람을 식별합니다.
5. **음성 더빙** - [Edge-TTS](https://github.com/rany2/edge-tts)(400개 이상의 음성) 또는 [Coqui XTTS v2](https://github.com/coqui-ai/TTS)(음성 복제, 대화의 각 화자에 대해)
6. **믹싱** - 더빙된 음성과 원래 배경 음악이 믹싱됩니다.
7. **정규화** - -23 LUFS로 정규화된 최종 오디오(EBU R128 방송 표준)
8. **립싱크** *(선택 사항)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip)는 더빙된 오디오에 입 움직임을 동기화합니다.

## 특징

- 🖥️ 테마 GUI(Tkinter) - 명령줄이 필요하지 않습니다. Graphite, Slate, Light 및 Neon 테마, 강조 색상, 텍스트 크기 및 설정 패널을 드래그하여 재정렬할 수 있습니다.
- 🌍 **26개 대상 언어**(언어당 여러 음성 포함)
- 🌐 **26개 언어로 지원되는 UI** - 인터페이스 자체가 언어에 맞게 조정됩니다.
- 🎬 **YouTube 및 URL 지원** - YouTube 링크를 붙여넣고 직접 번역하세요(yt-dlp 제공)
- ▶️ **통합 비디오 플레이어**(libmpv/mpv) - 색상으로 구분된 전송 컨트롤, 재생 목록, A/B 원본 및 더빙된 오디오, 자막 토글, 스냅샷, 전체 화면, 폴더 열기
- ⏱️ **실시간 번역** - 번역된 자막과 YouTube 스타일 지연 슬라이더가 포함된 로컬 파일이나 해결된 주문형 비디오 링크를 시청하세요. 엔진 MarianMT / Google / DeepL / Ollama. 실험적인 음성 더빙에서는 Edge-TTS와 두 번째 mpv 인스턴스를 사용합니다. 음성 오버랩 처리 및 실제 오디오/Windows 수용은 계속 진행 중입니다. 성장하는 라이브 방송은 아직 지원되지 않습니다. [라이브 구현 상태](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26)를 참조하세요.
- 🎵 Demucs를 통한 음성/음악 분리(배경 음악 유지)
- 🔇 **원본 오디오 음소거**는 실시간 번역 전과 도중에 사용할 수 있으며, 번역된 음성은 들리도록 유지하면서 동영상의 사운드트랙을 무음으로 설정합니다. 원래 오디오를 복원하려면 이 기능을 끄세요. 라이브 세션이 끝나면 재설정됩니다.
- 🧠 **MarianMT** - 완전 로컬, 오프라인 신경 번역(헬싱키-NLP, 요청 속도 제한 없음, API 키 없음)
- 🤖 **Ollama LLM 번역** *(v2.0의 새로운 기능)* - 자연스러운 음성 더빙을 위한 슬롯 인식 간결한 번역을 생성하는 로컬 LLM(Qwen3, Llama, Mistral), 처음 사용 시 모델 자동 감지/설치/시작/가져오기
- 🎙️ **음성 복제** - Coqui XTTS v2는 세그먼트별 적응 속도 및 환각에 대한 다중 시드 재시도를 통해 대상 언어(~1.8GB 모델)의 원본 오디오 음성으로 말하는 사람을 복제합니다.
- 👥 **말하는 사람 식별(분할)** - pyannote-audio 3.1은 말하는 여러 사람을 식별합니다. XTTS는 각 음성을 개별적으로 복제합니다.
- 😋 **립싱크** - Wav2Lip GAN은 입의 움직임을 더빙된 오디오와 동기화합니다(~416MB 모델)
- 🔊 **오디오 정규화** - 자동 -23 LUFS 음량 정규화(EBU R128)
- ✏️ 자막 편집기 - 음성 더빙 전 자막을 검토하고 수정합니다.
- 📦 일괄 처리 - 여러 비디오 또는 URL을 한 번에 번역
- ⚡ CUDA를 통한 GPU 가속(자동으로 CPU로 폴백)
- 📄 선택적 `.srt` 자막 내보내기
- 🔁 **DeepL Free** 번역 엔진(선택 사항 - 월 500,000자, 무료 API 키 필요)
- 🔧 **자동 설치** - 누락된 Python 패키지 및 ffmpeg가 처음 실행 시 자동으로 설치됩니다.

## 지원되는 언어

아랍어, 중국어, 체코어, 덴마크어, 네덜란드어, 영어, 핀란드어, 프랑스어, 독일어, 그리스어, 힌디어, 헝가리어, 인도네시아어, 이탈리아어, 일본어, 한국어, 노르웨이어, 폴란드어, 포르투갈어, 루마니아어, 러시아어, 스페인어, 스웨덴어, 터키어, 우크라이나어, 베트남어

## 음성 카탈로그

Edge-TTS 음성 카탈로그는 `video_translator_gui.py` 상단 근처의 `LANGUAGES`에 정의되어 있습니다. 해당 사전은 `--voice`가 생략된 경우 대상 언어 이름, GUI 음성 라디오 버튼 및 CLI 대체 음성에 대한 진실의 소스입니다.

Claude/프로젝트 유지 관리 노트는 **Voice Catalog Source Of Truth** 아래의 `CLAUDE.md`에 이 위치를 반영하므로 향후 코드 에이전트는 음성을 업데이트할 위치와 README가 사용자를 가리키는 위치를 알 수 있습니다.

## 번역 엔진

| 엔진 | 설정 | 한도 | 품질 |
|--------|-------|--------|---------|
| **Google Translate** *(기본값)* | 없음 | 비공식 스크래핑 - 대용량 비디오에서는 제한될 수 있습니다. | ★★★★ |
| **MarianMT** | 없음 - 처음 사용 시 언어 쌍당 최대 298MB 다운로드 | 없음 - 다운로드 후 완전 오프라인 | ★★★★ |
| **DeepL Free** | [deepl.com](https://www.deepl.com/pro-api)의 무료 API 키 | 500,000자/월 | ★★★★★ |
| **Ollama LLM** *(음성 더빙에 권장 - v2.0의 새로운 기능)* | 최초 사용 시 자동 설치(~1GB Ollama + 5GB 모델) | 없음 - 완전 로컬 | ★★★★★ |

> **MarianMT**는 첫 번째 다운로드 후 로컬로 캐시된 [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) 모델을 사용합니다. 명시적인 소스 언어가 필요합니다(자동 감지는 지원되지 않음 - 소스 언어를 수동으로 선택). 필수 Python 패키지(`sacremoses`, `sentencepiece`)가 누락된 경우 첫 번째 선택 시 자동으로 설치됩니다.

> **Ollama LLM** *(v2.0의 새로운 기능)*은 대상 시간대를 인식하여 번역을 생성하므로 음성 더빙에 권장되는 엔진입니다. MarianMT가 문자 그대로 번역하고 영어보다 최대 25% 더 긴 이탈리아어/스페인어/프랑스어를 생성하는 경우(TTS에서 가청 오디오 압축을 강제) LLM은 음성 전달을 위해 각 세그먼트를 간결하고 자연스럽게 유지하여 소스 대비 0.85-0.95의 일반적인 문자 비율을 달성하라는 메시지를 받습니다. 기본 모델은 `qwen3:8b`(디스크 5.2GB, ~6GB VRAM)입니다. `qwen3:4b`(~3GB)는 경량 옵션이고 `qwen3:14b`는 고품질 옵션입니다. 파이프라인은 Ollama 바이너리를 자동 감지하고 처음 사용할 때 공식 설치 프로그램을 통해 자동 설치하며(동의 팝업 포함) 데몬을 시작하고 선택한 모델을 가져옵니다. 수동 설정이 필요하지 않습니다. 누락된 항목이 있으면 자동으로 Google Translate로 전환됩니다.

## 음성 복제(XTTS v2)

활성화되면 앱은 원본 비디오에서 화자의 음성을 추출하고 이를 참조로 사용하여 대상 언어의 음성을 복제합니다.

- 지원 언어: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- 나머지 9개 언어의 경우 Edge-TTS가 자동으로 대체 언어로 사용됩니다.
- `~/.local/share/tts/`에 처음 사용 시 자동으로 모델(~1.8GB)이 다운로드됨
- **VAD 필터링된 참조**(v1.4): 더 나은 음성 복제 품질을 위해 [silero-vad](https://github.com/snakers4/silero-vad)를 통해 원본 오디오에서 선택된 10~15초의 연속 음성
- **생성 속도** 구성 가능(`xtts_speed`, 기본값 `1.25`): 번역된 텍스트가 소스 슬롯보다 길 때 값이 높을수록 사후 처리 오디오 압축 아티팩트가 줄어듭니다. `~/.config/videotranslatorai/config.json` 또는 CLI `--xtts-speed`를 통해 조정
- CUDA 또는 CPU에서 실행

## 말하는 사람 식별(분할)(pyannote-audio)

활성화되면 앱은 각 세그먼트에서 말하는 사람을 식별합니다. Voice Cloning과 결합하면 각 화자의 음성이 별도로 복제되므로 인터뷰, 팟캐스트, 다인용 비디오에 이상적입니다.

- 무료 [HuggingFace 토큰](https://huggingface.co/settings/tokens)이 필요합니다(일회성 등록).
- **토큰은 OS 키링: Windows Credential Manager, macOS Keychain, Linux Secret Service를 통해 안전하게 저장됩니다**(v1.4). 이전 일반 텍스트 JSON 스토리지에서 자동 마이그레이션
- 첫 번째 다운로드 후에는 완전히 오프라인으로 작동합니다.
- 모델: `pyannote/speaker-diarization-3.1`

## 립싱크(Wav2Lip)

활성화되면 앱은 Wav2Lip GAN을 적용하여 피사체의 입 움직임을 더빙된 오디오와 동기화합니다. 즉, 사람이 번역된 언어를 말하는 것처럼 보입니다.

- 모델(~416MB) 및 저장소는 `~/.local/share/wav2lip/`에 처음 사용 시 자동으로 복제됩니다.
- CUDA(권장) 또는 CPU에서 실행됩니다.
- 처리 시간이 크게 늘어납니다.
- 하나의 얼굴이 선명하게 보이는 동영상에서 가장 잘 작동합니다.

## 요구사항

- Python 3.10+(Windows 설치 프로그램이 3.11.9를 자동으로 프로비저닝)
- Windows 10/11(x64), Linux 또는 macOS
- **NVIDIA GPU를 적극 권장합니다** - 아래 GPU 표를 참조하세요.
- 전체 설치를 위한 20GB의 여유 디스크 공간(PyTorch CUDA, Whisper Large-v3, XTTS, Wav2Lip)

> **ffmpeg 및 모든 Python 패키지는 누락된 경우 처음 시작할 때 자동으로 설치됩니다**. 수동 설정이 필요하지 않습니다.

**선택적 시스템 종속성** - `rubberband-cli`(Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). 설치되면 프로필 제어 품질 대역(기본값 1.15-1.50, 하드 콘텐츠의 경우 최대 1.65)에서 피치 보존 시간 확장에 사용되어 복제된 XTTS 음성에서 잔여 "칩멍크" 효과를 제거합니다. 파이프라인은 변경 없이 실행됩니다(ffmpeg `atempo`로 자동 대체). 품질 프로필은 이제 극도의 오디오 속도 향상보다 추가 짧은 번역 재시도를 선호합니다.

### GPU 지원

파이프라인은 5개의 GPU 가속 구성 요소(faster-whisper, Demucs, XTTS, Wav2Lip, pyannote)를 사용합니다. GPU 적용 범위는 공급업체마다 동일하지 않습니다.

| GPU | Windows | Linux | 메모 |
|-----|---------|-------|-------|
| **NVIDIA**(RTX 20xx 이상, CUDA 12.4 드라이버) | ✅ 최대 가속 | ✅ 최대 가속 | **권장.** 5개 구성 요소는 모두 GPU에서 실행됩니다. |
| **AMD**(라데온) | ⚠️ 불완전함(DirectML은 XTTS 및 faster-whisper를 지원하지 않음) | ⚠️ 부분적(ROCm은 Demucs/XTTS/pyannote에서 작동하지만 faster-whisper는 CUDA만 지원함) | 작동하지만 Whisper 전사가 CPU에 유지되어 총 시간을 지배합니다. |
| **Intel Arc** | ⚠️ 미성숙한 PyTorch XPU 지원 | ⚠️동일 | 테스트되지 않았습니다. |
| **없음(CPU만 해당)** | ✅ 작동함 | ✅ 작동함 | 실시간보다 **10-20× 느릴** 것으로 예상됩니다. 5분 길이의 클립을 Whisper Large-v3로 복사하는 데만 50분 이상이 걸릴 수 있습니다. |

**권장 NVIDIA VRAM:**

| VRAM | 대표적인 그래픽 카드 | 경험 |
|------|---------------|-----------|
| 6GB | GTX 1660, RTX 2060 | 사용 가능, XTTS + Wav2Lip을 동시에 실행할 수 없음 |
| 8GB | RTX 3060 Ti, 4060 | 전체 파이프라인, 마진 없음 |
| **12GB+** | **RTX 3060 12GB, 4070, 4080** | **권장 - 편안함** |
| 24GB | RTX 3090, 4090 | 대규모 배치를 위한 예비 용량 |

## 설치

### Windows

1. 이 저장소를 복제하거나 다운로드하세요.
2. `setup_windows.bat`를 마우스 오른쪽 버튼으로 클릭 → **관리자 권한으로 실행** → 메뉴에 `[1] Install`가 표시됩니다.
3. 설치 프로그램이 자동으로 다음을 수행합니다.
   - Python 3.11이 없으면 설치합니다(시스템 전체).
   - Git for Windows가 없으면 설치합니다.
   - 모든 Python 종속 항목(PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps 등)을 설치합니다.
   - ffmpeg 다운로드 및 설치
   - 통합 비디오 플레이어(python-mpv 및 `mpv-runtime`의 libmpv 빌드)를 설치합니다. 이 단계는 선택 사항입니다. 실패하면 다른 모든 것이 작동하고 플레이어 창에서 누락된 내용을 설명합니다.
   - **공용 데스크톱 바로가기** 생성(PC의 모든 Windows 계정에 표시)

> 설치 프로그램은 **다중 사용자**입니다. 모든 것이 `%ProgramFiles%\VideoTranslatorAI` 아래 시스템 전체에 설치되며 컴퓨터의 모든 Windows 사용자는 바로 가기가 준비된 것을 찾습니다. VS C++ 빌드 도구는 **더 이상 필요하지 않습니다** - 유지 관리되는 `coqui-tts` 포크는 사전 컴파일된 Python 휠 패키지를 제공합니다.

### 리눅스/맥OS

```bash
# 저장소 복제
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# 선택 사항: 테스트된 NVIDIA CUDA 12.4 PyTorch 스택을 전면에 설치합니다.
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# 선택 사항: GUI를 허용하는 대신 모든 Python 런타임 패키지를 사전 설치합니다.
# 처음 실행 시 누락된 패키지 설치
pip install --break-system-packages -r requirements.txt

# 선택 사항: 통합 비디오 플레이어(배포판의 libmpv, PyPI의 python-mpv)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# 선택 사항: 프로젝트를 편집 가능한 Python 패키지로 설치
pip install --break-system-packages --no-deps -e .

# 소스에서 실행
python video_translator_gui.py

# 또는 편집 가능/패키지 설치 후
videotranslatorai
videotranslatorai --preflight
```

> 처음 실행 시 GUI는 누락된 패키지(faster-whisper, Demucs, Edge-TTS 등)를 감지하고 자동으로 설치하여 출력을 로그 창으로 스트리밍합니다. ffmpeg는 `apt-get` / `dnf` / `pacman`(Linux)를 통해 자동으로 설치되거나 GitHub(Windows)에서 다운로드됩니다.

> 헤더에는 **플레이어** 배지가 표시됩니다. libmpv 또는 python-mpv가 누락된 경우 왼쪽 창에 누락된 항목이 표시되고 **플레이어 설치**가 제공됩니다. Linux에서는 pkexec(이후 `sudo -n`)를 통해 패키지 관리자를 사용하고 둘 다 작동하지 않으면 수동 명령을 표시합니다. Windows에서는 현재 사용자(약 32MB)에 대한 libmpv를 다운로드하기 전에 묻습니다.

### 요구 사항 프로필

| 파일 | 목적 |
|------|---------|
| `requirements.txt` | 전체, 이전 버전과 호환되는 런타임 설치. |
| `requirements-core.txt` | GUI/CLI에서 사용되는 기본 파이프라인 패키지입니다. |
| `requirements-optional.txt` | XTTS, MarianMT 토크나이저, 분할, VAD, 키링. |
| `requirements-wav2lip.txt` | Wav2Lip 런타임 및 얼굴 감지 스택(`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch 스택은 NVIDIA CUDA 12.4 휠로 테스트되었습니다. |
| `requirements-player.txt` | 통합 비디오 플레이어: python-mpv(시스템 또는 Windows 설치 프로그램의 libmpv 필요) |
| `requirements-dev.txt` | CI/단위 테스트에서 사용되는 경량 종속성입니다. |

## 제거

### Windows

`setup_windows.bat`를 실행하고(마우스 오른쪽 버튼 클릭 → **관리자 권한으로 실행**) 메뉴에서 `[3] Uninstall`를 선택합니다. 세 가지 제거 하위 모드가 제공됩니다.

| 모드 | 관리자 필요 | 범위 |
|------|----------------|-------|
| **[1] 전체 제거 - 한 번의 클릭** | ✅ | 앱 폴더, 공개 데스크톱 바로가기, 시스템 PATH에서 ffmpeg, 모든 사용자의 HF 모델 캐시(Whisper/XTTS) 및 구성(`HF token`), 설치 프로그램에서 설치한 모든 Python AI 패키지를 제거합니다. 마지막에는 레지스트리 자동 제거 문자열을 통해 **Python 3.11** 및 **Git for Windows**를 자동으로 제거할지 여부도 묻습니다(선택). |
| **[2] 현재 사용자만 해당** | ❌ | 실행 중인 사용자의 VTAI 구성, HF/XTTS 캐시 및 레거시 사용자별 설치만 제거합니다. **시스템 전체 설치를 그대로 유지**하므로 PC의 다른 Windows 계정이 앱을 계속 사용할 수 있습니다. |
| **[3] 사용자 정의 - 세분화됨** | ✅ 시스템 항목의 경우, ❌ 사용자 항목의 경우 | 각 범주에 대한 Y/N 프롬프트: 앱 폴더, 바로가기, 컴퓨터 PATH, 사용자별 레거시 설치, 사용자별 구성/캐시, 그룹화된 Python 패키지(TTS, PyTorch 스택, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, 파이프라인 유틸리티), 마지막으로 선택적 Python 3.11 및 Git. |

**자동으로 제거되지 않음:** Visual Studio C++ 빌드 도구(이전 실행에 있는 경우). 원하는 경우 Windows 설정에서 *앱 및 기능*을 사용하여 수동으로 제거하세요.

### 리눅스/맥OS

전용 제거 프로그램 없음 - 수동으로 제거:

```bash
# GUI의 자동 설치 프로그램으로 설치된 Python 패키지
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# 사용자 데이터 및 모델 캐시
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # 구성(테마, 패널 순서, 설정)
rm -f  ~/.videotranslatorai_config.json     # 버전 <= 1.9의 레거시 구성(있는 경우)
```

## 사용법

### 진단

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

번역을 시작하거나 아무것도 설치하지 않고 로컬 환경 진단을 실행합니다. `--preflight-lipsync`는 ​​필요에 따라 Wav2Lip 얼굴 패키지를 처리하며 이는 **립싱크**를 활성화하기 전에 유용합니다. GUI는 로그 패널의 **진단** 버튼에서 동일한 기본 검사를 표시합니다. `--preflight-player`는 필요에 따라 통합 비디오 플레이어(python-mpv 및 로드 가능한 libmpv)를 처리합니다. `python -m videotranslator.libmpv_runtime check`는 libmpv만 조사합니다(종료 0은 준비되어 있고 2는 사용할 수 없음).

### GUI

```bash
python video_translator_gui.py
```

**레이아웃:** 일괄 번역 설정은 설정 패널 스택으로 오른쪽 열에 있습니다: **입력**, **번역**, **워크플로 프로필**, **시작** 및 축소 가능한 고급 섹션(모델, 번역 엔진, 오디오, 음성 복제, 립싱크, 분할, 옵션, 핫워드). 왼쪽의 넓은 영역은 **통합 비디오 플레이어**(전송, 재생 목록, A/B 원본 대 더빙된 오디오, 자막, 스냅샷, 전체 화면)이며 그 아래에 **실시간 번역** 막대가 있습니다. 제목을 기준으로 카드를 드래그하거나 **기타 핸들을 사용하여 열 위나 아래로 이동하세요. 주문이 저장되고(`ui_panel_order`) 다음 시작 시 복원됩니다. 하단의 로그 패널은**로그 숨기기**를 통해 숨길 수 있습니다. 시작 시 창이 현재 모니터(포인터 아래에 있는 모니터) 중앙에 열리고 최대화되므로 다중 모니터 설정에서 잘 작동합니다.

**비디오 비디오 플레이어 컨트롤:** 아이콘은 선택한 강조 색상과 관계없이 모든 테마에서 일관된 기능 색상을 사용합니다.

| 제어 | 색상 |
|---------|--------|
| 비디오 재생 | 녹색 |
| 일시 정지(재생 중 재생 대체) | 호박색 |
| 재생 중지 | 산호빛 레드 |
| 이전 / 뒤로 10초 / 앞으로 10초 / 다음 | 블루 |
| 스냅샷 | 보라색 |
| 폴더 열기 | 골드 |

마우스를 올리면 미묘한 색조의 배경이 추가됩니다. 사용할 수 없는 컨트롤은 중립적입니다. 중지 후에도 재생 목록 탐색을 계속 사용할 수 있습니다. 도구 설명과 키보드 포커스 표시기는 계속 사용할 수 있으므로 색상이 작업을 식별하는 유일한 방법은 아닙니다.

**로컬 파일에서:**
1. 하나 이상의 비디오 파일을 선택하려면 **추가**를 클릭하세요.
2. 소스 및 타겟 언어 선택
3. **모델** 섹션을 열고 Whisper 모델을 선택합니다(`small`는 속도/정확도의 균형이 잘 맞습니다).
4. 음성을 선택하고 필요한 경우 TTS 속도를 조정하세요.
5. *(선택 사항)* **번역 엔진**에서 **Google**(기본값), **MarianMT**(로컬/오프라인), **DeepL Free** 또는 **Ollama LLM**(로컬, 음성 더빙에 권장)을 선택합니다.
6. *(선택 사항)* **음성 복제**(XTTS v2) 및/또는 **말하는 사람 식별(분할)** 활성화
7. *(선택 사항)* **립싱크** 활성화(Wav2Lip)
8. **번역 시작**을 클릭하세요.

**YouTube(또는 지원되는 사이트)에서:**
1. **URL** 필드에 하나 이상의 URL을 붙여넣습니다(한 줄에 하나씩).
2. 평소대로 언어, 모델, 음성을 구성하세요.
3. **⬇ 다운로드 및 번역**을 클릭하세요.

> yt-dlp는 YouTube, Vimeo, Twitter/X, TikTok 및 [1000개 이상의 기타 사이트](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)를 지원합니다.

> ⚠️ **공정 사용 고지:** yt-dlp를 통해 동영상을 다운로드하는 것은 YouTube와 같은 플랫폼에서 자동 액세스로 간주되며 서비스 약관을 위반할 수 있습니다. 동일한 IP 주소를 과도하게 사용하거나 반복적으로 사용하면 임시 차단이 발생할 수 있습니다(HTTP 429/로그인 필요 오류). 다운로드에 실패하면 VPN을 사용하거나 IP를 교체하세요. 이 도구는 개인적이고 비상업적인 용도로만 사용하도록 만들어졌습니다. 번역된 콘텐츠를 재배포하면 저작권이 침해될 수 있습니다. 항상 원본 작성자의 권리를 존중하세요.

### 실시간 번역(자막 및 실험적인 음성 더빙)

번역된 자막과 선택적 음성 번역이 포함된 로컬 파일이나 해결된 주문형 비디오 링크를 시청하세요. 플레이어 아래의 막대를 사용하세요.

**링크에서:**

1. **URL** 필드에 링크를 붙여넣으세요.
2. 출발어와 도착어를 설정하고 음성을 선택한 후 **지연** 슬라이더를 조정하세요.
3. **더빙된 음성** 및/또는 **자막**을 선택하세요.
4. 번역된 음성만 들으려면 시작하기 전에 **원본 오디오 음소거**를 선택하세요(이탈리아어: **Silenzia originale**, 자막 확인란 옆)
5. **실시간 번역**을 클릭하세요. 링크가 확인되고 번역이 시작됩니다.

**로드된 파일에서:** 플레이어에서 동영상을 로드하고(입력 -> 추가 후 선택) URL 필드를 비워두고 동일한 라이브 설정을 선택한 다음 **실시간 번역**을 클릭합니다. 필드가 비어 있지 않으면 URL이 우선순위를 갖습니다.

- **엔진:** MarianMT(오프라인, 기본값), Google, DeepL 또는 Ollama. 음성 인식(Whisper)은 로컬에서 실행됩니다. 오프라인 모델은 초기 다운로드가 필요합니다.
- **음성 더빙:** 두 번째 mpv 인스턴스를 통한 실험적인 Edge-TTS 음성 재생. 인터넷 접속이 필요하며 일괄 음성 복제와는 별개입니다.
- **원본 오디오 음소거:** 번역을 시작하기 전과 번역 중에 모두 사용할 수 있습니다. 음악과 효과를 포함한 원본 사운드트랙 전체를 무음으로 설정하지만 번역된 음성은 들을 수 있도록 남겨둡니다. 원본 오디오에서 말하는 사람을 분리하지 않습니다. 사운드트랙을 복원하려면 이 기능을 끄세요. 라이브 세션이 끝나면 재설정됩니다. 플레이어의 스피커 버튼은 이 독립적인 컨트롤이 아닌 일반적인 음소거입니다.
- **일시 중지 및 탐색:** 비디오 플레이어 컨트롤이 라이브 세션에 연결됩니다. 종단 간 오디오 동기화에는 여전히 플랫폼별 승인 테스트가 필요합니다.
- **현재 제한 사항:** 클립 오버랩/페이드 처리, 오디오 타이밍 보정 및 Windows 승인은 계속 열려 있습니다. 성장하는 라이브 방송은 아직 지원되지 않습니다. 라이브 모드 레이블은 방송이 성장함에 따라 수집을 지원한다는 의미는 아닙니다. [구현현황 및 남은 작업](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26)을 확인하세요.

저장된 더빙 영상은 실시간 미리보기 대신 **다운로드 및 번역** / **번역 시작**을 이용하세요.

### 번역 엔진 블록 및 VPN

서로 다른 수정 사항을 적용하여 두 가지 다른 차단이 발생할 수 있습니다.

| 블록 | 증상 | 수정 |
|-------|---------|-----|
| **다운로드**(yt-dlp) | "봇이 아닌지 확인하려면 로그인하세요.", HTTP 429 | **VPN** / IP를 회전하거나 브라우저에서 YouTube에 로그인하세요(쿠키는 자동으로 읽혀집니다) |
| **번역**(Google 무료 엔드포인트) | "Google Translate는 번역할 수 없습니다... 요청 속도가 제한/차단되었습니다." | **MarianMT**(오프라인) 또는 **Ollama**(로컬)를 사용하세요. 요청 속도 제한이 없습니다. VPN도 도움이 됩니다. 이제 Google이 차단되면 일괄 흐름이 **자동으로 MarianMT로 돌아갑니다**. |

### 테마 및 외관

헤더에 있는 톱니바퀴 아이콘을 클릭하여 **설정**을 엽니다.

- **테마**: 자동(OS 어두운/밝은 모드를 따름), Graphite(기본값), Slate, Light, Neon.
- **악센트 색상**: 테마별 기본값 또는 파란색, 청록색, 보라색, 녹색, 호박색, 장미입니다.
- **텍스트 크기**: 작음, 보통, 큼, 매우 큼.
- **인터페이스 언어**: 26개 언어.

변경 사항은 다시 시작하지 않고 즉시 적용되며 구성 파일(`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`)에 저장됩니다. **기본값 복원**은 Graphite 테마, 기본 악센트, 일반 텍스트 크기 및 설정 패널의 기본 순서를 다시 가져옵니다.

### 명령줄

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**모든 옵션:**

| CLI 옵션 | 설명 | 기본값 |
|------|-------------|---------|
| `--lang-source` | 소스 언어(자동 감지용 `auto`) | `auto` |
| `--lang-target` | 대상 언어 코드(예: `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS 음성 이름 | auto |
| `--model` | Whisper 모델 (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS 속도 조정(예: `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` 또는 `deepl` | `google` |
| `--deepl-key` | DeepL Free API 키 | - |
| `--diarize` | 말하는 사람의 식별을 활성화합니다(분할)(pyannote) | - |
| `--hf-token` | 분할을 위한 HuggingFace 토큰 | - |
| `--lipsync` | 음성 더빙 후 Wav2Lip 립싱크 적용 | - |
| `--subs-only` | `.srt`만 생성, 음성 더빙 건너뛰기 | - |
| `--no-subs` | `.srt` 생성 건너뛰기 | - |
| `--no-demucs` | 음성/음악 분리 건너뛰기 | - |
| `--output` / `-o` | 출력 파일 경로 | auto |
| `--output-dir` | 번역된 파일을 위한 폴더(Windows 및 Linux 한 곳) | `<videos>/VideoTranslatorAI` |
| `--batch` | 여러 파일 처리 | - |

### 실제 모델과의 통합 테스트

기본 테스트 스위트는 실제 모델 다운로드와 긴 GPU 작업을 방지합니다. 설치된 로컬 스택에 대해 옵트인 경험적 검사를 실행하려면 다음을 수행하십시오.

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

이러한 검사는 실제 Wav2Lip 가져오기, Torch CUDA 가용성, Ollama 데몬 가용성 및 합성 음성의 faster-Whisper를 검증합니다. 로컬 드라이버/데몬/모델 상태가 준비되지 않은 경우 의도적으로 실패하거나 건너뜁니다.

**예:**

```bash
# 현지 MarianMT를 사용하여 이탈리아어 비디오를 영어로 번역하세요.
# (처음 사용 시 최대 298MB 모델을 다운로드한 후 완전히 오프라인으로 다운로드)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# 음성 복제 + 말하는 사람 식별(분할)을 통한 번역
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# 립싱크를 사용하여 번역
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# 자막만(음성 더빙 없음)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper 모델

| 모델 | 크기 | 속도 | 정확도 |
|-------|------|-------|----------|
| tiny | 75MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465MB | ⚡⚡ | ★★★☆ |
| medium | 1.5GB | ⚡ | ★★★★ |
| large-v2/v3 | 3GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1.6GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo`는 `large-v3`(4 디코더 레이어 대 32 레이어)의 증류 버전으로 대략 `medium` 등급 속도에서 거의 큰 품질을 제공합니다. 전사 속도가 중요한 경우 최신 GPU에 기본값을 권장합니다. 다국어 자료의 품질 저하가 미미합니다.

> 모델은 처음 사용할 때 자동으로 다운로드됩니다.

## 독립형 모듈 CLI

모듈식 패키지는 전체 파이프라인을 실행하지 않고도 직접 호출할 수 있는 4가지 사용자 대상 도구를 제공합니다.

```bash
# 얼굴 존재 여부를 확인하기 위해 비디오를 미리 비행합니다(Wav2Lip이 없으면 건너뜁니다).
python3 -m videotranslator.face_detector path/to/video.mp4
# 출구 0 = 얼굴 있음, 출구 1 = 얼굴 없음

# build_dubbed_track에서 생성된 *_metrics.csv를 분석합니다.
# pre_stretch_ratio의 P50/P75/P90/P95, 가청 대역 분석,
# 엔진 사용량을 늘리고 대상 텍스트와 함께 상위 N개의 최악의 이상값을 표시합니다.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# TTS용 텍스트를 삭제합니다(콜론, 세미콜론, 줄임표, 대시 다시 작성).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# TTS를 실행하기 전에 .srt 또는 .json 세그먼트 파일에서 음성 더빙 난이도를 추정하세요.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

각 도구에는 전체 옵션을 위한 `-h`/`--help`가 있습니다. 이는 자체 포함되어 있으며 음성 더빙 파이프라인이 의존하는 동일한 모듈을 재사용하므로 출력이 런타임과 일관되게 유지됩니다.

## 라이센스

MIT

### 타사 구성요소

저장소 코드는 MIT입니다. 설치 프로그램은 설치 시 자체 소스에서 아래 구성 요소를 다운로드합니다. 프로젝트는 이를 재배포하지 않습니다.

- **libmpv** (https://github.com/mpv-player/mpv), 통합 비디오 플레이어의 엔진입니다. Windows: zhongfly(https://github.com/zhongfly/mpv-winbuild)의 LGPL 빌드가 먼저 시도됩니다. shinchiro(https://sourceforge.net/projects/mpv-player-windows/files/libmpv/)의 고정된 GPL 빌드가 대안입니다. `mpv-runtime\BUILD.txt`는 ​​소스, 라이센스 버전 및 mpv 커밋을 기록하고 라이센스 텍스트는 DLL 옆에 있습니다. Linux: 배포 패키지(`libmpv2`, `libmpv1`, `mpv-libs` 또는 `mpv`).
- libmpv 내부의 **FFmpeg**(libmpv 빌드 이후 LGPL 또는 GPL).
- **python-mpv**(PyPI의 `mpv`), GPLv2+ 또는 LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03(LGPL), Windows 설치 프로그램에서 libmpv를 추출하고 나중에 삭제하는 데 사용됩니다.
- **Vulkan 로더**(Khronos, MIT 및 Apache-2.0)는 `vulkan-1.dll`가 누락된 경우에만 Windows에 다운로드됩니다.
- **edge-tts** (LGPLv3), 음성 더빙 파이프라인에서 사용됩니다.
- **MarianMT 모델**(Helsinki-NLP), 자체 라이선스(`opus-mt` 모델의 경우 Apache-2.0, `opus-mt-tc-big`의 경우 CC-BY-4.0)에 따라 처음 사용 시 Hugging Face Hub에서 다운로드됩니다.
