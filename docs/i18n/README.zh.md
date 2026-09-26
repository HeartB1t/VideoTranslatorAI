# 🎬 Video Translator AI

[中文](../../README.md) | [所有翻译](README.md)

**阅读此页面：** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

由 AI 驱动的视频语音配音工具，可自动将视频转录、翻译和重新配音为 26 种语言，具有本地处理选项，默认情况下无需 API 密钥。 Whisper 语音识别本地运行； Edge-TTS、Google Translate 和 DeepL 需要互联网连接。可选功能（DeepL、说话人识别（分类））可能需要 API 密钥或访问令牌。

> **v2.0** - 模块化包、本地 Ollama 翻译、质量配置文件编排、可安装的 Python 元数据以及选择与真实模型的集成测试。请参阅 [GitHub 版本](https://github.com/HeartB1t/VideoTranslatorAI/releases) 和提交历史记录以获取完整的更改列表。

## 它是如何运作的

1. **转录** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) 转录音频（GPU 加速）
2. **语音/音乐分离** - [Demucs](https://github.com/facebookresearch/demucs) 将人声与背景音乐隔离
3. **翻译** - MarianMT（本地、离线）、Google Translate、DeepL Free 或 **Ollama LLM**（Qwen3，槽感知简明翻译）
4. **识别说话人（分类）** *（可选）* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) 识别每个片段中谁在说话
5. **语音配音** - [Edge-TTS](https://github.com/rany2/edge-tts)（400 多个语音）或 [Coqui XTTS v2](https://github.com/coqui-ai/TTS)（语音克隆，针对对话中的每个发言者）
6. **混音** - 配音与原始背景音乐混合
7. **标准化** - 最终音频标准化为 -23 LUFS（EBU R128 广播标准）
8. **唇形同步** *（可选）* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) 将嘴部动作与配音音频同步

## 特点

- 🖥️ 主题 GUI (Tkinter) - 无需命令行； Graphite、Slate、Light 和 Neon 主题、强调色、文本大小和设置面板可通过拖动重新排序
- 🌍 **26 种目标语言**，每种语言有多种语音
- 🌐 **26 种语言的 UI** - 界面本身会适应您的语言
- 🎬 **YouTube 和 URL 支持** - 粘贴任何 YouTube 链接并直接翻译（由 yt-dlp 提供支持）
- ▶️ **集成视频播放器** (libmpv/mpv) - 颜色编码的传输控件、播放列表、A/B 原始音频与配音音频、字幕切换、快照、全屏、打开文件夹
- ⏱️ **实时翻译** - 观看本地文件或已解析的点播视频链接，带有翻译字幕和 YouTube 风格的延迟滑块；引擎 MarianMT / Google / DeepL / Ollama。实验性配音使用 Edge-TTS 和第二个 mpv 实例。语音重叠处理和真实音频/Windows 接受仍在进行中；尚不支持增长直播。请参阅[实时实施状态](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26)。
- 🎵 通过 Demucs 进行语音/音乐分离（保留背景音乐）
- 🔇 **将原始音频静音**，可在实时翻译之前和期间使用，使视频的配乐静音，同时保持翻译后的声音清晰可见。将其关闭即可恢复原始音频；当实时会话结束时它会重置。
- 🧠 **MarianMT** - 完全本地、离线神经翻译（赫尔辛基-NLP，无请求率限制，无 API 密钥）
- 🤖 **Ollama LLM 翻译** *（v2.0 中的新增功能）* - 本地 LLM（Qwen3、Llama、Mistral）为自然配音生成插槽感知的简明翻译，首次使用时自动检测/安装/启动/拉取模型
- 🎙️ **语音克隆** - Coqui XTTS v2 以目标语言（~1.8 GB 模型）克隆以原始音频说话的人，具有每段自适应速度和幻觉多种子重试功能
- 👥 **识别说话的人（分类）** - pyannote-audio 3.1 识别多人说话； XTTS 单独克隆每个声音
- 💋 **唇形同步** - Wav2Lip GAN 将嘴部运动与配音音频同步（~416 MB 模型）
- 🔊 **音频标准化** - 自动 -23 LUFS 响度标准化 (EBU R128)
- ✏️ 字幕编辑器 - 在配音前检查并更正字幕
- 📦 批处理 - 一次翻译多个视频或 URL
- ⚡ 通过 CUDA 进行 GPU 加速（自动回退到 CPU）
- 📄 可选 `.srt` 字幕导出
- 🔁 **DeepL Free** 翻译引擎（可选 - 500k 字符/月，需要免费 API 密钥）
- 🔧 **自动安装** - 首次启动时会自动安装缺少的 Python 包和 ffmpeg

