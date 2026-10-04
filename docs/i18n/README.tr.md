# 🎬 Video Translator AI

[Türkçe](../../README.md) | [Tüm çeviriler](README.md)

**Bu sayfayı şurada okuyun:** [Bahasa Indonesia](README.id.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Nederlands](README.nl.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Suomi](README.fi.md) · [Svenska](README.sv.md) · [Tiếng Việt](README.vi.md) · [Türkçe](README.tr.md) · [Ελληνικά](README.el.md) · [Русский](README.ru.md) · [Українська](README.uk.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Yerel işleme seçenekleriyle ve varsayılan olarak hiçbir API anahtarı gerektirmeden, videoları 26 dile otomatik olarak yazıya döken, çeviren ve yeniden dublaj yapan yapay zeka destekli video ses dublaj aracı. Whisper konuşma tanıma yerel olarak çalışır; Edge-TTS, Google Translate ve DeepL internet bağlantısı gerektirir. İsteğe bağlı özellikler (DeepL, konuşan kişilerin tanımlanması (günlük oluşturma)) bir API anahtarı veya erişim belirteci gerektirebilir.

![Video Translator AI ana penceresi: video oynatıcı ve çeviri panelleri](../../assets/screenshot.png)

> **v2.0** - modüler paket, yerel Ollama çevirisi, kalite profili düzenlemesi, kurulabilir Python meta verileri ve gerçek modellerle isteğe bağlı entegrasyon testleri. Değişikliklerin tam listesi için [GitHub Sürümleri](https://github.com/HeartB1t/VideoTranslatorAI/releases) ve işleme geçmişine bakın.

> **v2.1.0** - Windows yükleyicisi güçlendirildi (Microsoft Visual C++ çalışma zamanı, net bir kurulum günlüğü, GitHub Sürümlerinden kendi kendini güncelleme), daha temiz günlükler (her indirme için ilerleyen tek bir ilerleme çubuğu), GPU'su olmayan bilgisayarlarda yazılım tabanlı video kod çözme ve yükseltilmiş taşıma düğmeleri. Bkz. [GitHub Sürümleri](https://github.com/HeartB1t/VideoTranslatorAI/releases).

## Nasıl çalışır?

1. **Transkripsiyon** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) sesi metne dönüştürür (GPU hızlandırmalı)
2. **Ses/müzik ayrımı** - [Demucs](https://github.com/facebookresearch/demucs) vokalleri arka plan müziğinden ayırır
3. **Çeviri** - MarianMT (yerel, çevrimdışı), Google Translate, DeepL Free veya **Ollama LLM** (Qwen3, slota duyarlı kısa çeviriler)
4. **konuşan kişilerin tanımlanması (günlük oluşturma)** *(isteğe bağlı)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) her bölümde kimin konuştuğunu tanımlar
5. **ses dublajı** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ ses) veya [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (konuşmadaki her konuşmacı için ses klonlama)
6. **Karıştırma** - dublajlı sesin orijinal arka plan müziğiyle yeniden karıştırılması
7. **Normalleştirme** - son ses -23 LUFS'ye (EBU R128 yayın standardı) normalleştirildi
8. **Dudak Senkronizasyonu** *(isteğe bağlı)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip), ağız hareketlerini dublajlı sesle senkronize eder

## Özellikler

