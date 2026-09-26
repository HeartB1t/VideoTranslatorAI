# 🎬 Video Translator AI

[Tiếng Anh](../../README.md) | [Tất cả bản dịch](README.md)

**Đọc trang này trong:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Công cụ lồng tiếng video được hỗ trợ bởi AI tự động phiên âm, dịch và lồng tiếng lại video sang 26 ngôn ngữ, với các tùy chọn xử lý cục bộ và không yêu cầu khóa API theo mặc định. Nhận dạng giọng nói Whisper chạy cục bộ; Edge-TTS, Google Translate và DeepL yêu cầu kết nối internet. Các tính năng tùy chọn (DeepL, nhận dạng người đang nói (ghi nhật ký)) có thể yêu cầu khóa API hoặc mã thông báo truy cập.

> **v2.0** - gói mô-đun, bản dịch Ollama cục bộ, điều phối hồ sơ chất lượng, siêu dữ liệu Python có thể cài đặt và thử nghiệm tích hợp chọn tham gia với các mô hình thực. Xem [Bản phát hành GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases) và lịch sử cam kết để biết danh sách đầy đủ các thay đổi.

## Nó hoạt động như thế nào

1. **Phiên âm** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) phiên âm âm thanh (được tăng tốc GPU)
2. **Tách giọng/nhạc** - [Demucs](https://github.com/facebookresearch/demucs) tách giọng hát khỏi nhạc nền
3. **Dịch** - MarianMT (cục bộ, ngoại tuyến), Google Translate, DeepL Free hoặc **Ollama LLM** (Qwen3, bản dịch ngắn gọn nhận biết vị trí)
4. **nhận dạng người đang nói (ghi nhật ký)** *(tùy chọn)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) xác định ai đang nói trong mỗi phân đoạn
5. **lồng tiếng** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ giọng nói) hoặc [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (nhân bản giọng nói, cho mỗi người nói trong cuộc trò chuyện)
6. **Trộn** - giọng lồng tiếng được trộn lại với nhạc nền gốc
7. **Chuẩn hóa** - âm thanh cuối cùng được chuẩn hóa thành -23 LUFS (chuẩn phát sóng EBU R128)
8. **Đồng bộ khẩu hình** *(tùy chọn)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) đồng bộ hóa chuyển động của miệng với âm thanh lồng tiếng

## Tính năng