## 支持的语言

阿拉伯语、中文、捷克语、丹麦语、荷兰语、英语、芬兰语、法语、德语、希腊语、印地语、匈牙利语、印度尼西亚语、意大利语、日语、韩语、挪威语、波兰语、葡萄牙语、罗马尼亚语、俄语、西班牙语、瑞典语、土耳其语、乌克兰语、越南语

## 语音目录

Edge-TTS 语音目录在 `video_translator_gui.py` 顶部附近的 `LANGUAGES` 中定义。该词典是目标语言名称、GUI 语音单选按钮以及省略 `--voice` 时的 CLI 后备语音的真实来源。

Claude/项目维护注释在 **Voice Catalog Source Of Truth** 下的 `CLAUDE.md` 中反映了此位置，因此未来的代码代理知道在哪里更新语音以及自述文件将用户指向哪里。

## 翻译引擎

| 发动机 | 设置 | 限制 | 品质 |
|--------|-------|--------|---------|
| **Google Translate** *（默认）* | 无 | 非官方抓取 - 可能会在大型视频上受到限制 | ★★★★ |
| **MarianMT** | 无 - 首次使用时每个语言对下载约 298 MB | 无 - 下载后完全离线 | ★★★★ |
| **DeepL Free** | 免费 API 密钥位于 [deepl.com](https://www.deepl.com/pro-api) | 50 万字符/月 | ★★★★★ |
| **Ollama LLM** *（推荐用于配音 - v2.0 中的新增功能）* | 首次使用时自动安装（~1 GB Ollama + 5 GB 型号） | 无 - 完全本地化 | ★★★★★ |

> **MarianMT** 使用 [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) 模型，首次下载后在本地缓存。需要明确的源语言（不支持自动检测 - 手动选择源语言）。如果缺少，则首次选择时会自动安装所需的 Python 包（`sacremoses`、`sentencepiece`）。

> **Ollama LLM** *（v2.0 中的新增功能）* 是推荐的配音引擎，因为它可以生成了解目标时间段的翻译。当 MarianMT 进行字面翻译并生成意大利语/西班牙语/法语时，其生成的意大利语/西班牙语/法语比英语长约 25%（强制在 TTS 上进行可听音频压缩），因此法学硕士会被提示保持每个片段的简洁和自然，以便进行口头交付，从而实现与源的典型字符比为 0.85-0.95。默认型号为 `qwen3:8b`（磁盘 5.2 GB，~6 GB VRAM）； `qwen3:4b` (~3 GB) 是轻量级选项，`qwen3:14b` 是更高质量的选项。该管道自动检测 Ollama 二进制文件，在首次使用时通过官方安装程序自动安装它（在同意弹出窗口的情况下），启动守护进程并拉取所选模型 - 无需手动设置。如果缺少任何内容，自动切换到 Google Translate。

## 语音克隆 (XTTS v2)

启用后，该应用程序会从原始视频中提取说话者的语音，并将其用作克隆目标语言语音的参考。

- 支持的语言： AR、ZH、CS、DE、EN、ES、FR、HI、HU、IT、JA、KO、NL、PL、PT、RU、TR (17/26)
- 对于其余 9 种语言，Edge-TTS 会自动用作后备
- 模型 (~1.8 GB) 首次使用时自动下载到 `~/.local/share/tts/`
- **VAD 过滤参考** (v1.4)：通过 [silero-vad](https://github.com/snakers4/silero-vad) 从原始音频中选择 10-15 秒的连续语音，以获得更好的语音克隆质量
- **生成速度**可配置（`xtts_speed`，默认 `1.25`）：当翻译的文本长于源插槽时，较高的值可减少后处理音频压缩伪影。通过 `~/.config/videotranslatorai/config.json` 或 CLI `--xtts-speed` 进行调谐
- 在 CUDA 或 CPU 上运行

## 识别讲话者（二值化）（pyannote-audio）

启用后，该应用程序会识别每个部分中的发言者。与语音克隆相结合，每个发言者的声音都被单独克隆 - 非常适合采访、播客和多人视频。

- 需要免费的[HuggingFace令牌](https://huggingface.co/settings/tokens)（一次性注册）
- **通过操作系统密钥环安全存储令牌** (v1.4)：Windows Credential Manager、macOS Keychain、Linux Secret Service。从以前的纯文本 JSON 存储自动迁移
- 首次下载后，完全离线工作
- 型号：`pyannote/speaker-diarization-3.1`

## 口型同步 (Wav2Lip)

启用后，该应用程序会应用 Wav2Lip GAN 将受试者的嘴部运动与配音音频同步 - 该人似乎在说翻译后的语言。

- 模型 (~416 MB) 和存储库在首次使用时自动克隆到 `~/.local/share/wav2lip/`
- 在 CUDA（推荐）或 CPU 上运行
- 显着增加处理时间
- 最适用于具有清晰可见的单一脸部的视频

## 要求

- Python 3.10+（Windows 安装程序自动提供 3.11.9）
- Windows 10 / 11 (x64)、Linux 或 macOS
- **强烈推荐 NVIDIA GPU** - 请参阅下面的 GPU 表
- 完整安装需要 20 GB 可用磁盘空间（PyTorch CUDA、Whisper large-v3、XTTS、Wav2Lip）

> **如果缺少，ffmpeg 和所有 Python 软件包都会在首次启动时自动安装**。无需手动设置。

**可选系统依赖项** - `rubberband-cli`（Linux：`sudo apt install rubberband-cli`，macOS：`brew install rubberband`）。安装后，它用于在配置文件控制的质量带（默认 1.15-1.50，硬内容最高 1.65）中进行音高保留时间拉伸，消除克隆 XTTS 声音上残留的“花栗鼠”效果。如果没有它，管道将保持不变（自动回退到 ffmpeg `atempo`）。质量配置文件现在更喜欢额外的短翻译重试，而不是极端的音频加速。

### GPU支持

该管道使用五个 GPU 加速组件（faster-whisper、Demucs、XTTS、Wav2Lip、pyannote）。不同供应商的 GPU 覆盖率并不统一：

| GPU | Windows | Linux | 注释 |
|-----|---------|-------|-------|
| **NVIDIA**（RTX 20xx 或更高版本，CUDA 12.4 驱动程序） | ✅ 全加速 | ✅ 全加速 | **推荐。** 所有 5 个组件都在 GPU 上运行。 |
| **AMD**（Radeon） | ⚠️不完整（DirectML不支持XTTS和faster-whisper） | ⚠️部分（ROCm适用于Demucs/XTTS/pyannote，但faster-whisper仅支持CUDA） | 可以工作，但 Whisper 转录仍保留在 CPU 上并占据总时间。 |
| **Intel Arc** | ⚠️ 不成熟的 PyTorch XPU 支持 | ⚠️一样 | 未测试。 |
| **无（仅限 CPU）** | ✅ 有效 | ✅ 有效 | 预计比实时速度慢 **10-20 倍**。仅用 Whisper large-v3 转录一个 5 分钟的剪辑可能就需要 50 多分钟。 |

**推荐的 NVIDIA 显存：**

| VRAM | 常见显卡 | 经验 |
|------|---------------|-----------|
| 6GB | GTX 1660、RTX 2060 | 可以使用，不能同时运行 XTTS + Wav2Lip |
| 8GB | RTX 3060 钛、4060 | 管道齐全，无余量 |
| **12GB+** | **RTX 3060 12GB、4070、4080** | **推荐-舒适** |
| 24GB | RTX 3090、4090 | 大批量备用产能 |

## 安装

### Windows

1. 克隆或下载此存储库
2. 右键单击 `setup_windows.bat` → **以管理员身份运行** → 菜单显示 `[1] Install`
3. 安装程序自动：
   - 如果不存在则安装 Python 3.11（系统范围）
   - 如果不存在则安装 Git for Windows
   - 安装所有 Python 依赖项（PyTorch CUDA 12.4、faster-whisper、Demucs、coqui-tts、Wav2Lip deps 等）
   - 下载并安装 ffmpeg
   - 安装集成视频播放器（python-mpv 以及 `mpv-runtime` 中的 libmpv 构建）。该步骤是可选的：如果失败，其他一切都会正常，并且播放器窗格会解释缺少的内容
   - 创建**公共桌面快捷方式**（PC 上的每个 Windows 帐户都可见）

> 安装程序是**多用户**：所有内容都在 `%ProgramFiles%\VideoTranslatorAI` 下在系统范围内安装，并且计算机上的任何 Windows 用户都会发现快捷方式已准备就绪。 **不再需要 VS C++ 构建工具** - 维护的 `coqui-tts` 分支提供预编译的 Python 轮包。

### Linux / macOS

```bash
# 克隆存储库
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# 可选：预先安装经过测试的 NVIDIA CUDA 12.4 PyTorch 堆栈
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# 可选：预安装所有Python运行时包而不是让GUI
# 首次运行时安装缺少的软件包
pip install --break-system-packages -r requirements.txt

# 可选：集成视频播放器（发行版中的 libmpv，PyPI 中的 python-mpv）
sudo apt install libmpv2        # Fedora：mpv-libs，Arch：mpv，openSUSE：libmpv2
pip install --break-system-packages -r requirements-player.txt

# 可选：将项目安装为可编辑的 Python 包
pip install --break-system-packages --no-deps -e .

# 从源代码启动
python video_translator_gui.py

# 或者，在可编辑/包安装后
videotranslatorai
videotranslatorai --preflight
```

> 首次启动时，GUI 会检测到任何缺失的软件包（faster-whisper、Demucs、Edge-TTS 等）并自动安装它们，将输出流式传输到日志窗口。 ffmpeg 也会通过 `apt-get` / `dnf` / `pacman` (Linux) 自动安装或从 GitHub (Windows) 下载。

> 标题显示 **玩家** 徽章。当 libmpv 或 python-mpv 丢失时，左窗格会显示缺少的内容并提供 **安装播放器**：在 Linux 上，它通过 pkexec （然后是 `sudo -n`）使用包管理器，并在两者都不起作用时显示手动命令；在 Windows 上，它会在为当前用户下载 libmpv 之前询问（大约 32 MB）。

### 需求概况

| 文件 | 目的 |
|------|---------|
| `requirements.txt` | 完整的、向后兼容的运行时安装。 |
| `requirements-core.txt` | GUI/CLI 使用的默认管道包。 |
| `requirements-optional.txt` | XTTS、MarianMT 标记器、二值化、VAD、密钥环。 |
| `requirements-wav2lip.txt` | Wav2Lip 运行时和人脸检测堆栈（`new-basicsr`、`facexlib`、`dlib`）。 |
| `requirements-gpu-cu124.txt` | PyTorch 堆栈使用 NVIDIA CUDA 12.4 轮进行测试。 |
| `requirements-player.txt` | 集成视频播放器：python-mpv（需要系统或 Windows 安装程序中的 libmpv）。 |
| `requirements-dev.txt` | CI/单元测试使用的轻量级依赖项。 |

## 卸载

### Windows

运行 `setup_windows.bat`（右键单击 → **以管理员身份运行**）并从菜单中选择 `[3] Uninstall`。提供三种卸载子模式：

| 模式 | 需要管理员 | 适用范围 |
|------|----------------|-------|
| **[1] 完全卸载 - 一键** | ✅ | 从计算机路径中删除应用程序文件夹、公共桌面快捷方式、ffmpeg、每个用户的 HF 模型缓存 (Whisper/XTTS) 和配置 (`HF token`) 以及安装程序安装的所有 Python AI 包。最后，它还询问（选择加入）是否通过注册表静默卸载字符串静默卸载 **Python 3.11** 和 **Git for Windows**。 |
| **[2] 仅限当前用户** | ❌ | 仅删除正在运行的用户的 VTAI 配置、HF/XTTS 缓存和旧版每用户安装。 **保持系统范围内的安装完好无损**，以便 PC 上的其他 Windows 帐户可以继续使用该应用程序。 |
| **[3] 自定义 - 粒度** | ✅ 对于系统项目，❌ 对于用户项目 | 每个类别的是/否提示：应用程序文件夹、快捷方式、计算机路径、每用户旧版安装、每用户配置/缓存，然后分组 Python 包（TTS、PyTorch 堆栈、Whisper+ctranslate2、Demucs、Wav2Lip deps、pyannote、管道实用程序），最后是可选的 Python 3.11 和 Git。 |

**永远不会自动删除：** Visual Studio C++ 构建工具（如果在较旧的运行中存在）。如果需要，请使用 Windows 设置中的“应用程序和功能”手动删除它们。

### Linux / macOS

没有专用的卸载程序 - 手动删除：

```bash
# 由 GUI 的自动安装程序安装的 Python 包
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# 用户数据和模型缓存
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # 配置（主题、面板顺序、设置）
rm -f  ~/.videotranslatorai_config.json     # 版本 <= 1.9 的旧配置（如果存在）
```

## 用途

### 诊断

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

运行本地环境诊断，无需开始翻译或安装任何内容。 `--preflight-lipsync` 根据需要处理 Wav2Lip 脸部包，这在启用 **Lip Sync** 之前很有用。 GUI 通过日志面板的 **Diagnostics** 按钮公开相同的基本检查。 `--preflight-player` 根据需要处理集成视频播放器（python-mpv 和可加载的 libmpv）。 `python -m videotranslator.libmpv_runtime check` 单独探测 libmpv（出口 0 就绪，2 不可用）。

### GUI

```bash
python video_translator_gui.py
```

**布局：**批量翻译设置位于右侧的栏中，作为设置面板的堆栈：**输入**、**翻译**、**工作流程配置文件**、**开始**以及可折叠的高级部分（模型、翻译引擎、音频、语音克隆、口型同步、二值化、选项、热词）。左侧的大区域是**集成视频播放器**（传输、播放列表、A/B 原声与配音、字幕、快照、全屏），其下方是**实时翻译**栏。通过卡片标题或 **等** 手柄拖动卡片，可将其在列中上下移动；订单被保存（`ui_panel_order`）并在下次启动时恢复。底部的日志面板可以通过**隐藏日志**隐藏。启动时，窗口以当前监视器（指针下方的监视器）为中心打开并最大化，因此它在多监视器设置上表现良好。

**视频视频播放器控件：** 图标在每个主题中使用一致的功能颜色，与所选的强调色无关：

| 控制 | 颜色 |
|---------|--------|
| 播放视频 | 绿色 |
| 暂停（播放时替换播放） | 琥珀色 |
| 停止播放 | 珊瑚红 |
| 上一张/后 10 秒/前进 10 秒/下一张 | 蓝色 |
| 快照 | 紫罗兰色 |
| 打开文件夹 | 黄金 |

悬停会添加微妙的有色背景。不可用的控件是中立的；停止后播放列表导航仍然可用。工具提示和键盘焦点指示器仍然可用，因此颜色并不是识别操作的唯一方法。

**来自本地文件：**
1. 单击“**添加**”以选择一个或多个视频文件
2. 选择源语言和目标语言
3. 打开 **Model** 部分并选择 Whisper 模型（`small` 是速度/精度的良好平衡）
4. 选择声音并根据需要调整 TTS 速度
5. *（可选）* 在 **翻译引擎** 中选择 **Google**（默认）、**MarianMT**（本地/离线）、**DeepL Free** 或 **Ollama LLM**（本地，建议用于配音）
6. *（可选）* 启用 **语音克隆** (XTTS v2) 和/或 **说话人识别（二值化）**
7. *（可选）* 启用 **唇形同步** (Wav2Lip)
8. 单击**开始翻译**

**来自 YouTube（或任何受支持的网站）：**
1. 在 **URL** 字段中粘贴一个或多个 URL（每行一个）
2. 照常配置语言、模型和语音
3. 点击 **⬇ 下载并翻译**

> yt-dlp 支持 YouTube、Vimeo、Twitter/X、TikTok 和 [1000 多个其他网站](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)。

> ⚠️ **合理使用声明：** 通过 yt-dlp 下载视频被 YouTube 等平台视为自动访问，可能违反其服务条款。大量或重复使用同一 IP 地址可能会导致临时阻止（HTTP 429/需要登录错误）。如果遇到下载失败，请使用 VPN 或轮换 IP。该工具仅供个人非商业用途。重新分发翻译内容可能会侵犯版权 - 请始终尊重原始作者的权利。

### 实时翻译（字幕和实验配音）

观看本地文件或已解析的点播视频链接，其中包含翻译的字幕和可选的口语翻译。使用播放器下方的栏：

**来自链接：**

1. 将链接粘贴到 **URL** 字段中
2. 设置源语言和目标语言，选择语音并调整**延迟**滑块
3. 选择**配音**和/或**字幕**
4. 要仅听到翻译后的语音，请在开始之前选择**将原始音频静音**（意大利语：**Silenzia originale**，位于字幕复选框旁边）
5. 单击**实时翻译** - 链接已解析并开始翻译

**从加载的文件：** 在播放器中加载视频（输入 -> 添加，然后选择它），将 URL 字段留空，选择相同的实时设置，然后单击 **实时翻译**。当字段不为空时，URL 优先。

- **引擎：** MarianMT（离线，默认）、Google、DeepL 或 Ollama。语音识别 (Whisper) 在本地运行。离线模型需要初始下载。
- **语音配音：** 通过第二个 mpv 实例进行实验性 Edge-TTS 语音播放。它需要互联网访问，并且与批量语音克隆分开。
- **将原始音频静音：**在开始之前和翻译过程中均可用。它使整个原始配乐（包括音乐和效果）静音，但使翻译后的声音清晰可见。它不会隔离原始音频中说话的人。将其关闭以恢复配乐；当实时会话结束时它会重置。播放器的扬声器按钮是一般的静音，不是这个独立控制。
- **暂停和搜索：**视频播放器控件连接到实时会话；端到端音频同步仍然需要特定于平台的验收测试。
- **当前限制：** 剪辑重叠/淡入淡出处理、音频定时校准和 Windows 接受仍然开放。尚不支持增长直播；实时模式标签并不意味着支持随着广播的增长而摄取广播。参见[实施情况及剩余工作](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26)。

对于保存的配音视频，请使用 **下载和翻译** / **开始翻译** 而不是实时预览。

### 翻译引擎块和 VPN

可能会发生两个不同的块，并进行不同的修复：

| 块 | 症状 | 修复 |
|-------|---------|-----|
| **下载** (yt-dlp) | “登录以确认您不是机器人”，HTTP 429 | **VPN** / 轮换 IP，或在浏览器中登录 YouTube（自动读取 cookie） |
| **翻译**（Google 免费端点） | “Google Translate 无法翻译...请求速率受限/被阻止” | 使用 **MarianMT**（离线）或 **Ollama**（本地）- 无请求速率限制。 VPN 也有帮助。现在，当 Google 被阻止时，批处理流程**自动回退到 MarianMT**。 |

### 主题和外观

单击标题中的齿轮图标打开**设置**：

- **主题**：自动（遵循操作系统暗/亮模式）、Graphite（默认）、Slate、Light、Neon。
- **强调色**：每个主题默认，或蓝色、青色、紫色、绿色、琥珀色、玫瑰色。
- **文字大小**：小、正常、大、超大。
- **界面语言**：26 种语言。

更改会立即应用，无需重新启动，并保存在配置文件中（`ui_theme`、`ui_accent`、`ui_scale`、`ui_lang`）。 **恢复默认设置**恢复 Graphite 主题、默认重音、正常文本大小和设置面板的默认顺序。

### 命令行

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**所有选项：**

| CLI 选项 | 描述 | 默认 |
|------|-------------|---------|
| `--lang-source` | 源语言（`auto` 用于自动检测） | `auto` |
| `--lang-target` | 目标语言代码（例如 `it`、`fr`、`de`） | `it` |
| `--voice` | Edge-TTS 语音名称 | auto |
| `--model` | Whisper 型号 (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS速度调整（例如`+10%`、`-20%`） | `+0%` |
| `--translation-engine` | `google`、`marian` 或 `deepl` | `google` |
| `--deepl-key` | DeepL Free API 密钥 | - |
| `--diarize` | 启用说话人识别（分类）(pyannote) | - |
| `--hf-token` | 用于二值化的 HuggingFace 令牌 | - |
| `--lipsync` | 配音后应用 Wav2Lip 唇形同步 | - |
| `--subs-only` | 仅生成`.srt`，跳过配音 | - |
| `--no-subs` | 跳过`.srt`生成 | - |
| `--no-demucs` | 跳过语音/音乐分离 | - |
| `--output` / `-o` | 输出文件路径 | auto |
| `--output-dir` | 已翻译文件的文件夹（一处，Windows 和 Linux） | `<videos>/VideoTranslatorAI` |
| `--batch` | 处理多个文件 | - |

### 与真实模型的集成测试

默认测试套件避免了真实模型下载和长时间的 GPU 工作。要对已安装的本地堆栈运行选择加入经验检查：

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

这些检查验证真实的 Wav2Lip 导入、Torch CUDA 可用性、Ollama 守护程序可用性以及合成语音上的 faster-Whisper。当本地驱动程序/守护程序/模型状态未准备好时，它们会故意失败或跳过。

**示例：**

```bash
# 使用本地 MarianMT 将意大利语视频翻译成英语
# （首次使用时下载约 298 MB 模型，然后完全离线）
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# 通过语音克隆+说话人识别进行翻译（分类）
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# 口型同步翻译
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# 仅字幕（无配音）
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper型号

| 型号 | 尺寸 | 速度 | 准确度 |
|-------|------|-------|----------|
| tiny | 75MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465MB | ⚡⚡ | ★★★☆ |
| medium | 1.5GB | ⚡ | ★★★★ |
| large-v2/v3 | 3GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1.6GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` 是 `large-v3` 的精炼版本（4 个解码器层与 32 个解码器层） - 接近大质量，速度大致为 `medium` 层。当转录速度很重要时，建议在现代 GPU 上使用默认设置；多语言材料的质量下降很小。

> 首次使用时会自动下载模型。

## 独立模块 CLI

模块化包公开了四个面向用户的工具，可以直接调用这些工具，而无需启动完整的管道：

```bash
# 飞行前播放一段视频以了解人脸是否存在（如果不存在，Wav2Lip 将跳过）。
python3 -m videotranslator.face_detector path/to/video.mp4
# 出口 0 = 有脸，出口 1 = 无脸

# 分析 build_dubbed_track 生成的 *_metrics.csv。
# 报告 pre_stretch_ratio 的 P50/P75/P90/P95，可听频带细分，
# 拉伸引擎的使用情况，以及前 N 个最差的异常值及其目标文本。
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# 清理 TTS 文本（重写冒号、分号、省略号、破折号）。
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# 在运行 TTS 之前从 .srt 或 .json 片段文件估计配音难度。
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

每个工具都有 `-h`/`--help` 的完整选项。它们是独立的，并重用语音配音管道所依赖的相同模块，因此它们的输出与运行时保持一致。

## 许可证

MIT

### 第三方组件

存储库代码是 MIT。安装程序在安装时从自己的来源下载以下组件；该项目不会重新分配它们。

- **libmpv** (https://github.com/mpv-player/mpv)，集成视频播放器的引擎。 Windows：首先尝试中飞（https://github.com/zhongfly/mpv-winbuild）构建的LGPL； shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) 构建的固定 GPL 是后备方案。 `mpv-runtime\BUILD.txt` 记录源、许可证风格和 mpv 提交，许可证文本位于 DLL 旁边。 Linux：发行包（`libmpv2`、`libmpv1`、`mpv-libs` 或 `mpv`）。
- **FFmpeg** 位于 libmpv 内（LGPL 或 GPL，遵循 libmpv 构建）。
- **python-mpv**（PyPI 上的 `mpv`）、GPLv2+ 或 LGPLv2.1+。
- **7-Zip `7zr.exe`** 26.03 (LGPL)，Windows 安装程序用于提取 libmpv，然后删除。
- **Vulkan 加载程序**（Khronos、MIT 和 Apache-2.0），仅当 `vulkan-1.dll` 缺失时才在 Windows 上下载。
- **edge-tts** (LGPLv3)，由语音配音管道使用。
- **MarianMT 模型**（赫尔辛基-NLP），首次使用时根据自己的许可证从 Hugging Face Hub 下载（Apache-2.0 用于 `opus-mt` 模型，CC-BY-4.0 用于 `opus-mt-tc-big`）。