- 🖥️ Temalı GUI (Tkinter) - komut satırına gerek yok; Graphite, Slate, Light ve Neon temalarını, vurgu renklerini, metin boyutunu ve ayar panellerini sürükleyerek yeniden sıralayabilirsiniz
- 🕹️ **Görünümler** - ayarlardan eğlenceli stiller: Dex ve Handheld cep oyun konsolunu (piksel yazı tipi, kalın çerçeveler), CRT ve CRT Amber ise 80'lerin fosforlu monitörünü hatırlatır; videoda da kavis ve tarama çizgileri olur
- 🔊 **Seçmeden önce dinleyin** - sesin yanındaki hoparlör simgesi hedef dilde örnek bir cümle (Edge-TTS) ya da bir ElevenLabs sesinin ücretsiz örneğini çalar
- 🌍 **26 hedef dil**, dil başına birden fazla ses ile
- 🌐 **26 dilde kullanıcı arayüzü** - arayüzün kendisi dilinize uyum sağlar
- 🎬 **YouTube ve URL desteği** - herhangi bir YouTube bağlantısını yapıştırın ve doğrudan çevirin (yt-dlp tarafından desteklenmektedir)
- ▶️ **Entegre video oynatıcı** (libmpv/mpv) - renk kodlu aktarım kontrolleri, çalma listesi, A/B orijinal ve dublajlı ses, altyazı geçişi, anlık görüntü, tam ekran, klasörü açma
- ⏱️ **Gerçek zamanlı çeviri** - yerel bir dosyayı veya isteğe bağlı bir video bağlantısını çevrilmiş altyazılar ve bir gecikme kaydırıcısıyla izleyin; motorlar MarianMT / Google / DeepL / Ollama. Dublaj Edge-TTS'i ya da isteğe bağlı olarak ikinci bir mpv örneği üzerinden ElevenLabs seslerini kullanır; üst üste binen cümleler bekler, hızlanır veya kısılarak biter. Süren canlı yayınlar henüz desteklenmiyor.
- 🎵Demucs ile ses/müzik ayrımı (arka plan müziğini korur)
- 🔇 Canlı çeviri öncesinde ve sırasında kullanılabilen **Orijinal sesi kapat**, çevrilen sesin duyulabilir kalmasını sağlarken videonun müziğini susturur. Orijinal sesi geri yüklemek için bunu kapatın; canlı oturum sona erdiğinde sıfırlanır.
- 🧠 **MarianMT** - tamamen yerel, çevrimdışı sinirsel çeviri (Helsinki-NLP, istek hızı sınırı yok, API anahtarı yok)
- 🤖 **Ollama LLM çevirisi** *(v2.0'da yeni)* - doğal ses dublajı için slot bilinçli kısa çeviriler üreten yerel LLM (Qwen3, Llama, Mistral), ilk kullanımda modeli otomatik olarak algılar/kurur/başlatır/çeker
- 🎙️ **Ses klonlama** - Coqui XTTS v2, orijinal sesin sesini konuşan kişiyi hedef dilde (~1,8 GB model), segment başına uyarlamalı hız ve halüsinasyonlar üzerinde çoklu tohum yeniden deneme ile klonlar
- 👥 **konuşan kişilerin tanımlanması (günlük tutma)** - pyannote-audio 3.1 konuşan birden fazla kişiyi tanımlar; XTTS her sesi ayrı ayrı klonlar
- 💋 **Lip Sync** - Wav2Lip GAN, ağız hareketlerini dublajlı ses ile senkronize eder (~416 MB model)
- 🔊 **Ses normalleştirmesi** - otomatik -23 LUFS ses yüksekliği normalleştirmesi (EBU R128)
- ✏️ Altyazı düzenleyici - ses dublajından önce altyazıları inceleyin ve düzeltin
- 📦 Toplu işleme - birden fazla videoyu veya URL'yi aynı anda çevirin
- ⚡ CUDA aracılığıyla GPU hızlandırma (otomatik olarak CPU'ya geri döner)
- 📄 İsteğe bağlı `.srt` altyazı dışa aktarımı
- 🔁 **DeepL Free** çeviri motoru (isteğe bağlı - 500 bin karakter/ay, ücretsiz API anahtarı gerektirir)
- 🔧 **Otomatik kurulum** - eksik Python paketleri ve ffmpeg, ilk başlatmada otomatik olarak yüklenir
- 🧮 **Bu bilgisayar için modeller** - işlemciyi, RAM'i, GPU'yu, VRAM'i ve boş diski algılar, hız, denge veya kalite için konuşma tanıma, çeviri ve ses modelleri önerir, Whisper modellerini indirip doğrular ve kendi videonuzda ölçer
- 🗣️ **ElevenLabs sesleri** *(isteğe bağlı, çevrimiçi, ücretli)* - kendi API anahtarınızla canlı dublaj için doğal çok dilli sesler; anahtar veya kota yetmezse Edge-TTS devam eder
- 🧬 **Voicebox ile ses klonlama** *(isteğe bağlı)* - konuşanın sesini ayrı bir yerel [Voicebox](https://github.com/jamiepine/voicebox) sunucusuyla klonlar; çalışmıyorsa video Edge-TTS kullanır

## Desteklenen diller

Arapça, Çince, Çekçe, Danca, Felemenkçe, İngilizce, Fince, Fransızca, Almanca, Yunanca, Hintçe, Macarca, Endonezce, İtalyanca, Japonca, Korece, Norveççe, Lehçe, Portekizce, Romence, Rusça, İspanyolca, İsveççe, Türkçe, Ukraynaca, Vietnamca

## Ses Kataloğu

Edge-TTS ses kataloğu, `video_translator_gui.py`'nin üst kısmına yakın `LANGUAGES`'de tanımlanır. Bu sözlük, hedef dil adları, GUI sesli radyo düğmeleri ve `--voice` atlandığında CLI geri dönüş sesi için gerçeğin kaynağıdır.

Claude/proje bakım notları `CLAUDE.md`'de **Voice Catalog Source Of Truth** altında bu konumu yansıtır, böylece gelecekteki kod aracıları sesleri nerede güncelleyeceklerini ve README'nin kullanıcıları nereye yönlendireceğini bilir.

## Çeviri motorları

| Motor | Kurulum | Sınırlar | Kalite |
|--------|-------|--------|---------|
| **Google Translate** *(varsayılan)* | Yok | Resmi olmayan kazıma - büyük videolarda kısılabilir | ★★★★ |
| **MarianMT** | Yok - ilk kullanımda dil çifti başına ~298 MB indirme | Yok - indirmeden sonra tamamen çevrimdışı | ★★★★ |
| **DeepL Free** | [deepl.com](https://www.deepl.com/pro-api) adresinde ücretsiz API anahtarı | 500 bin karakter/ay | ★★★★★ |
| **Ollama Yüksek Lisans** *(sesli dublaj için önerilir - v2.0'da yeni)* | İlk kullanımda otomatik olarak yüklenir (~1 GB Ollama + 5 GB model) | Yok - tamamen yerel | ★★★★★ |

> **MarianMT**, ilk indirmeden sonra yerel olarak önbelleğe alınan [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) modellerini kullanır. Açık kaynak dili gerektirir (otomatik algılama desteklenmez; kaynak dili manuel olarak seçin). Gerekli Python paketleri (`sacremoses`, `sentencepiece`) eksikse ilk seçimde otomatik olarak yüklenir.

> **Ollama LLM** *(v2.0'da yeni)*, hedef zaman aralığının farkında olan çeviriler ürettiği için sesli dublaj için önerilen motordur. MarianMT'nin kelimenin tam anlamıyla çeviri yaptığı ve İngilizce'den ~%25 daha uzun İtalyanca/İspanyolca/Fransızca ürettiği durumlarda (TTS'de sesli ses sıkıştırmasını zorunlu kılar), LLM'den, kaynağa göre 0,85-0,95'lik tipik bir karakter oranı elde ederek, sözlü sunum için her bölümü kısa ve doğal tutması istenir. Varsayılan model `qwen3:8b`'dir (diskte 5,2 GB, ~6 GB VRAM); `qwen3:4b` (~3 GB) hafif seçenektir, `qwen3:14b` ise daha yüksek kaliteli seçenektir. Boru hattı Ollama ikili dosyasını otomatik olarak algılar, ilk kullanımda resmi yükleyici aracılığıyla otomatik olarak yükler (onay açılır penceresiyle), arka plan programını başlatır ve seçilen modeli çeker; manuel kurulum gerekmez. Herhangi bir şey eksikse otomatik olarak Google Translate'ye geçiş yapar.

## Ses Klonlama (XTTS v2)

Etkinleştirildiğinde uygulama, konuşmacının sesini orijinal videodan çıkarır ve sesi hedef dilde kopyalamak için referans olarak kullanır.

- Desteklenen diller: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Geriye kalan 9 dil için otomatik olarak geri dönüş olarak Edge-TTS kullanılır
- Model (~1,8 GB) ilk kullanımda otomatik olarak `~/.local/share/tts/`'ye indirilir
- **VAD filtreli referans** (v1.4): Daha iyi ses klonlama kalitesi için [silero-vad](https://github.com/snakers4/silero-vad) aracılığıyla orijinal sesten seçilen 10-15 saniyelik sürekli konuşma
- **Oluşturma hızı** yapılandırılabilir (`xtts_speed`, varsayılan `1.25`): Çevrilen metin kaynak yuvasından uzun olduğunda daha yüksek değerler, işlem sonrası ses sıkıştırma bozukluklarını azaltır. `~/.config/videotranslatorai/config.json` veya CLI `--xtts-speed` aracılığıyla ayarlama yapın
- CUDA veya CPU'da çalışır

## konuşan kişilerin tanımlanması (günlük tutma) (pyannote-audio)

Etkinleştirildiğinde uygulama, her segmentte kimin konuştuğunu tanımlar. Ses Klonlama ile birlikte her konuşmacının sesi ayrı ayrı kopyalanır; röportajlar, podcast'ler ve çok kişili videolar için idealdir.

- Ücretsiz bir [HuggingFace jetonu](https://huggingface.co/settings/tokens) gerektirir (tek seferlik kayıt)
- **Jeton, işletim sistemi anahtarlığı aracılığıyla güvenli bir şekilde saklanır** (v1.4): Windows Credential Manager, macOS Keychain, Linux Secret Service. Önceki düz metin JSON depolama alanından otomatik geçiş
- İlk indirmeden sonra tamamen çevrimdışı çalışır
- Modeli: `pyannote/speaker-diarization-3.1`

## Dudak Senkronizasyonu (Wav2Lip)

Etkinleştirildiğinde uygulama, deneğin ağız hareketlerini dublajlı sesle senkronize etmek için Wav2Lip GAN'ı uygular; kişi çevrilmiş dili konuşuyor gibi görünür.

- Model (~416 MB) ve repo, ilk kullanımda `~/.local/share/wav2lip/`'ye otomatik olarak klonlandı
- CUDA (önerilen) veya CPU üzerinde çalışır
- İşlem süresini önemli ölçüde artırır
- Tek ve açıkça görülebilen bir yüze sahip videolarda en iyi sonucu verir

## Bu bilgisayar için modeller

Gelişmiş ayarlar > Model > **Bu bilgisayar için modeller**, hiçbir şeyi değiştirmeden donanımı (işlemci, RAM, GPU ve kullanılabilir VRAM, boş disk) okuyan ve her aşama için bir model öneren bir pencere açar: dosyalar ve canlı için konuşma tanıma, çeviri ve ses.

- **Hız**, **Dengeli** veya **Kalite** seçin: her öneri gerekçelerini listeler.
- Diğer tüm seçenekler seçilebilir kalır ve bu bilgisayar için değerlendirilir: sığar, sınırda, çok büyük, disk yetersiz veya çevrimiçi hizmet.
- **İndir** eksik bir Whisper modelini ilerleme ve İptal ile getirir ve her dosyayı Hugging Face sağlama toplamlarıyla doğrular; düğmeye basmadan hiçbir şey indirilmez.
- **Performans testi** seçilen modeli yüklü videoda ölçer (yükleme, ilk cümle, hız); ses bilgisayardan asla çıkmaz.
- **Uygula** modelleri ayarlar; **Öncekini geri yükle** önceki seçimi geri getirir. NVIDIA GPU'lar CUDA ile kullanılır; AMD (ROCm) ve Apple GPU'lar gösterilir, ancak orada konuşma modelleri işlemcide çalışır.

## Voicebox (yerel sunucuyla ses klonlama)

[Voicebox](https://github.com/jamiepine/voicebox) (MIT), sesleri klonlayan ayrı bir programdır. Onu kendiniz kurun ve başlatın; bu uygulama yalnızca yerel API'sini çağırır ve onu asla kurmaz.

- Gelişmiş ayarlar > Ses Klonlama > **Voicebox**: adresi (varsayılan `http://127.0.0.1:17493`), motoru (varsayılan `chatterbox`) ayarlayın ve **Doğrula** düğmesine basın.
- Her video için konuşanın temiz bir örneğinden geçici bir ses klonlanır (konuşmacı ayrımıyla her konuşmacı için bir tane) ve ardından silinir.
- Voicebox API'sinde kimlik doğrulama olmadığı için yalnızca bu bilgisayardaki bir adres kabul edilir.
- Voicebox yanıt vermezse veya hedef dili desteklemezse video Edge-TTS ile dublajlanır.

## Ses çıkarma

Sesi çevirmek yerine yerel bir dosyadan veya bir URL'den çıkarın. Bir biçim seçin (MP3, M4A, Opus, OGG, FLAC veya WAV) ve kayıplı biçimler için bir bit hızı. Yalnızca enstrümantal modu, Demucs ile sesi kaldırır ve yalnızca müziği bırakır.

Komut satırından:

```bash
python video_translator_gui.py video.mp4 --extract-audio --audio-format mp3 --audio-bitrate 320
python video_translator_gui.py video.mp4 --extract-audio --instrumental --audio-format flac
```

Grafik arabirimde ses çıkarma denetimleri Girdi kartındadır: bir biçim ve bit hızı seçin, yalnızca müziği bırakmak için yalnızca enstrümantal seçeneğini etkinleştirin, ardından Çıkar düğmesine basın.

## Gereksinimler

- Python 3.10+ (Windows yükleyicisi 3.11.9'u otomatik olarak hazırlar)
- Windows 10/11 (x64), Linux veya macOS
- **NVIDIA GPU şiddetle tavsiye edilir** - aşağıdaki GPU tablosuna bakın
- Tam kurulum için 20 GB boş disk alanı (PyTorch CUDA, Whisper büyük-v3, XTTS, Wav2Lip)

> **ffmpeg ve tüm Python paketleri eksikse ilk başlatmada otomatik olarak yüklenir**. Manuel kurulum gerekmez.

**İsteğe bağlı sistem bağımlılığı** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Kurulduğunda, profil kontrollü kalite bandında (varsayılan 1,15-1,50, sert içerik için 1,65'e kadar) perdeyi koruyan zaman uzatma için kullanılır ve klonlanmış XTTS seslerinde kalan "sincap" efektini ortadan kaldırır. Boru hattı bu olmadan değişmeden çalışır (ffmpeg `atempo`'ye otomatik geri dönüş). Kaliteli profiller artık aşırı ses hızlandırma yerine ekstra kısa çeviri yeniden denemelerini tercih ediyor.

### GPU desteği

Boru hattı beş GPU hızlandırmalı bileşen kullanıyor (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). GPU kapsamı satıcılar arasında aynı değildir:

| GPU | Windows | Linux | Notlar |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx veya daha yenisi, CUDA 12.4 sürücüsü) | ✅ tam hızlanma | ✅ tam hızlanma | **Önerilen.** 5 bileşenin tümü GPU'da çalışır. |
| **AMD** (Radeon) | ⚠️ eksik (DirectML, XTTS ve faster-whisper'yi desteklemez) | ⚠️ kısmi (ROCm, Demucs/XTTS/pyannote için çalışır ancak faster-whisper yalnızca CUDA'yı destekler) | Çalışıyor ancak Whisper transkripsiyonu CPU'da kalıyor ve toplam süreye hakim oluyor. |
| **Intel Arc** | ⚠️ olgunlaşmamış PyTorch XPU desteği | ⚠️ aynı | Test edilmedi. |
| **Yok (yalnızca CPU)** | ✅ çalışır | ✅ çalışır | Gerçek zamandan **10-20 kat daha yavaş** bekleyin. 5 dakikalık bir klibin yalnızca Whisper büyük-v3 ile metne dönüştürülmesi 50'den fazla dakika sürebilir. |

**Önerilen NVIDIA VRAM:**

| VRAM | Yaygın ekran kartları | Deneyim |
|------|---------------|-----------|
| 6GB | GTX 1660, RTX 2060 | Kullanılabilir, XTTS + Wav2Lip aynı anda çalıştırılamaz |
| 8GB | RTX 3060Ti, 4060 | Tam boru hattı, marj yok |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Önerilen - rahat** |
| 24GB | RTX 3090, 4090 | Büyük partiler için yedek kapasite |

## Kurulum

### Windows

Adım adım, komut satırına gerek yok. Temiz bir Windows 11 bilgisayarda test edildi.

1. Projeyi **indirin**: yeşil **Code** düğmesi → **Download ZIP**, veya [GitHub Sürümleri](https://github.com/HeartB1t/VideoTranslatorAI/releases)'nden en son zip dosyası. Herhangi bir klasöre, örneğin Masaüstüne, çıkarın.
2. **Yükleyin**: `setup_windows.bat`'ye sağ tıklayın → **Yönetici olarak çalıştır** → `1` tuşuna basın (Yükle). SmartScreen "Windows bilgisayarınızı korudu" derse, **Diğer bilgiler** → **Yine de çalıştır**'a tıklayın: betik düz metindir, Not Defteri ile açabilirsiniz.
3. **Bekleyin**: hızlı bağlantılı temiz bir bilgisayarda yaklaşık 15 dakika ve 8 GB disk alanı gerekir. Yükleyici şu sırayla indirir ve kurar:
   - Eksikse Python 3.11 (sistem çapında) ve Microsoft Visual C++ çalışma zamanı
   - Python paketleri: PyTorch (NVIDIA GPU varsa CUDA 12.4, yoksa CPU sürümü), faster-whisper, Demucs, coqui-tts, pyannote ve Wav2Lip yığını
   - Git for Windows (Wav2Lip için), ffmpeg ve entegre video oynatıcı (`mpv-runtime` içinde libmpv; isteğe bağlıdır, onsuz da her şey çalışır)
   - bilgisayardaki her Windows hesabı için bir **Masaüstü kısayolu** ve uygulama ile **Video Translator AI'yi Güncelle**'yi içeren bir **Başlat Menüsü** klasörü
4. **Başlatın**: Masaüstü kısayolundan veya Başlat Menüsünden başlatın. NVIDIA GPU olmadan uygulama işlemciyle çalışır, sadece daha yavaş: küçük bir Whisper modeli seçin.

> Her şey `%ProgramFiles%\VideoTranslatorAI` altında sistem genelinde yüklenir, böylece bilgisayardaki her Windows kullanıcısı kısayolu hazır bulur. `setup_windows.bat`'nin her çalıştırılması `%USERPROFILE%\VideoTranslatorAI-setup.log` dosyasına bir günlük yazar: bir sorunu bildirirken bunu ekleyin. Yükleyici **KURULUM TAMAMLANMADI** ile biterse, tekrar çalıştırın ve `[2] Repair / Update` seçeneğini seçin. VS C++ Derleme Araçlarına gerek yoktur: bakımı yapılan `coqui-tts` çatalı önceden derlenmiş tekerlek paketleri sağlar.

### Linux / macOS

```bash
# Python 3.11 ile 3.13 arası gerekir (PyTorch'un 3.14 için henüz paketi yok): python3'ü 3.14 olan bir dağıtımda aşağıdaki komutlarda python3.13 kullanın
# Depoyu klonla
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# İsteğe bağlı: test edilen NVIDIA CUDA 12.4 PyTorch yığınını öne yükleyin
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# İsteğe bağlı: GUI'ye izin vermek yerine tüm Python çalışma zamanı paketlerini önceden yükleyin
# ilk çalıştırmada eksik paketleri yükleyin
pip install --break-system-packages -r requirements.txt

# İsteğe bağlı: entegre video oynatıcı (dağıtımdan libmpv, PyPI'den python-mpv)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# İsteğe bağlı: projeyi düzenlenebilir bir Python paketi olarak yükleyin
pip install --break-system-packages --no-deps -e .

# Kaynaktan başlat
python video_translator_gui.py

# Veya düzenlenebilir/paket kurulumundan sonra
videotranslatorai
videotranslatorai --preflight
```

> İlk başlatmada GUI, eksik paketleri (faster-whisper, Demucs, Edge-TTS, vb.) algılar ve çıktıyı günlük penceresine aktararak bunları otomatik olarak yükler. ffmpeg ayrıca `apt-get` / `dnf` / `pacman` (Linux) aracılığıyla otomatik olarak yüklenir veya GitHub'dan (Windows) indirilir. PyTorch'un desteklemediği bir Python ile başlatılırsa uygulama, bilgisayarda bulunan desteklenen bir Python ile kendiliğinden yeniden başlar.

> Başlıkta **Oyuncu** rozeti gösteriliyor. Libmpv veya python-mpv eksik olduğunda, sol bölmede neyin eksik olduğu belirtilir ve **Oynatıcıyı yükle** seçeneği sunulur: Linux'ta pkexec (sonra `sudo -n`) aracılığıyla paket yöneticisini kullanır ve ikisi de çalışmadığında manuel komutu gösterir; Windows'ta geçerli kullanıcı için libmpv'yi indirmeden önce sorar (yaklaşık 32 MB).

### Gereksinim profilleri

| Dosya | Amaç |
|------|---------|
| `requirements.txt` | Tam, geriye dönük uyumlu çalışma zamanı kurulumu. |
| `requirements-core.txt` | GUI/CLI tarafından kullanılan varsayılan işlem hattı paketleri. |
| `requirements-optional.txt` | XTTS, MarianMT belirteçleri, günlük tutma, VAD, anahtarlık. |
| `requirements-wav2lip.txt` | Wav2Lip çalışma zamanı ve yüz algılama yığını (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch yığını NVIDIA CUDA 12.4 tekerlekleriyle test edildi. |
| `requirements-player.txt` | Entegre video oynatıcı: python-mpv (sistemden veya Windows yükleyicisinden libmpv gerekir). |
| `requirements-dev.txt` | CI/birim testleri tarafından kullanılan hafif bağımlılıklar. |

## Güncelle

### Windows

Başlat Menüsü → **Video Translator AI** → **Video Translator AI'yi Güncelle** (yönetici izni ister) veya `setup_windows.bat`'yi yönetici olarak çalıştırıp `[2] Repair / Update` seçeneğini seçin. Yükleyici [GitHub Sürümleri](https://github.com/HeartB1t/VideoTranslatorAI/releases)'ni kontrol eder: daha yeni bir sürüm varsa sürümü indirir, SHA256 sağlama toplamını doğrular ve yükler; aksi takdirde mevcut dosyaları onarır. Ayarlarınız, kaydedilmiş anahtarlarınız, indirilen modelleriniz ve çevrilmiş videolarınız korunur. İnternet bağlantısı olmadan güncelleme atlanır ve onarım devam eder.

### Linux / macOS

```bash
cd VideoTranslatorAI
git pull
pip install --break-system-packages -r requirements.txt
```

## Kaldır

### Windows

`setup_windows.bat`'yi çalıştırın (sağ tıklayın → **Yönetici olarak çalıştır**) ve menüden `[3] Uninstall`'yi seçin. Üç kaldırma alt modu sunulmaktadır:

| Mod | Yönetici gerekli | Kapsam |
|------|----------------|-------|
| **[1] Tam kaldırma - tek tıklama** | ✅ | Uygulama klasörünü, Masaüstü kısayolunu ve Başlat Menüsü girişlerini, makine PATH'sinden ffmpeg'i, her kullanıcının HF model önbelleğini (Whisper/XTTS) ve yapılandırmayı (`HF token`) ve yükleyici tarafından yüklenen tüm Python AI paketlerini kaldırır. Sonunda ayrıca **Python 3.11** ve **Git for Windows**'nin kayıt defteri sessiz kaldırma dizeleri aracılığıyla sessizce kaldırılıp kaldırılmayacağını da sorar (katılmayı tercih eder). Python 3.11 kaldırıldığında pip'in onun için geçerli kullanıcının klasörüne kurduğu paketler (`%APPDATA%\Python\Python311`) de silinir; başka bir Python 3.11 kurulu kalırsa silinmez. |
| **[2] Yalnızca mevcut kullanıcı** | ❌ | Yalnızca çalışan kullanıcının VTAI yapılandırmasını, HF/XTTS önbelleğini ve kullanıcı başına eski yüklemeyi kaldırır. **Sistem genelindeki kurulumu olduğu gibi bırakır**, böylece bilgisayardaki diğer Windows hesapları uygulamayı kullanmaya devam edebilir. |
| **[3] Özel - ayrıntılı** | ✅ sistem öğeleri için, ❌ kullanıcı öğeleri için | Her kategori için E/H istemi: uygulama klasörü, kısayol, makine PATH'i, kullanıcı başına eski yüklemeler, kullanıcı başına yapılandırmalar/önbellekler, ardından gruplandırılmış Python paketleri (TTS, PyTorch yığını, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, ardışık düzen yardımcı programları) ve son olarak isteğe bağlı Python 3.11 ve Git. |

Her mod, programın kullanıcı için sakladıklarını da kaldırır: yapılandırma ve günlük kayıtlar (`%APPDATA%\VideoTranslatorAI`), oynatıcı, JavaScript ve Wav2Lip çalışma ortamlarını içeren program verileri (`%LOCALAPPDATA%\VideoTranslatorAI`), gerçek zamanın geçici dosyaları (`%TEMP%\VideoTranslatorAI`), MarianMT modelleri ve Windows Kimlik Bilgisi Yöneticisi'nde kayıtlı anahtarlar (HF belirteci, ElevenLabs). Anahtarlar her Windows hesabına aittir: her hesap kendi anahtarlarını `[2]` ile kaldırır.

**Asla otomatik olarak kaldırılmaz:** Visual Studio C++ Derleme Araçları (daha eski çalıştırmalarda mevcutsa) ve diğer programların paylaştığı Microsoft Visual C++ çalışma zamanı. İsterseniz bunları manuel olarak kaldırmak için Windows Ayarlarında *Uygulamalar ve özellikler* seçeneğini kullanın. Kurulum günlüğü `%USERPROFILE%\VideoTranslatorAI-setup.log` kasıtlı olarak saklanır.

### Linux / macOS

Özel bir kaldırıcı yok - manuel olarak kaldırın:

```bash
# GUI'nin otomatik yükleyicisi tarafından yüklenen Python paketleri
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Kullanıcı verileri ve model önbellekleri
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip ~/.cache/wav2lip
rm -rf ~/.config/videotranslatorai          # yapılandırma (temalar, panel sırası, ayarlar)
rm -rf ~/.local/share/fonts/VideoTranslatorAI   # görünümlerin yazı tipleri
rm -rf ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt*   # MarianMT çeviri modelleri
rm -rf ~/.local/share/VideoTranslatorAI                          # program verileri (yt-dlp için JavaScript çalışma ortamı)
rm -rf "${TMPDIR:-/tmp}/VideoTranslatorAI"                       # gerçek zamanın geçici dosyaları
# kayıtlı anahtarlar (HF belirteci, ElevenLabs)
python3 -c "import keyring; [keyring.delete_password('VideoTranslatorAI', u) for u in ('hf_token', 'elevenlabs_api_key') if keyring.get_password('VideoTranslatorAI', u)]"
rm -f  ~/.videotranslatorai_config.json     # <= 1.9 sürümlerinin eski yapılandırması (varsa)
```

## Kullanım

### Teşhis

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Çeviriyi başlatmadan veya herhangi bir şey yüklemeden yerel ortam teşhisini çalıştırır. `--preflight-lipsync`, Wav2Lip yüz paketlerini gerektiği gibi ele alır; bu, **Lip Sync**'i etkinleştirmeden önce faydalıdır. GUI, günlük panelinin **Teşhis** düğmesinden aynı temel kontrolü sunar. `--preflight-player`, entegre video oynatıcıyı (python-mpv ve yüklenebilir bir libmpv) gerektiği gibi ele alır. `python -m videotranslator.libmpv_runtime check`, libmpv'yi tek başına araştırır (çıkış 0 hazır, 2 kullanılamaz).

**Günlük dosyası:** günlük panelinin gösterdiği her şey (her tıklama ve seçim, sonuçlar, işlem adımları, ayrıntılarıyla hatalar) yapılandırmanın yanındaki `logs/videotranslator.log` dosyasına da kaydedilir: Linux'ta `~/.config/videotranslatorai/logs/`, Windows'ta `%APPDATA%\VideoTranslatorAI\logs\`. Günde bir dosya, son 7 gün saklanır; **Tanılama** düğmesi yolu gösterir. Bir sorun bildirirken ekleyin. API anahtarları ve alanlara yazılan metin asla yazılmaz. Her satır zamanı, düzeyi (bilgi, uyarı, hata; arayüz dilinde, uyarılar ve hatalar panelde renkli) ve alanı gösterir, örneğin tıklamalar için [ui], çeviriler için [job], gerçek zaman için [live]; her başlatmada sürüm, sistem, GPU ve ayarları içeren bir başlık yazılır.

### GUI

```bash
python video_translator_gui.py
```

**Düzen:** toplu çeviri ayarları, bir dizi ayar paneli olarak sağdaki sütunda bulunur: **Giriş**, **Çeviri**, **İş akışı profili**, **Başlangıç** ve daraltılabilir gelişmiş bölümler (model, çeviri motoru, ses, ses klonlama, dudak senkronizasyonu, günlük tutma, seçenekler, özel kelimeler). Soldaki geniş alan **entegre video oynatıcıdır** (aktarım, oynatma listesi, A/B orijinal ve dublajlı ses, altyazılar, anlık görüntü, tam ekran), altında **gerçek zamanlı çeviri** çubuğu bulunur. Bir kartı sütunda yukarı veya aşağı taşımak için başlığından veya **≡** tutamacından sürükleyin; sipariş kaydedilir (`ui_panel_order`) ve bir sonraki başlangıçta geri yüklenir. Alt kısımdaki günlük paneli **Günlüğü gizle** seçeneğiyle gizlenebilir. Başlangıçta pencere geçerli monitörde (işaretçinin altındaki) ortalanmış olarak açılır ve ekranı kaplar, böylece çoklu monitör kurulumunda iyi çalışır.

**Video video oynatıcı kontrolleri:** simgeler, seçilen vurgu renginden bağımsız olarak her temada tutarlı işlevsel renkler kullanır:

| Kontrol | Renk |
|---------|--------|
| Videoyu oynat | Yeşil |
| Duraklat (oynatma sırasında Oynat'ın yerine geçer) | kehribar |
| Oynatmayı durdur | Mercan kırmızısı |
| Geri / 10 sn geri / 10 sn ileri / sonraki | Mavi |
| Anlık Görüntü | Menekşe |
| Klasörü aç | Altın |

Fareyle üzerine gelme, ince renkli bir arka plan ekler. Kullanılamayan kontroller nötrdür; Çalma listesi gezinmesi Durdurulduktan sonra kullanılabilir durumda kalır. Araç ipuçları ve klavye odak göstergeleri hâlâ mevcut olduğundan, eylemleri tanımlamanın tek yolu renk değildir.

**Yerel dosyalardan:**
1. Bir veya daha fazla video dosyası seçmek için **Ekle**'yi tıklayın
2. Kaynak ve hedef dili seçin
3. **Model** bölümünü açın ve bir Whisper modeli seçin (`small` iyi bir hız/doğruluk dengesidir)
4. Bir ses seçin ve gerekirse TTS hızını ayarlayın
5. *(İsteğe bağlı)* **Çeviri motorunda** **Google** (varsayılan), **MarianMT** (yerel/çevrimdışı), **DeepL Free** veya **Ollama LLM** (yerel, sesli dublaj için önerilir) öğesini seçin.
6. *(İsteğe bağlı)* **Ses Klonlamayı** (XTTS v2) ve/veya **konuşan kişilerin tanımlanmasını (günlük oluşturma)** etkinleştirin
7. *(İsteğe bağlı)* **Dudak Senkronizasyonu**'nu etkinleştirin (Wav2Lip)
8. **Çeviriyi Başlat**'ı tıklayın

**YouTube'dan (veya desteklenen herhangi bir siteden):**
1. **URL** alanına bir veya daha fazla URL yapıştırın (her satıra bir tane)
2. Dili, modeli ve sesi her zamanki gibi yapılandırın
3. **⬇ İndir ve Çevir**'i tıklayın

> yt-dlp; YouTube, Vimeo, Twitter/X, TikTok ve [1000'den fazla diğer siteyi](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) destekler.

> ⚠️ **Adil kullanım bildirimi:** Videoların yt-dlp aracılığıyla indirilmesi, YouTube gibi platformlar tarafından otomatik erişim olarak kabul edilir ve Hizmet Şartlarını ihlal edebilir. Aynı IP adresinin yoğun veya tekrarlı kullanımı, geçici engellemelere (HTTP 429 / oturum açmayı gerektiren hatalar) neden olabilir. İndirme hatalarıyla karşılaşırsanız bir VPN kullanın veya IP'nizi değiştirin. Bu araç yalnızca ticari olmayan, kişisel kullanıma yöneliktir. Çevrilmiş içeriğin yeniden dağıtımı telif hakkını ihlal edebilir; her zaman orijinal içerik oluşturucunun haklarına saygı gösterin.

### Gerçek zamanlı çeviri (altyazılar ve deneysel sesli dublaj)

Yerel bir dosyayı veya çevrilmiş altyazılar ve isteğe bağlı sözlü çeviri içeren çözümlenmiş isteğe bağlı video bağlantısını izleyin. Oynatıcının altındaki çubuğu kullanın:

**Bir bağlantıdan:**

1. **URL** alanına bir bağlantı yapıştırın
2. Kaynağı ve hedef dili ayarlayın, bir ses seçin ve **Gecikme** kaydırıcısını ayarlayın
3. **Dublajlı ses** ve/veya **Altyazılar**'ı seçin
4. Yalnızca çevrilmiş sesi duymak için, başlamadan önce **Orijinal sesi kapat** seçeneğini seçin (İtalyanca: **Silenzia originale**, altyazı onay kutusunun yanında)
5. **Gerçek zamanlı çevir**'i tıklayın; bağlantı çözülür ve çeviri başlar

**Yüklenen bir dosyadan:** oynatıcıya bir video yükleyin (Giriş -> Ekle, ardından seçin), URL alanını boş bırakın, aynı canlı ayarları seçin ve **Gerçek zamanlı olarak çevir**'i tıklayın. Alan boş olmadığında URL önceliklidir.

- **Motor:** MarianMT (çevrimdışı, varsayılan), Google, DeepL veya Ollama. Konuşma tanıma (Whisper) yerel olarak çalışır. Çevrimdışı modellerin ilk indirilmesi gerekir.
- **Gecikme:** gecikmeli modda bir dosyada, görüntü bir duraklamadan sonra devam etmeden önce kaç saniyelik çevirinin biriktirildiği (sesle en az 8 sn, yalnızca altyazıyla 4 sn). Görüntü durmaya devam ederse tampon 4 sn artarak 30 sn'ye kadar büyür ve çubuk bunu bildirir.
- **Ses dublajı:** ikinci bir mpv örneği aracılığıyla deneysel Edge-TTS konuşma oynatma. İnternet erişimi gerektirir ve toplu ses klonlamadan farklıdır.
- **ElevenLabs sesi:** isteğe bağlı, Gelişmiş ayarlar > Ses Klonlama > **ElevenLabs canlı ses** altında. API anahtarınızı girin, doğrulayın, hedef dili konuşan bir model ve bir ses seçin. Çevrilen metin ElevenLabs'e gönderilir (karakter başına ücretli); anahtar sistem anahtarlığında kalır. Anahtar veya kota yetmezse Edge-TTS devam eder. Gerçek zamanlı çubuğun **ElevenLabs…** düğmesinden de açılır; çubuğun satırı seslendirmenin hangi sesi kullanacağını gösterir.
  - ElevenLabs ücretsiz planı (27 Eylül 2026'da kontrol edildi): API üzerinden yalnızca varsayılan sesler (Roger, Sarah, George, River...) çalışır; ayda 10.000 karakter ve aynı anda en fazla 4 istek. Pencere, ücretli plan gerektiren sesleri işaretler.
  - ElevenLabs kitaplığındaki sesler, klonlanmış sesler ve daha fazla karakter, ElevenLabs'ten kendi fiyat ve koşullarıyla satın alınan ücretli bir ElevenLabs aboneliği gerektirir ([ElevenLabs pricing](https://elevenlabs.io/pricing)). VideoTranslatorAI ücretsiz kalır, ElevenLabs ile bağlantılı değildir ve ona ihtiyaç duymaz: Edge-TTS ücretsiz varsayılan sestir.
  - Gerçek zaman için modeller, ilk ses yaklaşık: Flash v2.5 0,2 sn, Turbo v2.5 0,2 sn, v3 Conversational 0,4 sn. Multilingual v2 (0,9 sn) ve v3 (1-2 sn) daha zengin duyulur ama videonun gerisinde kalır; Turbo v2 ve Flash v2 yalnızca İngilizce konuşur.
  - ElevenLabs bir cümleyi reddettiğinde (anahtar, plan, bulunamayan ses veya model, dil, biten karakterler, çok fazla istek), gerçek zamanlı çubuk nedenini söyler ve günlük ElevenLabs'in kendi mesajını saklar.
- **Orijinal sesi kapat:** hem başlamadan önce hem de çeviri sırasında kullanılabilir. Müzik ve efektler de dahil olmak üzere orijinal film müziğinin tamamını susturur ancak çevrilen sesi duyulabilir halde bırakır. Orijinal seste konuşan kişiyi izole etmez. Film müziğini geri yüklemek için onu kapatın; canlı oturum sona erdiğinde sıfırlanır. Müzikçaların hoparlör düğmesi, bu bağımsız kontrol değil, genel sessizdir.
- **Duraklat ve ara:** video oynatıcı kontrolleri canlı oturuma bağlıdır; uçtan uca ses senkronizasyonu hâlâ platforma özel kabul testlerine ihtiyaç duyuyor.
- **Mevcut sınırlar:** ses zamanlamasının kalibrasyonu ve Windows üzerindeki kabul testi hâlâ açık. Hâlâ süren canlı yayınlar desteklenmiyor; canlı mod etiketi, devam eden bir yayının sürekli alınması anlamına gelmez.

Kaydedilmiş dublajlı bir video için gerçek zamanlı önizleme yerine **İndir ve Çevir** / **Çeviriyi Başlat** seçeneğini kullanın.

### Çeviri motor blokları ve VPN

Farklı düzeltmelerle iki farklı blok meydana gelebilir:

| Blok | Belirti | Düzeltme |
|-------|---------|-----|
| **İndir** (yt-dlp) | "Bot olmadığınızı doğrulamak için oturum açın", HTTP 429 | **VPN** / IP döndürün veya tarayıcınızdan YouTube'da oturum açın (çerezler otomatik olarak okunur) |
| **Çeviri** (Google ücretsiz uç noktası) | "Google Translate çevrilemedi... istek hızı sınırlı/engellendi" | **MarianMT** (çevrimdışı) veya **Ollama** (yerel) kullanın; istek hızı sınırı yoktur. Bir VPN de yardımcı olur. Toplu akış artık Google engellendiğinde **otomatik olarak MarianMT'ye geri dönüyor**. |

### Temalar ve görünüm

**Ayarlar**'ı açmak için başlıktaki dişli simgesini tıklayın:

- **Tema**: Otomatik (işletim sistemi karanlık/açık modunu takip eder), Graphite (varsayılan), Slate, Light, Neon.
- **Görünümler**: Dex ve Handheld (cep konsolu, piksel yazı tipi, kalın çerçeveler), CRT ve CRT Amber (80'lerin fosforlu monitörü; video da bir mpv gölgelendiricisiyle kavis ve tarama çizgileri kazanır). Varsayılan yine Graphite'tir.
- **Vurgu rengi**: temaya göre varsayılan veya mavi, deniz mavisi, mor, yeşil, kehribar, gül.
- **Metin boyutu**: küçük, normal, büyük, ekstra büyük.
- **Arayüz dili**: 26 dil.

Değişiklikler, yeniden başlatmaya gerek kalmadan anında uygulanır ve yapılandırma dosyasına (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`) kaydedilir. **Varsayılanları geri yükle**, Graphite temasını, varsayılan vurguyu, normal metin boyutunu ve ayarlar panellerinin varsayılan sırasını geri getirir.

### Komut satırı

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Tüm seçenekler:**

| CLI seçeneği | Açıklama | Varsayılan |
|------|-------------|---------|
| `--lang-source` | Kaynak dili (otomatik algılama için `auto`) | `auto` |
| `--lang-target` | Hedef dil kodu (ör. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS ses adı | auto |
| `--model` | Whisper modeli (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS hız ayarı (örn. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` veya `deepl` | `google` |
| `--deepl-key` | DeepL Free API anahtarı | - |
| `--diarize` | Konuşan kişilerin tanımlanmasını etkinleştirin (günlükleştirme) (pyannote) | - |
| `--hf-token` | Günlük tutma için HuggingFace jetonu | - |
| `--lipsync` | Ses dublajından sonra Wav2Lip dudak senkronizasyonunu uygulayın | - |
| `--subs-only` | Yalnızca `.srt` oluşturun, sesli dublajı atlayın | - |
| `--no-subs` | `.srt` oluşturmayı atla | - |
| `--no-demucs` | Ses/müzik ayrımını atla | - |
| `--output` / `-o` | Çıkış dosyası yolu | auto |
| `--output-dir` | Çevrilen dosyalar için klasör (tek yer, Windows ve Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Birden fazla dosyayı işle | - |
| `--voicebox` | Sesi çalışan bir Voicebox sunucusuyla klonlar | - |
| `--voicebox-url` | Voicebox adresi | `http://127.0.0.1:17493` |
| `--voicebox-engine` | Voicebox motoru (`chatterbox`, `qwen`, ...) | `chatterbox` |

### gerçek modellerle entegrasyon testleri

Varsayılan test paketi, gerçek model indirmelerini ve uzun GPU çalışmasını önler. Kurulu yerel yığına yönelik isteğe bağlı ampirik kontrolleri çalıştırmak için:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Bu kontroller gerçek Wav2Lip içe aktarmalarını, Torch CUDA kullanılabilirliğini, Ollama arka plan programının kullanılabilirliğini ve sentetik konuşmada faster-Whisper'yi doğrular. Yerel sürücü/arka plan programı/model durumu hazır olmadığında kasıtlı olarak başarısız olurlar veya atlarlar.

**Örnekler:**

```bash
# Yerel MarianMT ile İtalyanca videoyu İngilizceye çevirin
# (ilk kullanımda ~298 MB modeli indirir, ardından tamamen çevrimdışı olur)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Ses klonlama + konuşan kişilerin tanımlanması (günlükleştirme) ile çeviri
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Dudak senkronizasyonu ile çevirin
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Yalnızca altyazılar (sesli dublaj yok)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper modelleri

| Modeli | Boyut | Hız | doğruluk |
|-------|------|-------|----------|
| tiny | 75MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465MB | ⚡⚡ | ★★★☆ |
| medium | 1,5GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo`, `large-v3`'nin damıtılmış bir versiyonudur (4 kod çözücü katmanına karşı 32) - kabaca `medium` kademe hızında neredeyse büyük kalite. Transkripsiyon hızı önemli olduğunda modern bir GPU'da önerilen varsayılan; çok dilli materyaldeki kalite düşüşü küçüktür.

> Modeller ilk kullanımda otomatik olarak indirilir.

> Bilgisayarınıza hangi modelin uyduğunu bilmiyor musunuz? Model ayarlarında **Bu bilgisayar için modeller** penceresini açın: donanımınıza göre bir model önerir ve onu ölçebilir.

## Bağımsız modül CLI'leri

Modüler paket, tüm işlem hattını başlatmadan doğrudan çağrılabilen, kullanıcıya yönelik dört aracı kullanıma sunar:

```bash
# Yüzün varlığı için bir videonun ön uçuşunu gerçekleştirin (eğer yoksa Wav2Lip atlayacaktır).
python3 -m videotranslator.face_detector path/to/video.mp4
# çıkış 0 = yüz mevcut, çıkış 1 = yüz yok

# build_dubbed_track tarafından oluşturulan *_metrics.csv dosyasını analiz edin.
# pre_stretch_ratio'nin P50/P75/P90/P95 raporları, işitilebilirlik bandı dökümü,
# motor kullanımını genişletme ve hedef metinleriyle birlikte en kötü aykırı değerlerin ilk N'i.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Metni TTS için sterilize edin (iki nokta üst üste, noktalı virgül, üç nokta ve kısa çizgileri yeniden yazar).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# TTS'yi çalıştırmadan ÖNCE bir .srt veya .json segment dosyasından ses dublajının zorluğunu tahmin edin.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Her araçta tam seçenekler için `-h`/`--help` bulunur. Bağımsızdırlar ve ses dublaj hattının dayandığı aynı modülleri yeniden kullanırlar, böylece çıktıları çalışma zamanı ile tutarlı kalır.

## Lisans

MIT

### Üçüncü taraf bileşenler

Depo kodu MIT'dir. Kurulumcular aşağıdaki bileşenleri kurulum sırasında kendi kaynaklarından indirirler; proje bunları yeniden dağıtmaz.

- **libmpv** (https://github.com/mpv-player/mpv), entegre video oynatıcının motoru. Windows: İlk önce zhongfly (https://github.com/zhongfly/mpv-winbuild) tarafından oluşturulan LGPL denenir; geri dönüş, shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) tarafından yapılan sabitlenmiş bir GPL yapısıdır. `mpv-runtime\BUILD.txt` kaynağı, lisans türünü ve mpv taahhüdünü kaydeder ve lisans metni DLL'nin yanında yer alır. Linux: dağıtım paketi (`libmpv2`, `libmpv1`, `mpv-libs` veya `mpv`).
- **FFmpeg** libmpv içinde (LGPL veya GPL, libmpv yapısını takip ederek).
- **python-mpv** (PyPI'de `mpv`), GPLv2+ veya LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), Windows yükleyicisi tarafından libmpv'yi ayıklamak için kullanılır ve daha sonra silinir.
- **Vulkan yükleyici** (Khronos, MIT ve Apache-2.0), yalnızca `vulkan-1.dll` eksik olduğunda Windows'a indirilir.
- **edge-tts** (LGPLv3), ses dublaj hattı tarafından kullanılır.
- **MarianMT modelleri** (Helsinki-NLP), ilk kullanımda kendi lisansları altında Hugging Face Hub'dan indirilmiştir (`opus-mt` modelleri için Apache-2.0, `opus-mt-tc-big` için CC-BY-4.0).
- **Voicebox** (MIT, https://github.com/jamiepine/voicebox), isteğe bağlı, kullanıcı tarafından ayrıca kurulur; motorlarının kendi lisansları vardır (ses filigranlı Chatterbox MIT, Llama 3.2 Community License kapsamındaki TADA ağırlıkları).
- **ElevenLabs** (https://elevenlabs.io), kullanıcının kendi hesabı ve API anahtarıyla, hizmetin kendi koşullarına göre kullanılan isteğe bağlı çevrimiçi hizmet.
- Görünümlerin kullandığı **Pixelify Sans** ve **VT323** yazı tipleri (SIL Open Font License 1.1): depoda bulunan tek üçüncü taraf dosyalar, lisans metinleriyle birlikte `assets/fonts` içinde.