- 🖥️ GUI theo chủ đề (Tkinter) - không cần dòng lệnh; Các chủ đề Graphite, Slate, Light và Neon, màu nhấn, kích thước văn bản và bảng cài đặt mà bạn có thể sắp xếp lại bằng cách kéo
- 🌍 **26 ngôn ngữ đích** với nhiều giọng nói cho mỗi ngôn ngữ
- 🌐 **Giao diện người dùng bằng 26 ngôn ngữ** - giao diện tự điều chỉnh theo ngôn ngữ của bạn
- 🎬 **Hỗ trợ YouTube và URL** - dán bất kỳ liên kết YouTube nào và dịch trực tiếp (được cung cấp bởi yt-dlp)
- ►️ **Trình phát video tích hợp** (libmpv/mpv) - điều khiển truyền tải được mã hóa màu, danh sách phát, âm thanh gốc A/B và âm thanh lồng tiếng, chuyển đổi phụ đề, ảnh chụp nhanh, toàn màn hình, mở thư mục
- ⏱️ **Dịch thời gian thực** - xem tệp cục bộ hoặc liên kết video theo yêu cầu đã được giải quyết với phụ đề đã dịch và thanh trượt độ trễ kiểu YouTube; động cơ MarianMT / Google / DeepL / Ollama. Lồng tiếng thử nghiệm sử dụng Edge-TTS và phiên bản mpv thứ hai. Việc xử lý chồng chéo giọng nói và chấp nhận âm thanh thực/Windows vẫn đang được tiến hành; chương trình phát sóng trực tiếp đang phát triển chưa được hỗ trợ. Xem [trạng thái triển khai trực tiếp](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Tách giọng/nhạc qua Demucs (giữ nhạc nền)
- 🔇 **Tắt tiếng âm thanh gốc**, khả dụng trước và trong khi dịch trực tiếp, tắt tiếng nhạc nền của video trong khi vẫn nghe được giọng đã dịch. Tắt nó đi để khôi phục âm thanh gốc; nó đặt lại khi phiên trực tiếp kết thúc.
- 🧠 **MarianMT** - bản dịch thần kinh ngoại tuyến, cục bộ hoàn toàn (Helsinki-NLP, không giới hạn tốc độ yêu cầu, không có khóa API)
- 🤖 **Bản dịch Ollama LLM** *(mới trong v2.0)* - LLM cục bộ (Qwen3, Llama, Mistral) tạo ra các bản dịch ngắn gọn theo vị trí để lồng tiếng tự nhiên, tự động phát hiện/cài đặt/bắt đầu/kéo mô hình trong lần sử dụng đầu tiên
- 🎙️ **Nhân bản giọng nói** - Coqui XTTS v2 nhân bản người nói bằng giọng của âm thanh gốc bằng ngôn ngữ đích (kiểu máy ~ 1,8 GB), với tốc độ thích ứng trên mỗi phân đoạn và thử lại nhiều hạt giống đối với ảo giác
- 👥 **nhận dạng người đang nói (ghi nhật ký)** - pyannote-audio 3.1 xác định nhiều người đang nói; XTTS nhân bản từng giọng nói riêng biệt
- 💋 **Lip Sync** - Wav2Lip GAN đồng bộ hóa chuyển động của miệng với âm thanh lồng tiếng (kiểu máy ~416 MB)
- 🔊 **Chuẩn hóa âm thanh** - tự động chuẩn hóa âm lượng -23 LUFS (EBU R128)
- ✏️ Trình chỉnh sửa phụ đề - xem xét và sửa phụ đề trước khi lồng tiếng
- 📦 Xử lý hàng loạt - dịch nhiều video hoặc URL cùng một lúc
- ⚡ Tăng tốc GPU thông qua CUDA (tự động quay trở lại CPU)
- 📄 Xuất phụ đề `.srt` tùy chọn
- 🔁 **DeepL Free** công cụ dịch thuật (tùy chọn - 500k ký tự/tháng, yêu cầu khóa API miễn phí)
- 🔧 **Tự động cài đặt** - các gói Python và ffmpeg bị thiếu sẽ được cài đặt tự động trong lần khởi chạy đầu tiên

## Ngôn ngữ được hỗ trợ

Tiếng Ả Rập, Tiếng Trung, Tiếng Séc, Tiếng Đan Mạch, Tiếng Hà Lan, Tiếng Anh, Tiếng Phần Lan, Tiếng Pháp, Tiếng Đức, Tiếng Hy Lạp, Tiếng Hindi, Tiếng Hungary, Tiếng Indonesia, Tiếng Ý, Tiếng Nhật, Tiếng Hàn, Tiếng Na Uy, Tiếng Ba Lan, Tiếng Bồ Đào Nha, Tiếng Romania, Tiếng Nga, Tiếng Tây Ban Nha, Tiếng Thụy Điển, Tiếng Thổ Nhĩ Kỳ, Tiếng Ukraina, Tiếng Việt

## Danh mục giọng nói

Danh mục giọng nói Edge-TTS được xác định trong `LANGUAGES` gần đầu `video_translator_gui.py`. Từ điển đó là nguồn thông tin chính xác cho tên ngôn ngữ đích, nút radio giọng nói GUI và giọng nói dự phòng CLI khi `--voice` bị bỏ qua.

Ghi chú Claude/bảo trì dự án phản ánh vị trí này trong `CLAUDE.md` trong **Voice Catalog Source Of Truth**, để các tác nhân mã trong tương lai biết nơi cập nhật giọng nói và nơi README trỏ đến người dùng.

## Công cụ dịch thuật

| Động cơ | thiết lập | Giới hạn | chất lượng |
|--------|-------|--------|---------|
| **Google Translate** *(mặc định)* | không có | Quét không chính thức - có thể được điều chỉnh trên các video lớn | ★★★★ |
| **MarianMT** | Không có - tải xuống ~298 MB mỗi cặp ngôn ngữ trong lần sử dụng đầu tiên | Không có - hoàn toàn ngoại tuyến sau khi tải xuống | ★★★★ |
| **DeepL Free** | Khóa API miễn phí tại [deepl.com](https://www.deepl.com/pro-api) | 500k ký tự/tháng | ★★★★★ |
| **Ollama LLM** *(được khuyến nghị để lồng tiếng - tính năng mới trong v2.0)* | Tự động cài đặt trong lần sử dụng đầu tiên (~1 GB kiểu Ollama + 5 GB) | Không có - hoàn toàn cục bộ | ★★★★★ |

> **MarianMT** sử dụng các mô hình [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP), được lưu vào bộ nhớ đệm cục bộ sau lần tải xuống đầu tiên. Yêu cầu ngôn ngữ nguồn rõ ràng (tự động phát hiện không được hỗ trợ - chọn ngôn ngữ nguồn theo cách thủ công). Các gói Python bắt buộc (`sacremoses`, `sentencepiece`) được cài đặt tự động trong lựa chọn đầu tiên nếu bị thiếu.

> **Ollama LLM** *(mới ở phiên bản 2.0)* là công cụ được khuyên dùng để lồng tiếng vì nó tạo ra các bản dịch có tính đến khoảng thời gian mục tiêu. Trong đó MarianMT dịch theo nghĩa đen và tạo ra tiếng Ý / tiếng Tây Ban Nha / tiếng Pháp dài hơn tiếng Anh ~ 25% (buộc phải nén âm thanh có thể nghe được trên TTS), LLM được nhắc giữ từng phân đoạn ngắn gọn và tự nhiên để truyền đạt bằng giọng nói, đạt được tỷ lệ ký tự điển hình là 0,85-0,95 so với nguồn. Model mặc định là `qwen3:8b` (5,2 GB trên đĩa, ~6 GB VRAM); `qwen3:4b` (~3 GB) là tùy chọn nhẹ, `qwen3:14b` là tùy chọn chất lượng cao hơn. Đường dẫn tự động phát hiện tệp nhị phân Ollama, tự động cài đặt nó thông qua trình cài đặt chính thức trong lần sử dụng đầu tiên (với cửa sổ bật lên có sự đồng ý), khởi động trình nền và lấy mô hình đã chọn - không cần thiết lập thủ công. Tự động chuyển sang Google Translate nếu thiếu bất cứ thứ gì.

## Nhân bản giọng nói (XTTS v2)

Khi được bật, ứng dụng sẽ trích xuất giọng nói của người nói từ video gốc và sử dụng nó làm tham chiếu để sao chép giọng nói bằng ngôn ngữ đích.

- Ngôn ngữ được hỗ trợ: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Đối với 9 ngôn ngữ còn lại, Edge-TTS được sử dụng tự động làm dự phòng
- Model (~1,8 GB) được tự động tải xuống trong lần sử dụng đầu tiên vào `~/.local/share/tts/`
- **Tham chiếu được lọc VAD** (v1.4): 10-15 giây giọng nói liên tục được chọn từ âm thanh gốc qua [silero-vad](https://github.com/snakers4/silero-vad) để có chất lượng sao chép giọng nói tốt hơn
- **Tốc độ tạo** có thể định cấu hình (`xtts_speed`, `1.25` mặc định): giá trị cao hơn giúp giảm hiện tượng nén âm thanh sau xử lý khi văn bản dịch dài hơn khe nguồn. Điều chỉnh qua `~/.config/videotranslatorai/config.json` hoặc CLI `--xtts-speed`
- Chạy trên CUDA hoặc CPU

## nhận dạng người đang nói (ghi nhật ký) (pyannote-audio)

Khi được bật, ứng dụng sẽ xác định ai đang nói trong từng phân đoạn. Kết hợp với Nhân bản giọng nói, giọng nói của mỗi người nói được sao chép riêng biệt - lý tưởng cho các cuộc phỏng vấn, podcast và video nhiều người.

- Yêu cầu [HuggingFace token](https://huggingface.co/settings/tokens) miễn phí (đăng ký một lần)
- **Mã thông báo được lưu trữ an toàn** (v1.4) thông qua khóa hệ điều hành: Windows Credential Manager, macOS Keychain, Linux Secret Service. Tự động di chuyển từ bộ lưu trữ JSON văn bản gốc trước đó
- Sau lần tải xuống đầu tiên, hoạt động hoàn toàn ngoại tuyến
- Model: `pyannote/speaker-diarization-3.1`

## Đồng bộ khẩu hình (Wav2Lip)

Khi được bật, ứng dụng sẽ áp dụng Wav2Lip GAN để đồng bộ hóa cử động miệng của đối tượng với âm thanh được lồng tiếng - người đó dường như nói ngôn ngữ đã dịch.

- Model (~416 MB) và repo được sao chép tự động trong lần sử dụng đầu tiên vào `~/.local/share/wav2lip/`
- Chạy trên CUDA (được khuyến nghị) hoặc CPU
- Tăng đáng kể thời gian xử lý
- Hoạt động hiệu quả nhất trên những video có một khuôn mặt duy nhất, rõ ràng

## Yêu cầu

- Python 3.10+ (trình cài đặt Windows tự động cung cấp 3.11.9)
- Windows 10/11 (x64), Linux hoặc macOS
- **Khuyến nghị sử dụng GPU NVIDIA** - xem bảng GPU bên dưới
- Dung lượng đĩa trống 20 GB để cài đặt đầy đủ (PyTorch CUDA, Whisper big-v3, XTTS, Wav2Lip)

> **ffmpeg và tất cả các gói Python được cài đặt tự động** trong lần khởi chạy đầu tiên nếu thiếu. Không cần thiết lập thủ công.

**Phụ thuộc hệ thống tùy chọn** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Khi được cài đặt, nó được sử dụng để duy trì cao độ, kéo dài thời gian trong dải chất lượng do cấu hình kiểm soát (mặc định 1,15-1,50, tối đa 1,65 đối với nội dung cứng), loại bỏ hiệu ứng "chipmunk" còn sót lại trên các giọng XTTS nhân bản. Đường dẫn chạy không thay đổi nếu không có nó (tự động chuyển sang ffmpeg `atempo`). Cấu hình chất lượng hiện ưu tiên thử lại bản dịch ngắn hơn là tăng tốc âm thanh cực cao.

### hỗ trợ GPU

Quy trình sử dụng năm thành phần tăng tốc GPU (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). Phạm vi phủ sóng GPU không đồng nhất giữa các nhà cung cấp:

| GPU | Windows | Linux | Ghi chú |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx trở lên, trình điều khiển CUDA 12.4) | ✅ Tăng tốc tối đa | ✅ Tăng tốc tối đa | **Được khuyến nghị.** Tất cả 5 thành phần đều chạy trên GPU. |
| **AMD** (Radeon) | ⚠️ chưa đầy đủ (DirectML không hỗ trợ XTTS và faster-whisper) | ⚠️ một phần (ROCm hoạt động cho Demucs/XTTS/pyannote nhưng faster-whisper chỉ hỗ trợ CUDA) | Hoạt động nhưng phiên mã Whisper vẫn tồn tại trên CPU và chiếm ưu thế trong tổng thời gian. |
| **Intel Arc** | ⚠️ Hỗ trợ XPU PyTorch chưa hoàn thiện | ⚠️ giống nhau | Chưa được thử nghiệm. |
| **Không (chỉ CPU)** | ✅ hoạt động | ✅ hoạt động | Dự kiến **chậm hơn 10-20×** so với thời gian thực. Một clip dài 5 phút có thể mất hơn 50 phút chỉ để phiên âm bằng Whisper big-v3. |

**VRAM NVIDIA được đề xuất:**

| VRAM | Các card đồ họa phổ biến | Kinh nghiệm |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Dùng được, không thể chạy đồng thời XTTS + Wav2Lip |
| 8 GB | RTX 3060 Ti, 4060 | Đường dẫn đầy đủ, không có lợi nhuận |
| **12 GB++** | **RTX 3060 12GB, 4070, 4080** | **Khuyến nghị - thoải mái** |
| 24GB | RTX 3090, 4090 | Công suất dự phòng cho lô lớn |

## Cài đặt

### Windows

1. Sao chép hoặc tải xuống kho lưu trữ này
2. Nhấp chuột phải vào `setup_windows.bat` → **Chạy với tư cách quản trị viên** → menu hiển thị `[1] Install`
3. Trình cài đặt tự động:
   - Cài đặt Python 3.11 nếu không có (toàn hệ thống)
   - Cài đặt Git for Windows nếu không có
   - Cài đặt tất cả các phần phụ thuộc Python (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps, v.v.)
   - Tải xuống và cài đặt ffmpeg
   - Cài đặt trình phát video tích hợp (python-mpv cộng với bản dựng libmpv trong `mpv-runtime`). Bước này là tùy chọn: nếu thất bại, mọi thứ khác sẽ hoạt động và khung trình phát sẽ giải thích những gì còn thiếu
   - Tạo **Lối tắt màn hình công cộng** (hiển thị với mọi tài khoản Windows trên PC)

> Trình cài đặt **nhiều người dùng**: mọi thứ đều được cài đặt trên toàn hệ thống trong `%ProgramFiles%\VideoTranslatorAI` và bất kỳ người dùng Windows nào trên máy đều thấy lối tắt sẵn sàng hoạt động. Công cụ xây dựng VS C++ **không còn cần thiết** - nhánh `coqui-tts` được duy trì cung cấp các gói bánh xe Python được biên dịch sẵn.

### Linux/macOS

```bash
# Sao chép kho lưu trữ
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Tùy chọn: cài đặt trước NVIDIA CUDA 12.4 PyTorch đã được thử nghiệm
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Tùy chọn: cài đặt sẵn tất cả các gói thời gian chạy Python thay vì để GUI
# cài đặt các gói bị thiếu trong lần chạy đầu tiên
pip install --break-system-packages -r requirements.txt

# Tùy chọn: trình phát video tích hợp (libmpv từ bản phân phối, python-mpv từ PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Tùy chọn: cài đặt dự án dưới dạng gói Python có thể chỉnh sửa
pip install --break-system-packages --no-deps -e .

# Khởi chạy từ nguồn
python video_translator_gui.py

# Hoặc, sau khi cài đặt gói/có thể chỉnh sửa
videotranslatorai
videotranslatorai --preflight
```

> Trong lần khởi chạy đầu tiên, GUI sẽ phát hiện mọi gói bị thiếu (faster-whisper, Demucs, Edge-TTS, v.v.) và tự động cài đặt chúng, truyền dữ liệu đầu ra tới cửa sổ nhật ký. ffmpeg cũng được cài đặt tự động thông qua `apt-get`/`dnf`/`pacman` (Linux) hoặc tải xuống từ GitHub (Windows).

> Tiêu đề hiển thị huy hiệu **Người chơi**. Khi thiếu libmpv hoặc python-mpv, khung bên trái sẽ cho biết nội dung còn thiếu và cung cấp **Cài đặt trình phát**: trên Linux, nó sử dụng trình quản lý gói thông qua pkexec (sau đó là `sudo -n`) và hiển thị lệnh thủ công khi cả hai đều không hoạt động; trên Windows nó hỏi trước khi tải xuống libmpv cho người dùng hiện tại (khoảng 32 MB).

### Hồ sơ yêu cầu

| Tập tin | Mục đích |
|------|---------|
| `requirements.txt` | Cài đặt thời gian chạy đầy đủ, tương thích ngược. |
| `requirements-core.txt` | Các gói đường dẫn mặc định được GUI/CLI sử dụng. |
| `requirements-optional.txt` | XTTS, mã thông báo MarianMT, nhật ký, VAD, móc khóa. |
| `requirements-wav2lip.txt` | Thời gian chạy Wav2Lip và ngăn xếp nhận diện khuôn mặt (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Ngăn xếp PyTorch đã được thử nghiệm với bánh xe NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Trình phát video tích hợp: python-mpv (cần libmpv từ hệ thống hoặc từ trình cài đặt Windows). |
| `requirements-dev.txt` | Các phần phụ thuộc nhẹ được CI/kiểm thử đơn vị sử dụng. |

## Gỡ cài đặt

### Windows

Chạy `setup_windows.bat` (nhấp chuột phải → **Chạy với tư cách quản trị viên**) và chọn `[3] Uninstall` từ menu. Ba chế độ phụ gỡ cài đặt được cung cấp:

| Chế độ | Yêu cầu quản trị viên | Phạm vi |
|------|----------------|-------|
| **[1] Gỡ cài đặt hoàn toàn - một cú nhấp chuột** | ✅ | Xóa thư mục ứng dụng, lối tắt Public Desktop, ffmpeg khỏi máy PATH, bộ đệm mô hình HF của mọi người dùng (Whisper/XTTS) và cấu hình (`HF token`) cũng như tất cả các gói Python AI được trình cài đặt cài đặt. Cuối cùng, nó cũng hỏi (chọn tham gia) xem có nên gỡ cài đặt âm thầm **Python 3.11** và **Git for Windows** thông qua chuỗi gỡ cài đặt yên tĩnh đăng ký của họ hay không. |
| **[2] Chỉ người dùng hiện tại** | ❌ | Chỉ xóa cấu hình VTAI, bộ đệm HF/XTTS của người dùng đang chạy và cài đặt cũ cho mỗi người dùng. **Giữ nguyên cài đặt trên toàn hệ thống** để các tài khoản Windows khác trên PC có thể tiếp tục sử dụng ứng dụng. |
| **[3] Tùy chỉnh - chi tiết** | ✅ cho các mục hệ thống, ❌ cho các mục người dùng | Lời nhắc Y/N cho từng danh mục: thư mục ứng dụng, lối tắt, PATH của máy, số lượt cài đặt cũ của mỗi người dùng, cấu hình/bộ nhớ đệm của mỗi người dùng, sau đó nhóm các gói Python (TTS, ngăn xếp PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, các tiện ích đường ống) và cuối cùng là Python 3.11 và Git tùy chọn. |

**Không bao giờ bị xóa tự động:** Công cụ xây dựng Visual Studio C++ (nếu có từ các lần chạy cũ hơn). Sử dụng *Ứng dụng và tính năng* trong Cài đặt Windows để xóa chúng theo cách thủ công nếu muốn.

### Linux/macOS

Không có trình gỡ cài đặt chuyên dụng - xóa thủ công:

```bash
# Các gói Python được cài đặt bởi trình cài đặt tự động của GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Dữ liệu người dùng và bộ đệm mô hình
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (chủ đề, thứ tự bảng điều khiển, cài đặt)
rm -f  ~/.videotranslatorai_config.json     # cấu hình cũ của phiên bản <= 1.9, nếu có
```

## Cách sử dụng

### Chẩn đoán

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Chạy chẩn đoán môi trường cục bộ mà không cần bắt đầu dịch hoặc cài đặt bất cứ thứ gì. `--preflight-lipsync` xử lý các gói khuôn mặt Wav2Lip theo yêu cầu, điều này rất hữu ích trước khi bật **Lip Sync**. GUI hiển thị kiểm tra cơ sở tương tự từ nút **Chẩn đoán** của bảng nhật ký. `--preflight-player` xử lý trình phát video tích hợp (python-mpv và libmpv có thể tải) theo yêu cầu. `python -m videotranslator.libmpv_runtime check` chỉ thăm dò libmpv (thoát 0 sẵn sàng, 2 không khả dụng).

### GUI

```bash
python video_translator_gui.py
```

**Bố cục:** cài đặt dịch hàng loạt nằm trong cột bên phải, dưới dạng một nhóm các bảng cài đặt: **Đầu vào**, **Dịch**, **Hồ sơ quy trình công việc**, **Bắt đầu** và các phần nâng cao có thể thu gọn (kiểu máy, công cụ dịch thuật, âm thanh, nhân bản giọng nói, đồng bộ khẩu hình, nhật ký hóa, tùy chọn, từ nóng). Khu vực lớn bên trái là **trình phát video tích hợp** (truyền tải, danh sách phát, âm thanh gốc A/B và lồng tiếng, phụ đề, ảnh chụp nhanh, toàn màn hình), với thanh **bản dịch thời gian thực** bên dưới. Kéo thẻ theo tiêu đề hoặc bằng tay cầm **≡** để di chuyển thẻ lên hoặc xuống cột; đơn hàng được lưu (`ui_panel_order`) và được khôi phục ở lần bắt đầu tiếp theo. Bảng nhật ký ở phía dưới có thể được ẩn bằng **Ẩn nhật ký**. Khi bắt đầu, cửa sổ sẽ mở ở giữa màn hình hiện tại (màn hình bên dưới con trỏ) và được phóng to, do đó, cửa sổ này hoạt động tốt trên thiết lập nhiều màn hình.

**Điều khiển trình phát video video:** các biểu tượng sử dụng màu sắc chức năng nhất quán trong mọi chủ đề, độc lập với màu nhấn đã chọn:

| Kiểm soát | Màu sắc |
|---------|--------|
| Phát video | màu xanh lá cây |
| Tạm dừng (thay thế Chơi trong khi chơi) | Hổ phách |
| Dừng phát lại | Màu đỏ san hô |
| Trước / lùi 10 giây / tiến 10 giây / tiếp theo | Màu xanh |
| Ảnh chụp nhanh | màu tím |
| Mở thư mục | Vàng |

Di chuột sẽ thêm nền có tông màu tinh tế. Các điều khiển không khả dụng là trung tính; điều hướng danh sách phát vẫn có thể sử dụng được sau khi dừng. Chú giải công cụ và chỉ báo tiêu điểm bàn phím vẫn có sẵn, vì vậy màu sắc không phải là cách duy nhất để xác định hành động.

**Từ các tập tin cục bộ:**
1. Nhấp vào **Thêm** để chọn một hoặc nhiều tệp video
2. Chọn ngôn ngữ nguồn và đích
3. Mở phần **Mẫu** và chọn mẫu Whisper (`small` là sự cân bằng tốt giữa tốc độ/độ chính xác)
4. Chọn giọng nói và điều chỉnh tốc độ TTS nếu cần
5. *(Tùy chọn)* Trong **Công cụ dịch** chọn **Google** (mặc định), **MarianMT** (cục bộ/ngoại tuyến), **DeepL Free** hoặc **Ollama LLM** (địa phương, được khuyên dùng để lồng tiếng)
6. *(Tùy chọn)* Bật **Nhân bản giọng nói** (XTTS v2) và/hoặc **nhận dạng người đang nói (ghi nhật ký)**
7. *(Tùy chọn)* Bật **Đồng bộ hóa môi** (Wav2Lip)
8. Nhấp vào **Bắt đầu dịch**

**Từ YouTube (hoặc bất kỳ trang web được hỗ trợ nào):**
1. Dán một hoặc nhiều URL vào trường **URL** (một URL trên mỗi dòng)
2. Cấu hình ngôn ngữ, model và giọng nói như bình thường
3. Nhấp vào **⬇ Tải xuống và dịch**

> yt-dlp hỗ trợ YouTube, Vimeo, Twitter/X, TikTok và [hơn 1000 trang web khác](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Thông báo sử dụng hợp lý:** Việc tải video xuống qua yt-dlp được các nền tảng như YouTube coi là quyền truy cập tự động và có thể vi phạm Điều khoản dịch vụ của họ. Việc sử dụng nhiều hoặc nhiều lần từ cùng một địa chỉ IP có thể dẫn đến chặn tạm thời (lỗi HTTP 429/yêu cầu đăng nhập). Sử dụng VPN hoặc thay đổi IP của bạn nếu bạn gặp lỗi tải xuống. Công cụ này chỉ dành cho mục đích sử dụng cá nhân, phi thương mại. Việc phân phối lại nội dung đã dịch có thể vi phạm bản quyền - luôn tôn trọng quyền của người sáng tạo ban đầu.

### Dịch thuật thời gian thực (phụ đề và lồng tiếng thử nghiệm)

Xem tệp cục bộ hoặc liên kết video theo yêu cầu đã được giải quyết với phụ đề đã dịch và bản dịch giọng nói tùy chọn. Sử dụng thanh bên dưới trình phát:

**Từ một liên kết:**

1. Dán liên kết vào trường **URL**
2. Đặt ngôn ngữ nguồn và đích, chọn giọng nói và điều chỉnh thanh trượt **Độ trễ**
3. Chọn **Giọng lồng tiếng** và/hoặc **Phụ đề**
4. Để chỉ nghe giọng nói đã dịch, hãy chọn **Tắt âm thanh gốc** trước khi bắt đầu (bằng tiếng Ý: **Silenzia originale**, bên cạnh hộp kiểm phụ đề)
5. Nhấp vào **Dịch trong thời gian thực** - liên kết được giải quyết và quá trình dịch bắt đầu

**Từ tệp đã tải:** tải video trong trình phát (Đầu vào -> Thêm, sau đó chọn video đó), để trống trường URL, chọn cài đặt trực tiếp tương tự và nhấp vào **Dịch trong thời gian thực**. URL được ưu tiên khi trường không trống.

- **Công cụ:** MarianMT (ngoại tuyến, mặc định), Google, DeepL hoặc Ollama. Nhận dạng giọng nói (Whisper) chạy cục bộ. Các mô hình ngoại tuyến cần tải xuống lần đầu.
- **Lồng tiếng:** thử nghiệm phát lại giọng nói Edge-TTS thông qua phiên bản mpv thứ hai. Nó yêu cầu truy cập internet và tách biệt với việc nhân bản giọng nói hàng loạt.
- **Tắt âm thanh gốc:** khả dụng cả trước khi bắt đầu và trong khi dịch. Nó làm im lặng toàn bộ nhạc nền gốc, bao gồm cả nhạc và hiệu ứng, nhưng vẫn để lại giọng nói được dịch. Nó không cô lập người nói trong âm thanh gốc. Tắt nó đi để khôi phục nhạc nền; nó đặt lại khi phiên trực tiếp kết thúc. Nút loa của máy nghe nhạc là nút tắt tiếng chung chứ không phải nút điều khiển độc lập này.
- **Tạm dừng và tìm kiếm:** các nút điều khiển trình phát video được kết nối với phiên trực tiếp; Đồng bộ hóa âm thanh từ đầu đến cuối vẫn cần các thử nghiệm chấp nhận dành riêng cho nền tảng.
- **Giới hạn hiện tại:** xử lý chồng chéo/làm mờ clip, hiệu chỉnh thời gian âm thanh và chấp nhận Windows vẫn mở. Các chương trình phát sóng trực tiếp đang phát triển chưa được hỗ trợ; nhãn chế độ trực tiếp không ngụ ý hỗ trợ việc nhập chương trình phát sóng khi nó phát triển. Xem [trạng thái triển khai và công việc còn lại](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Đối với video lồng tiếng đã lưu, hãy sử dụng **Tải xuống & Dịch** / **Bắt đầu dịch** thay vì xem trước trong thời gian thực.

### Khối công cụ dịch thuật và VPN

Hai khối khác nhau có thể xảy ra với các cách khắc phục khác nhau:

| Chặn | triệu chứng | sửa chữa |
|-------|---------|-----|
| **Tải xuống** (yt-dlp) | "Đăng nhập để xác nhận bạn không phải là bot", HTTP 429 | **VPN** / xoay IP hoặc đăng nhập vào YouTube trên trình duyệt của bạn (cookie được đọc tự động) |
| **Dịch** (điểm cuối miễn phí của Google) | "Google Translate không thể dịch... tốc độ yêu cầu bị giới hạn/bị chặn" | Sử dụng **MarianMT** (ngoại tuyến) hoặc **Ollama** (cục bộ) - không giới hạn tỷ lệ yêu cầu. VPN cũng có ích. Luồng hàng loạt hiện **tự động quay trở lại MarianMT** khi Google bị chặn. |

### Chủ đề và sự xuất hiện

Nhấp vào biểu tượng bánh răng trong tiêu đề để mở **Cài đặt**:

- **Chủ đề**: Tự động (tuân theo chế độ tối/sáng của hệ điều hành), Graphite (mặc định), Slate, Light, Neon.
- **Màu nhấn**: mặc định theo chủ đề hoặc xanh lam, xanh mòng két, tím, xanh lá cây, hổ phách, hồng.
- **Kích thước văn bản**: nhỏ, bình thường, lớn, cực lớn.
- **Ngôn ngữ giao diện**: 26 ngôn ngữ.

Các thay đổi được áp dụng ngay lập tức mà không cần khởi động lại và được lưu trong tệp cấu hình (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Khôi phục mặc định** mang lại chủ đề Graphite, giọng mặc định, kích thước văn bản thông thường và thứ tự mặc định của bảng cài đặt.

### Dòng lệnh

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Tất cả các lựa chọn:**

| Tùy chọn CLI | Mô tả | Mặc định |
|------|-------------|---------|
| `--lang-source` | Ngôn ngữ nguồn (`auto` để tự động phát hiện) | `auto` |
| `--lang-target` | Mã ngôn ngữ đích (ví dụ: `it`, `fr`, `de`) | `it` |
| `--voice` | Tên giọng nói Edge-TTS | auto |
| `--model` | Mẫu Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Điều chỉnh tốc độ TTS (ví dụ `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` hoặc `deepl` | `google` |
| `--deepl-key` | Khóa API DeepL Free | - |
| `--diarize` | Cho phép nhận dạng người đang nói (diarization) (pyannote) | - |
| `--hf-token` | Mã thông báo HuggingFace để ghi nhật ký | - |
| `--lipsync` | Áp dụng đồng bộ hóa môi Wav2Lip sau khi lồng tiếng | - |
| `--subs-only` | Chỉ tạo `.srt`, bỏ qua lồng tiếng | - |
| `--no-subs` | Bỏ qua thế hệ `.srt` | - |
| `--no-demucs` | Bỏ qua việc tách giọng nói/âm nhạc | - |
| `--output` / `-o` | Đường dẫn tập tin đầu ra | auto |
| `--output-dir` | Thư mục chứa các tệp đã dịch (một nơi, Windows và Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Xử lý nhiều tập tin | - |

### kiểm thử tích hợp với mô hình thực

Bộ thử nghiệm mặc định tránh việc tải xuống mô hình thực và hoạt động GPU lâu. Để chạy kiểm tra thực nghiệm chọn tham gia cho ngăn xếp cục bộ đã cài đặt:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Các bước kiểm tra này xác thực hoạt động nhập Wav2Lip thực, tính khả dụng của Torch CUDA, tính khả dụng của daemon Ollama và faster-Whisper trên giọng nói tổng hợp. Họ cố tình thất bại hoặc bỏ qua khi trạng thái trình điều khiển/daemon/mô hình cục bộ chưa sẵn sàng.

**Ví dụ:**

```bash
# Dịch video tiếng Ý sang tiếng Anh với MarianMT địa phương
# (tải xuống mô hình ~298 MB trong lần sử dụng đầu tiên, sau đó hoàn toàn ngoại tuyến)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Dịch bằng nhân bản giọng nói + nhận dạng người nói (ghi nhật ký)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Dịch bằng cách đồng bộ khẩu hình
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Chỉ có phụ đề (không lồng tiếng)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Các mẫu Whisper

| người mẫu | Kích thước | Tốc độ | Độ chính xác |
|-------|------|-------|----------|
| tiny | 75MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` là phiên bản chắt lọc của `large-v3` (4 lớp giải mã so với 32) - chất lượng gần như lớn với tốc độ khoảng `medium`. Mặc định được đề xuất trên GPU hiện đại khi tốc độ sao chép có vấn đề; chất lượng giảm sút đối với tài liệu đa ngôn ngữ là không đáng kể.

> Các mô hình được tải xuống tự động trong lần sử dụng đầu tiên.

## CLI mô-đun độc lập

Gói mô-đun hiển thị bốn công cụ hướng tới người dùng có thể được gọi trực tiếp mà không cần khởi chạy toàn bộ quy trình:

```bash
# Chiếu trước một video về sự hiện diện của khuôn mặt (Wav2Lip sẽ bỏ qua nếu vắng mặt).
python3 -m videotranslator.face_detector path/to/video.mp4
# lối ra 0 = có mặt, lối ra 1 = không có mặt

# Phân tích *_metrics.csv do build_dubbed_track tạo ra.
# Báo cáo P50/P75/P90/P95 của pre_stretch_ratio, sự cố dải âm thanh,
# kéo dài mức sử dụng công cụ và N ngoại lệ tệ nhất với văn bản mục tiêu của chúng.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Làm sạch văn bản cho TTS (viết lại dấu hai chấm, dấu chấm phẩy, dấu chấm lửng, dấu gạch ngang).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Ước tính độ khó khi lồng tiếng từ tệp phân đoạn .srt hoặc .json TRƯỚC KHI chạy TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Mỗi công cụ đều có `-h`/`--help` để có đầy đủ các tùy chọn. Chúng độc lập và tái sử dụng cùng các mô-đun mà quy trình lồng tiếng dựa vào, do đó, đầu ra của chúng luôn nhất quán với thời gian chạy.

## Giấy phép

MIT

### Các thành phần của bên thứ ba

Mã kho lưu trữ là MIT. Trình cài đặt tải xuống các thành phần bên dưới từ nguồn riêng của họ tại thời điểm cài đặt; dự án không phân phối lại chúng.

- **libmpv** (https://github.com/mpv-player/mpv), công cụ của trình phát video tích hợp. Windows: bản dựng LGPL của zhongfly (https://github.com/zhongfly/mpv-winbuild) được thử trước tiên; bản dựng GPL được ghim bởi shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) là bản dự phòng. `mpv-runtime\BUILD.txt` ghi lại nguồn, hương vị giấy phép và cam kết mpv, đồng thời văn bản giấy phép nằm bên cạnh tệp DLL. Linux: gói phân phối (`libmpv2`, `libmpv1`, `mpv-libs` hoặc `mpv`).
- **FFmpeg** bên trong libmpv (LGPL hoặc GPL, theo bản dựng libmpv).
- **python-mpv** (`mpv` trên PyPI), GPLv2+ hoặc LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), được trình cài đặt Windows sử dụng để giải nén libmpv và xóa sau đó.
- **Trình tải Vulkan** (Khronos, MIT và Apache-2.0), chỉ được tải xuống trên Windows khi thiếu `vulkan-1.dll`.
- **edge-tts** (LGPLv3), được sử dụng bởi quy trình lồng tiếng.
- **Mẫu MarianMT** (Helsinki-NLP), được tải xuống từ Hugging Face Hub trong lần sử dụng đầu tiên theo giấy phép của riêng họ (Apache-2.0 dành cho mẫu `opus-mt`, CC-BY-4.0 dành cho `opus-mt-tc-big`).
