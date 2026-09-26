# Video Translator AI

[Tất cả ngôn ngữ](README_LANGUAGES.md) | [English](README.md)

Công cụ mã nguồn mở để chép lời, dịch và lồng tiếng video sang 26 ngôn ngữ.
Nhận dạng giọng nói Whisper chạy cục bộ; dịch thuật và tổng hợp giọng nói tùy
thuộc vào công cụ được chọn.

## Bắt đầu nhanh

Windows: chạy `setup_windows.bat` với quyền quản trị và chọn `[1] Install`.
Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Thêm tệp hoặc liên kết, chọn ngôn ngữ, giọng nói và công cụ dịch rồi bắt đầu.
**Silenzia originale** tắt toàn bộ âm thanh gốc, gồm cả nhạc và hiệu ứng. Lồng
tiếng thời gian thực vẫn đang thử nghiệm; chương trình chưa hỗ trợ các buổi phát
trực tiếp đang diễn ra. Xem [README tiếng Anh](README.md) để biết tài liệu đầy đủ.
