"""Messages for a Python the pinned PyTorch does not support, in 26 languages.

Merged into UI_STRINGS at startup with :func:`merge_into`, like the other
string modules; the i18n tests check keys and placeholders in every language.
The check itself runs before any window (system_packages.relaunch_on_unsupported_python):
these lines explain, in the log or in a dialog, what it did or could not do.
"""

from __future__ import annotations

_KEYS = ("msg_python_unsupported", "msg_python_none", "msg_python_relaunched")

_T: dict[str, tuple[str, str, str]] = {
    "en": ('Video Translator AI was started with Python {version}, which PyTorch {torch} does not support: the AI packages cannot be installed for it. Start the app with Python {supported}.',
           'No Python with PyTorch was found on this PC: install Python {supported} and start the app with it.',
           'Started with Python {version}, which PyTorch {torch} does not support: restarted with {python}.'),
    "it": ("Video Translator AI è stato avviato con Python {version}, che PyTorch {torch} non supporta: i pacchetti IA non si possono installare per questa versione. Avvia l'app con Python {supported}.",
           "Su questo PC non è stato trovato nessun Python con PyTorch: installa Python {supported} e avvia l'app con quello.",
           'Avviato con Python {version}, che PyTorch {torch} non supporta: riavviato con {python}.'),
    "es": ('Video Translator AI se inició con Python {version}, que PyTorch {torch} no admite: los paquetes de IA no se pueden instalar para esa versión. Inicia la aplicación con Python {supported}.',
           'No se encontró ningún Python con PyTorch en este PC: instala Python {supported} e inicia la aplicación con él.',
           'Iniciado con Python {version}, que PyTorch {torch} no admite: reiniciado con {python}.'),
    "fr": ("Video Translator AI a été lancé avec Python {version}, que PyTorch {torch} ne prend pas en charge : les paquets d'IA ne peuvent pas être installés pour cette version. Lancez l'application avec Python {supported}.",
           "Aucun Python avec PyTorch n'a été trouvé sur ce PC : installez Python {supported} et lancez l'application avec lui.",
           'Lancé avec Python {version}, que PyTorch {torch} ne prend pas en charge : relancé avec {python}.'),
    "de": ('Video Translator AI wurde mit Python {version} gestartet, das PyTorch {torch} nicht unterstützt: Die KI-Pakete lassen sich für diese Version nicht installieren. Starten Sie die App mit Python {supported}.',
           'Auf diesem PC wurde kein Python mit PyTorch gefunden: Installieren Sie Python {supported} und starten Sie die App damit.',
           'Gestartet mit Python {version}, das PyTorch {torch} nicht unterstützt: neu gestartet mit {python}.'),
    "pt": ('O Video Translator AI foi iniciado com o Python {version}, que o PyTorch {torch} não suporta: os pacotes de IA não podem ser instalados para essa versão. Inicie o aplicativo com o Python {supported}.',
           'Nenhum Python com PyTorch foi encontrado neste PC: instale o Python {supported} e inicie o aplicativo com ele.',
           'Iniciado com o Python {version}, que o PyTorch {torch} não suporta: reiniciado com {python}.'),
    "nl": ('Video Translator AI is gestart met Python {version}, dat PyTorch {torch} niet ondersteunt: de AI-pakketten kunnen niet voor deze versie worden geïnstalleerd. Start de app met Python {supported}.',
           'Er is op deze pc geen Python met PyTorch gevonden: installeer Python {supported} en start de app daarmee.',
           'Gestart met Python {version}, dat PyTorch {torch} niet ondersteunt: opnieuw gestart met {python}.'),
    "ru": ('Video Translator AI запущен с Python {version}, который PyTorch {torch} не поддерживает: пакеты ИИ для этой версии установить нельзя. Запустите приложение с Python {supported}.',
           'На этом ПК не найден Python с PyTorch: установите Python {supported} и запустите приложение с ним.',
           'Запущено с Python {version}, который PyTorch {torch} не поддерживает: перезапущено с {python}.'),
    "uk": ('Video Translator AI запущено з Python {version}, який PyTorch {torch} не підтримує: пакети ШІ для цієї версії встановити неможливо. Запустіть застосунок із Python {supported}.',
           'На цьому ПК не знайдено Python із PyTorch: установіть Python {supported} і запустіть застосунок із ним.',
           'Запущено з Python {version}, який PyTorch {torch} не підтримує: перезапущено з {python}.'),
    "pl": ('Video Translator AI uruchomiono z Pythonem {version}, którego PyTorch {torch} nie obsługuje: pakietów AI nie da się zainstalować dla tej wersji. Uruchom aplikację z Pythonem {supported}.',
           'Na tym komputerze nie znaleziono Pythona z PyTorch: zainstaluj Pythona {supported} i uruchom aplikację z nim.',
           'Uruchomiono z Pythonem {version}, którego PyTorch {torch} nie obsługuje: uruchomiono ponownie z {python}.'),
    "cs": ('Video Translator AI byl spuštěn s Pythonem {version}, který PyTorch {torch} nepodporuje: balíčky AI pro tuto verzi nelze nainstalovat. Spusťte aplikaci s Pythonem {supported}.',
           'Na tomto počítači nebyl nalezen žádný Python s PyTorch: nainstalujte Python {supported} a spusťte aplikaci s ním.',
           'Spuštěno s Pythonem {version}, který PyTorch {torch} nepodporuje: restartováno s {python}.'),
    "hu": ('A Video Translator AI a Python {version} verzióval indult, amelyet a PyTorch {torch} nem támogat: az MI-csomagok ehhez a verzióhoz nem telepíthetők. Indítsa az alkalmazást Python {supported} verzióval.',
           'Ezen a gépen nem található PyTorch-ot tartalmazó Python: telepítse a Python {supported} verziót, és azzal indítsa az alkalmazást.',
           'Python {version} verzióval indult, amelyet a PyTorch {torch} nem támogat: újraindítva ezzel: {python}.'),
    "ro": ('Video Translator AI a fost pornit cu Python {version}, pe care PyTorch {torch} nu îl acceptă: pachetele de IA nu pot fi instalate pentru această versiune. Porniți aplicația cu Python {supported}.',
           'Pe acest PC nu a fost găsit niciun Python cu PyTorch: instalați Python {supported} și porniți aplicația cu el.',
           'Pornit cu Python {version}, pe care PyTorch {torch} nu îl acceptă: repornit cu {python}.'),
    "el": ('Το Video Translator AI ξεκίνησε με Python {version}, την οποία το PyTorch {torch} δεν υποστηρίζει: τα πακέτα ΤΝ δεν μπορούν να εγκατασταθούν για αυτή την έκδοση. Ξεκινήστε την εφαρμογή με Python {supported}.',
           'Δεν βρέθηκε Python με PyTorch σε αυτόν τον υπολογιστή: εγκαταστήστε την Python {supported} και ξεκινήστε την εφαρμογή με αυτήν.',
           'Ξεκίνησε με Python {version}, την οποία το PyTorch {torch} δεν υποστηρίζει: επανεκκίνηση με {python}.'),
    "da": ('Video Translator AI blev startet med Python {version}, som PyTorch {torch} ikke understøtter: AI-pakkerne kan ikke installeres til denne version. Start appen med Python {supported}.',
           'Der blev ikke fundet nogen Python med PyTorch på denne pc: installer Python {supported}, og start appen med den.',
           'Startet med Python {version}, som PyTorch {torch} ikke understøtter: genstartet med {python}.'),
    "sv": ('Video Translator AI startades med Python {version}, som PyTorch {torch} inte stöder: AI-paketen kan inte installeras för den versionen. Starta appen med Python {supported}.',
           'Ingen Python med PyTorch hittades på den här datorn: installera Python {supported} och starta appen med den.',
           'Startad med Python {version}, som PyTorch {torch} inte stöder: omstartad med {python}.'),
    "no": ('Video Translator AI ble startet med Python {version}, som PyTorch {torch} ikke støtter: AI-pakkene kan ikke installeres for denne versjonen. Start appen med Python {supported}.',
           'Ingen Python med PyTorch ble funnet på denne PC-en: installer Python {supported} og start appen med den.',
           'Startet med Python {version}, som PyTorch {torch} ikke støtter: startet på nytt med {python}.'),
    "fi": ('Video Translator AI käynnistettiin Python {version} -versiolla, jota PyTorch {torch} ei tue: tekoälypaketteja ei voi asentaa tälle versiolle. Käynnistä sovellus Python {supported} -versiolla.',
           'Tältä tietokoneelta ei löytynyt PyTorchin sisältävää Pythonia: asenna Python {supported} ja käynnistä sovellus sillä.',
           'Käynnistetty Python {version} -versiolla, jota PyTorch {torch} ei tue: käynnistetty uudelleen tulkilla {python}.'),
    "tr": ('Video Translator AI, PyTorch {torch} tarafından desteklenmeyen Python {version} ile başlatıldı: yapay zeka paketleri bu sürüm için kurulamaz. Uygulamayı Python {supported} ile başlatın.',
           'Bu bilgisayarda PyTorch içeren bir Python bulunamadı: Python {supported} kurun ve uygulamayı onunla başlatın.',
           'PyTorch {torch} tarafından desteklenmeyen Python {version} ile başlatıldı: {python} ile yeniden başlatıldı.'),
    "id": ('Video Translator AI dijalankan dengan Python {version}, yang tidak didukung PyTorch {torch}: paket AI tidak dapat dipasang untuk versi ini. Jalankan aplikasi dengan Python {supported}.',
           'Tidak ditemukan Python dengan PyTorch di PC ini: pasang Python {supported} dan jalankan aplikasi dengannya.',
           'Dijalankan dengan Python {version}, yang tidak didukung PyTorch {torch}: dimulai ulang dengan {python}.'),
    "vi": ('Video Translator AI đã được khởi động bằng Python {version}, phiên bản mà PyTorch {torch} không hỗ trợ: không thể cài các gói AI cho phiên bản này. Hãy khởi động ứng dụng bằng Python {supported}.',
           'Không tìm thấy Python nào có PyTorch trên máy này: hãy cài Python {supported} và khởi động ứng dụng bằng nó.',
           'Đã khởi động bằng Python {version}, phiên bản mà PyTorch {torch} không hỗ trợ: đã khởi động lại bằng {python}.'),
    "hi": ('Video Translator AI को Python {version} के साथ शुरू किया गया, जिसे PyTorch {torch} समर्थित नहीं करता: इस संस्करण के लिए AI पैकेज इंस्टॉल नहीं हो सकते। ऐप को Python {supported} के साथ शुरू करें।',
           'इस PC पर PyTorch वाला कोई Python नहीं मिला: Python {supported} इंस्टॉल करें और ऐप को उसके साथ शुरू करें।',
           'Python {version} के साथ शुरू हुआ, जिसे PyTorch {torch} समर्थित नहीं करता: {python} के साथ फिर से शुरू किया गया।'),
    "ar": ('تم تشغيل Video Translator AI باستخدام Python {version}، وهو إصدار لا يدعمه PyTorch {torch}: لا يمكن تثبيت حزم الذكاء الاصطناعي لهذا الإصدار. شغّل التطبيق باستخدام Python {supported}.',
           'لم يُعثر على أي Python مزوّد بـ PyTorch على هذا الجهاز: ثبّت Python {supported} وشغّل التطبيق به.',
           'بدأ التشغيل باستخدام Python {version} الذي لا يدعمه PyTorch {torch}: أُعيد التشغيل باستخدام {python}.'),
    "ja": ('Video Translator AI は Python {version} で起動されましたが、PyTorch {torch} はこのバージョンに対応していないため、AI パッケージをインストールできません。Python {supported} でアプリを起動してください。',
           'この PC に PyTorch を含む Python が見つかりませんでした。Python {supported} をインストールし、それでアプリを起動してください。',
           'PyTorch {torch} が対応していない Python {version} で起動されたため、{python} で再起動しました。'),
    "ko": ('Video Translator AI가 PyTorch {torch}에서 지원하지 않는 Python {version}으로 시작되어 이 버전에는 AI 패키지를 설치할 수 없습니다. Python {supported}으로 앱을 시작하세요.',
           '이 PC에서 PyTorch가 있는 Python을 찾지 못했습니다. Python {supported}을 설치하고 그것으로 앱을 시작하세요.',
           'PyTorch {torch}가 지원하지 않는 Python {version}으로 시작되어 {python}(으)로 다시 시작했습니다.'),
    "zh": ('Video Translator AI 使用 Python {version} 启动，但 PyTorch {torch} 不支持该版本，因此无法为其安装 AI 软件包。请使用 Python {supported} 启动应用。',
           '这台电脑上没有找到带 PyTorch 的 Python：请安装 Python {supported}，并用它启动应用。',
           '以 PyTorch {torch} 不支持的 Python {version} 启动，已改用 {python} 重新启动。'),
}

PYTHON_UI_STRINGS: dict[str, dict[str, str]] = {
    lang: dict(zip(_KEYS, values)) for lang, values in _T.items()
}


def merge_into(ui_strings: dict[str, dict[str, str]]) -> list[str]:
    """Add these strings to ``ui_strings`` in place; return the problems found."""
    problems: list[str] = []
    for lang, values in _T.items():
        if len(values) != len(_KEYS):
            problems.append(f"{lang}: {len(values)} strings for {len(_KEYS)} keys")
    for lang, entries in PYTHON_UI_STRINGS.items():
        bucket = ui_strings.get(lang)
        if bucket is None:
            problems.append(f"unknown language {lang!r}")
            continue
        for key, value in entries.items():
            existing = bucket.get(key)
            if existing is not None and existing != value:
                problems.append(f"collision {lang}.{key}")
                continue
            bucket[key] = value
    return problems
