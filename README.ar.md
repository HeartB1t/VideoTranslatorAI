# Video Translator AI

[كل اللغات](README_LANGUAGES.md) | [الإنجليزية](README.md)

أداة مفتوحة المصدر لنسخ الفيديو وترجمته ودبلجته إلى 26 لغة. يعمل Whisper محلياً؛
وتعتمد الترجمة والصوت على المحرك المختار.

## البدء السريع

في Windows شغّل `setup_windows.bat` كمسؤول واختر `[1] Install`. في Linux أو
macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

أضف ملفاً أو رابطاً، اختر اللغات والصوت، ثم ابدأ الترجمة. خيار **Silenzia
originale** يكتم الموسيقى والصوت الأصليين بالكامل ويبقي الصوت المترجم. الدبلجة
الفورية تجريبية، والبث المباشر غير مدعوم حالياً. راجع [README الكامل](README.md)
للتفاصيل التقنية والمتطلبات والترخيص.
