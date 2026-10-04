# 🎬 Video Translator AI

[Bahasa Inggris](../../README.md) | [Semua terjemahan](README.md)

**Baca halaman ini di:** [Bahasa Indonesia](README.id.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Nederlands](README.nl.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Suomi](README.fi.md) · [Svenska](README.sv.md) · [Tiếng Việt](README.vi.md) · [Türkçe](README.tr.md) · [Ελληνικά](README.el.md) · [Русский](README.ru.md) · [Українська](README.uk.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Alat sulih suara video bertenaga AI yang secara otomatis mentranskripsikan, menerjemahkan, dan menjuluki ulang video ke dalam 26 bahasa, dengan opsi pemrosesan lokal dan tidak memerlukan kunci API secara default. Pengenalan ucapan Whisper berjalan secara lokal; Edge-TTS, Google Translate dan DeepL memerlukan koneksi internet. Fitur opsional (DeepL, identifikasi orang yang berbicara (diarisasi)) mungkin memerlukan kunci API atau token akses.

![Jendela utama Video Translator AI: pemutar video dan panel terjemahan](../../assets/screenshot.png)

> **v2.0** - paket modular, terjemahan Ollama lokal, orkestrasi profil kualitas, metadata Python yang dapat diinstal, dan pengujian integrasi keikutsertaan dengan model nyata. Lihat [Rilis GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases) dan riwayat penerapan untuk daftar lengkap perubahan.

> **v2.1.0** - installer Windows diperkuat (runtime Microsoft Visual C++, log pemasangan yang jelas, pembaruan otomatis dari GitHub Releases), log yang lebih rapi (satu progress bar yang berjalan per unduhan), decoding video perangkat lunak pada mesin tanpa GPU, dan tombol transport yang ditinggikan. Lihat [Rilis GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases).

## Bagaimana cara kerjanya

1. **Transkripsi** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) mentranskripsikan audio (diakselerasi GPU)
2. **Pemisahan suara/musik** - [Demucs](https://github.com/facebookresearch/demucs) mengisolasi vokal dari musik latar
3. **Terjemahan** - MarianMT (lokal, offline), Google Translate, DeepL Free, atau **Ollama LLM** (Qwen3, terjemahan ringkas yang sadar slot)
4. **identifikasi orang yang berbicara (diarisasi)** *(opsional)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) mengidentifikasi siapa yang berbicara di setiap segmen
5. **dubbing suara** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ suara) atau [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (kloning suara, untuk setiap pembicara dalam percakapan)
6. **Mixing** - suara yang di-dubbing dicampur kembali dengan musik latar asli
7. **Normalisasi** - audio akhir dinormalisasi ke -23 LUFS (standar siaran EBU R128)
8. **Lip Sync** *(opsional)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) menyinkronkan gerakan mulut ke audio yang di-dubbing

## Fitur

- 🖥️ GUI Bertema (Tkinter) - tidak memerlukan baris perintah; Graphite, Slate, Light dan Neon tema, warna aksen, ukuran teks, dan panel pengaturan dapat Anda susun ulang dengan menyeret
- 🕹️ **Skin** - tampilan ceria dari pengaturan: Dex dan Handheld mengingatkan pada konsol genggam (font piksel, bingkai tebal), CRT dan CRT Amber pada monitor fosfor tahun 80-an, dengan lengkungan dan garis pindai juga di video
- 🔊 **Dengarkan sebelum memilih** - ikon pengeras suara di samping suara memutar kalimat contoh dalam bahasa tujuan (Edge-TTS) atau sampel gratis suara ElevenLabs
- 🌍 **26 bahasa target** dengan banyak suara per bahasa
- 🌐 **UI dalam 26 bahasa** - antarmukanya sendiri menyesuaikan dengan bahasa Anda
- 🎬 **Dukungan YouTube & URL** - tempel tautan YouTube apa pun dan terjemahkan secara langsung (didukung oleh yt-dlp)
- ▶️ **Pemutar video terintegrasi** (libmpv/mpv) - kontrol transportasi berkode warna, daftar putar, audio asli A/B vs audio yang di-dubbing, pengalihan subtitle, snapshot, layar penuh, folder terbuka
- ⏱️ **Terjemahan waktu nyata** - tonton file lokal atau tautan video sesuai permintaan dengan subtitle terjemahan dan penggeser jeda; mesin MarianMT / Google / DeepL / Ollama. Sulih suara memakai Edge-TTS atau, secara opsional, suara ElevenLabs lewat instans mpv kedua; kalimat yang bertumpuk akan menunggu, dipercepat, atau memudar. Siaran langsung yang sedang berjalan belum didukung.
- 🎵 Pemisahan suara/musik melalui Demucs (menyimpan musik latar)
- 🔇 **Mute audio asli**, tersedia sebelum dan selama terjemahan langsung, mengheningkan soundtrack video sekaligus menjaga suara terjemahan tetap terdengar. Matikan untuk mengembalikan audio asli; itu diatur ulang ketika sesi langsung berakhir.
- 🧠 **MarianMT** - terjemahan neural offline yang sepenuhnya lokal (Helsinki-NLP, tanpa batas kecepatan permintaan, tanpa kunci API)
- 🤖 **Terjemahan Ollama LLM** *(baru di v2.0)* - LLM lokal (Qwen3, Llama, Mistral) yang memproduksi terjemahan ringkas sesuai slot untuk dubbing suara alami, model deteksi/pemasangan/mulai/tarik otomatis pada penggunaan pertama
- 🎙️ **Kloning suara** - Coqui XTTS v2 mengkloning orang yang berbicara dalam suara audio asli dalam bahasa target (~model 1,8 GB), dengan kecepatan adaptif per segmen dan percobaan ulang multi-seed pada halusinasi
- 👥 **identifikasi orang yang berbicara (diarisasi)** - pyannote-audio 3.1 mengidentifikasi banyak orang yang berbicara; XTTS mengkloning setiap suara secara terpisah
- 💋 **Lip Sync** - Wav2Lip GAN menyinkronkan gerakan mulut ke audio yang di-dubbing (~model 416 MB)
- 🔊 **Normalisasi audio** - normalisasi kenyaringan -23 LUFS otomatis (EBU R128)
- ✏️ Editor subtitle - tinjau dan perbaiki subtitle sebelum dubbing suara
- 📦 Pemrosesan batch - terjemahkan beberapa video atau URL sekaligus
- ⚡ Akselerasi GPU melalui CUDA (kembali ke CPU secara otomatis)
- 📄 Ekspor subtitle `.srt` opsional
- 🔁 **DeepL Free** mesin terjemahan (opsional - 500 ribu karakter/bulan, memerlukan kunci API gratis)
- 🔧 **Instal otomatis** - paket Python dan ffmpeg yang hilang diinstal secara otomatis pada peluncuran pertama
- 🧮 **Model untuk PC ini** - mendeteksi CPU, RAM, GPU, VRAM, dan ruang disk kosong, menyarankan model pengenalan suara, terjemahan, dan suara untuk kecepatan, keseimbangan, atau kualitas, mengunduh dan memeriksa model Whisper, lalu mengukurnya dengan video Anda sendiri
- 🗣️ **Suara ElevenLabs** *(opsional, daring, berbayar)* - suara multibahasa yang alami untuk sulih suara langsung dengan kunci API Anda sendiri; jika kunci atau kuota gagal, Edge-TTS mengambil alih
- 🧬 **Kloning suara dengan Voicebox** *(opsional)* - mengkloning suara pembicara lewat server lokal [Voicebox](https://github.com/jamiepine/voicebox) yang terpisah; jika tidak berjalan, video memakai Edge-TTS

## Bahasa yang didukung

Arab, Tionghoa, Ceko, Denmark, Belanda, Inggris, Finlandia, Prancis, Jerman, Yunani, Hindi, Hongaria, Indonesia, Italia, Jepang, Korea, Norwegia, Polandia, Portugis, Rumania, Rusia, Spanyol, Swedia, Turki, Ukraina, Vietnam

## Katalog Suara

Katalog suara Edge-TTS ditentukan dalam `LANGUAGES` di dekat bagian atas `video_translator_gui.py`. Kamus tersebut adalah sumber kebenaran untuk nama bahasa target, tombol radio suara GUI, dan suara cadangan CLI ketika `--voice` dihilangkan.

Catatan Claude/pemeliharaan proyek mencerminkan lokasi ini di `CLAUDE.md` di bawah **Voice Catalog Source Of Truth**, sehingga agen kode di masa mendatang mengetahui di mana harus memperbarui suara dan di mana README mengarahkan pengguna.

## Mesin terjemahan

| Mesin | Pengaturan | Batasan | Kualitas |
|--------|-------|--------|---------|
| **Google Translate** *(standar)* | Tidak ada | Pengikisan tidak resmi - mungkin dibatasi pada video berukuran besar | ★★★★ |
| **MarianMT** | Tidak ada - mengunduh ~298 MB per pasangan bahasa pada penggunaan pertama | Tidak ada - sepenuhnya offline setelah diunduh | ★★★★ |
| **DeepL Free** | Kunci API gratis di [deepl.com](https://www.deepl.com/pro-api) | 500 ribu karakter/bulan | ★★★★★ |
| **Ollama LLM** *(direkomendasikan untuk sulih suara - baru di v2.0)* | Diinstal otomatis pada penggunaan pertama (~1 GB Ollama + model 5 GB) | Tidak ada - sepenuhnya lokal | ★★★★★ |

> **MarianMT** menggunakan model [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP), yang di-cache secara lokal setelah pengunduhan pertama. Memerlukan bahasa sumber yang eksplisit (deteksi otomatis tidak didukung - pilih bahasa sumber secara manual). Paket Python yang diperlukan (`sacremoses`, `sentencepiece`) diinstal secara otomatis pada pilihan pertama jika tidak ada.

> **Ollama LLM** *(baru di v2.0)* adalah mesin yang direkomendasikan untuk sulih suara suara karena menghasilkan terjemahan yang sesuai dengan slot waktu target. Jika MarianMT diterjemahkan secara harfiah dan menghasilkan bahasa Italia / Spanyol / Prancis ~25% lebih lama daripada bahasa Inggris (memaksa kompresi audio terdengar di TTS), LLM diminta untuk menjaga setiap segmen tetap ringkas dan alami untuk penyampaian lisan, mencapai rasio karakter tipikal 0,85-0,95 vs sumber. Model defaultnya adalah `qwen3:8b` (disk 5,2 GB, VRAM ~6 GB); `qwen3:4b` (~3 GB) adalah opsi yang ringan, `qwen3:14b` adalah opsi berkualitas lebih tinggi. Pipeline secara otomatis mendeteksi biner Ollama, menginstalnya secara otomatis melalui penginstal resmi pada penggunaan pertama (dengan popup persetujuan), memulai daemon dan menarik model yang dipilih - tidak diperlukan pengaturan manual. Secara otomatis beralih ke Google Translate jika ada yang hilang.

## Kloning Suara (XTTS v2)

Saat diaktifkan, aplikasi mengekstrak suara pembicara dari video asli dan menggunakannya sebagai referensi untuk mengkloning suara tersebut dalam bahasa target.

- Bahasa yang didukung: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Untuk 9 bahasa lainnya, Edge-TTS digunakan secara otomatis sebagai cadangan
- Model (~1,8 GB) diunduh secara otomatis saat pertama kali digunakan ke `~/.local/share/tts/`
- **Referensi dengan filter VAD** (v1.4): 10-15 detik ucapan terus menerus yang dipilih dari audio asli melalui [silero-vad](https://github.com/snakers4/silero-vad) untuk kualitas kloning suara yang lebih baik
- **Kecepatan pembuatan** dapat dikonfigurasi (`xtts_speed`, default `1.25`): nilai yang lebih tinggi mengurangi artefak kompresi audio pascapemrosesan ketika teks yang diterjemahkan lebih panjang dari slot sumber. Dengarkan melalui `~/.config/videotranslatorai/config.json` atau CLI `--xtts-speed`
- Berjalan pada CUDA atau CPU

## identifikasi orang yang berbicara (diarisasi) (pyannote-audio)

Jika diaktifkan, aplikasi mengidentifikasi siapa yang berbicara di setiap segmen. Dikombinasikan dengan Kloning Suara, setiap suara pembicara diklon secara terpisah - ideal untuk wawancara, podcast, dan video multi-orang.

- Membutuhkan [token HuggingFace](https://huggingface.co/settings/tokens) gratis (pendaftaran satu kali)
- **Token disimpan dengan aman** (v1.4) melalui keyring OS: Windows Credential Manager, macOS Keychain, Linux Secret Service. Migrasi otomatis dari penyimpanan JSON teks biasa sebelumnya
- Setelah pengunduhan pertama, berfungsi sepenuhnya offline
- Model: `pyannote/speaker-diarization-3.1`

## Sinkronisasi Bibir (Wav2Lip)

Saat diaktifkan, aplikasi menerapkan Wav2Lip GAN untuk menyinkronkan gerakan mulut subjek dengan audio yang di-dubbing - orang tersebut tampaknya berbicara dalam bahasa terjemahan.

- Model (~416 MB) dan repo diklon secara otomatis saat pertama kali digunakan ke `~/.local/share/wav2lip/`
- Berjalan pada CUDA (disarankan) atau CPU
- Meningkatkan waktu pemrosesan secara signifikan
- Berfungsi paling baik pada video dengan satu wajah yang terlihat jelas

## Model untuk PC ini

Pengaturan lanjutan > Model > **Model untuk PC ini** membuka jendela yang membaca perangkat keras (CPU, RAM, GPU dan VRAM yang bisa dipakai, ruang disk kosong) tanpa mengubah apa pun dan menyarankan satu model untuk setiap tahap: pengenalan suara untuk file dan siaran langsung, terjemahan, dan suara.

- Pilih **Kecepatan**, **Seimbang**, atau **Kualitas**: setiap saran menyebutkan alasannya.
- Semua opsi lain tetap bisa dipilih dan dinilai untuk PC ini: muat, pas-pasan, terlalu besar, disk tidak cukup, atau layanan daring.
- **Unduh** mengambil model Whisper yang belum ada, dengan kemajuan dan Batal, lalu memeriksa setiap file dengan checksum Hugging Face; tidak ada yang diunduh sebelum Anda menekannya.
- **Benchmark** mengukur model pilihan pada video yang dimuat (pemuatan, kalimat pertama, kecepatan); audio tidak pernah keluar dari PC.
- **Terapkan** menetapkan model; **Pulihkan sebelumnya** mengembalikan pilihan sebelumnya. GPU NVIDIA dipakai melalui CUDA; GPU AMD (ROCm) dan Apple ditampilkan, tetapi di sana model suara berjalan di CPU.

## Voicebox (kloning suara lewat server lokal)

[Voicebox](https://github.com/jamiepine/voicebox) (MIT) adalah program terpisah yang mengkloning suara. Pasang dan jalankan sendiri; aplikasi ini hanya memanggil API lokalnya dan tidak pernah memasangnya.

- Pengaturan lanjutan > Kloning Suara > **Voicebox**: atur alamat (bawaan `http://127.0.0.1:17493`), mesin (bawaan `chatterbox`), lalu tekan **Periksa**.
- Untuk setiap video, suara sementara dikloning dari sampel bersih pembicara (satu per pembicara dengan pemisahan pembicara) lalu dihapus.
- Hanya alamat di PC ini yang diterima, karena API Voicebox tidak memakai autentikasi.
- Jika Voicebox tidak merespons atau tidak mendukung bahasa tujuan, video disulihsuarakan dengan Edge-TTS.

## Ekstraksi audio

Ekstrak audio dari file lokal atau URL alih-alih menerjemahkannya. Pilih format (MP3, M4A, Opus, OGG, FLAC atau WAV) dan, untuk format lossy, bitrate. Mode hanya instrumental menghapus suara dengan Demucs dan hanya menyisakan musik.

Dari baris perintah:

```bash
python video_translator_gui.py video.mp4 --extract-audio --audio-format mp3 --audio-bitrate 320
python video_translator_gui.py video.mp4 --extract-audio --instrumental --audio-format flac
```

Di antarmuka grafis, kontrol ekstraksi audio ada di kartu Masukan: pilih format dan bitrate, aktifkan opsi hanya instrumental untuk menyimpan musik saja, lalu tekan Ekstrak.

## Persyaratan

- Python 3.10+ (penginstal Windows menyediakan 3.11.9 secara otomatis)
- Windows 10/11 (x64), Linux, atau macOS
- **NVIDIA GPU sangat disarankan** - lihat tabel GPU di bawah
- Ruang disk kosong 20 GB untuk instalasi penuh (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg dan semua paket Python diinstal secara otomatis** pada peluncuran pertama jika tidak ada. Tidak diperlukan pengaturan manual.

**Ketergantungan sistem opsional** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Saat dipasang, ini digunakan untuk mempertahankan peregangan waktu dalam pita kualitas yang dikontrol profil (default 1,15-1,50, hingga 1,65 untuk konten keras), menghilangkan sisa efek "chipmunk" pada suara XTTS yang dikloning. Pipeline berjalan tidak berubah tanpanya (fallback otomatis ke ffmpeg `atempo`). Profil berkualitas kini lebih memilih percobaan ulang terjemahan ekstra pendek dibandingkan peningkatan kecepatan audio yang ekstrem.

### dukungan GPU

Pipeline ini menggunakan lima komponen yang dipercepat GPU (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). Cakupan GPU tidak seragam antar vendor:

| GPU | Windows | Linux | Catatan |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx atau lebih baru, driver CUDA 12.4) | ✅ akselerasi penuh | ✅ akselerasi penuh | **Direkomendasikan.** Kelima komponen tersebut dijalankan pada GPU. |
| **AMD** (Radeon) | ⚠️ tidak lengkap (DirectML tidak mendukung XTTS dan faster-whisper) | ⚠️ sebagian (ROCm berfungsi untuk Demucs/XTTS/pyannote tetapi faster-whisper hanya mendukung CUDA) | Berfungsi tetapi transkripsi Whisper tetap berada di CPU dan mendominasi total waktu. |
| **Intel Arc** | ⚠️ dukungan PyTorch XPU yang belum matang | ⚠️ sama | Tidak diuji. |
| **Tidak ada (hanya CPU)** | ✅ berfungsi | ✅ berfungsi | Harapkan **10-20× lebih lambat** dibandingkan waktu nyata. Klip berdurasi 5 menit mungkin memerlukan waktu 50+ menit hanya untuk ditranskripsikan dengan Whisper large-v3. |

**VRAM NVIDIA yang Direkomendasikan:**

| VRAM | Contoh kartu grafis | Pengalaman |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Dapat digunakan, tidak dapat menjalankan XTTS + Wav2Lip secara bersamaan |
| 8 GB | RTX 3060 Ti, 4060 | Pipa penuh, tanpa margin |
| **12GB+** | **RTX 3060 12GB, 4070, 4080** | **Direkomendasikan - nyaman** |
| 24 GB | RTX 3090, 4090 | Kapasitas cadangan untuk batch besar |

## Instalasi

### Windows

Langkah demi langkah, tanpa perlu baris perintah. Diuji pada PC Windows 11 yang bersih.

1. **Unduh** proyeknya: tombol hijau **Code** → **Download ZIP**, atau zip terbaru dari [Rilis GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases). Ekstrak ke folder mana pun, misalnya Desktop.
2. **Instal**: klik kanan `setup_windows.bat` → **Run as administrator** → tekan `1` (Install). Jika SmartScreen menampilkan "Windows protected your PC", klik **More info** → **Run anyway**: skripnya berupa teks biasa, bisa dibuka dengan Notepad.
3. **Tunggu**: pada PC baru dengan koneksi cepat, prosesnya memakan waktu sekitar 15 menit dan 8 GB ruang disk. Penginstal mengunduh dan menyiapkan, dalam urutan ini:
   - Python 3.11 (seluruh sistem) dan runtime Microsoft Visual C++, jika belum ada
   - paket Python: PyTorch (CUDA 12.4 dengan GPU NVIDIA, selain itu versi CPU), faster-whisper, Demucs, coqui-tts, pyannote dan tumpukan Wav2Lip
   - Git for Windows (untuk Wav2Lip), ffmpeg dan pemutar video terintegrasi (libmpv di `mpv-runtime`; opsional, semuanya tetap berfungsi tanpanya)
   - **pintasan Desktop** untuk setiap akun Windows di PC dan folder **Start Menu** berisi aplikasi serta **Perbarui Video Translator AI**
4. **Jalankan** dari pintasan Desktop atau Start Menu. Tanpa GPU NVIDIA aplikasi tetap berjalan di CPU, hanya lebih lambat: pilih model Whisper yang kecil.

> Semuanya terinstal di seluruh sistem di bawah `%ProgramFiles%\VideoTranslatorAI`, sehingga setiap pengguna Windows di mesin menemukan pintasan yang siap dipakai. Setiap kali `setup_windows.bat` dijalankan, sebuah log ditulis ke `%USERPROFILE%\VideoTranslatorAI-setup.log`: lampirkan file ini saat melaporkan masalah. Jika penginstal berakhir dengan **INSTALLATION INCOMPLETE**, jalankan lagi dan pilih `[2] Repair / Update`. VS C++ Build Tools tidak diperlukan: fork `coqui-tts` yang dikelola menyediakan paket wheel yang sudah dikompilasi.

### Linux/macOS

```bash
# Diperlukan Python 3.11 sampai 3.13 (PyTorch belum punya paket untuk 3.14): pada distribusi yang python3-nya 3.14, gunakan python3.13 pada perintah di bawah
# Kloning reponya
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Opsional: instal tumpukan NVIDIA CUDA 12.4 PyTorch yang diuji di depan
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Opsional: pra-instal semua paket runtime Python alih-alih membiarkan GUI
# instal paket yang hilang saat pertama kali dijalankan
pip install --break-system-packages -r requirements.txt

# Opsional: pemutar video terintegrasi (libmpv dari distribusi, python-mpv dari PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Lengkungan: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Opsional: instal proyek sebagai paket Python yang dapat diedit
pip install --break-system-packages --no-deps -e .

# Luncurkan dari sumber
python video_translator_gui.py

# Atau, setelah diedit/instalasi paket
videotranslatorai
videotranslatorai --preflight
```

> Pada peluncuran pertama GUI mendeteksi paket yang hilang (faster-whisper, Demucs, Edge-TTS, dll.) dan menginstalnya secara otomatis, mengalirkan output ke jendela log. ffmpeg juga diinstal secara otomatis melalui `apt-get` / `dnf` / `pacman` (Linux) atau diunduh dari GitHub (Windows). Jika dijalankan dengan Python yang tidak didukung PyTorch, aplikasi memulai ulang sendiri dengan Python yang didukung yang ditemukan di PC.

> Header menunjukkan lencana **Pemain**. Ketika libmpv atau python-mpv tidak ada, panel kiri menunjukkan apa yang hilang dan menawarkan **Instal pemutar**: di Linux ia menggunakan manajer paket melalui pkexec (kemudian `sudo -n`) dan menampilkan perintah manual ketika tidak ada yang berfungsi; di Windows ia menanyakan sebelum mengunduh libmpv untuk pengguna saat ini (sekitar 32 MB).

### Profil kebutuhan

| Mengajukan | Tujuan |
|------|---------|
| `requirements.txt` | Penginstalan runtime penuh yang kompatibel dengan versi sebelumnya. |
| `requirements-core.txt` | Paket pipa default yang digunakan oleh GUI/CLI. |
| `requirements-optional.txt` | XTTS, tokenizer MarianMT, diarisasi, VAD, gantungan kunci. |
| `requirements-wav2lip.txt` | Runtime Wav2Lip dan tumpukan deteksi wajah (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Tumpukan PyTorch diuji dengan roda NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Pemutar video terintegrasi: python-mpv (membutuhkan libmpv dari sistem atau dari penginstal Windows). |
| `requirements-dev.txt` | Ketergantungan ringan yang digunakan oleh CI/pengujian unit. |

## Pembaruan

### Windows

Start Menu → **Video Translator AI** → **Perbarui Video Translator AI** (akan meminta hak administrator), atau jalankan `setup_windows.bat` sebagai administrator dan pilih `[2] Repair / Update`. Penginstal memeriksa [Rilis GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases): jika ada versi yang lebih baru, ia mengunduh rilis tersebut, memverifikasi checksum SHA256-nya, lalu menginstalnya; jika tidak, ia memperbaiki file yang ada. Pengaturan, kunci tersimpan, model yang diunduh, dan video yang sudah diterjemahkan tetap dipertahankan. Tanpa koneksi internet, pembaruan dilewati dan perbaikan tetap berlanjut.

### Linux/macOS

```bash
cd VideoTranslatorAI
git pull
pip install --break-system-packages -r requirements.txt
```

## Copot pemasangan

### Windows

Jalankan `setup_windows.bat` (klik kanan → **Run as administrator**) dan pilih `[3] Uninstall` dari menu. Tiga sub-mode uninstall ditawarkan:

| Modus | Dibutuhkan Admin | Ruang lingkup |
|------|----------------|-------|
| **[1] Pencopotan pemasangan penuh - satu klik** | ✅ | Menghapus folder aplikasi, pintasan Desktop dan entri Start Menu, ffmpeg dari PATH mesin, cache model HF setiap pengguna (Whisper/XTTS) dan konfigurasi (`HF token`), dan semua paket Python AI yang diinstal oleh penginstal. Pada akhirnya ia juga menanyakan (ikut serta) apakah akan menghapus secara diam-diam **Python 3.11** dan **Git for Windows** melalui string pencopotan diam-diam registri mereka. Menghapus Python 3.11 juga menghapus paket yang dipasang pip untuknya di folder pengguna saat ini (`%APPDATA%\Python\Python311`), kecuali masih ada Python 3.11 lain yang terpasang. |
| **[2] Khusus pengguna saat ini** | ❌ | Hanya menghapus konfigurasi VTAI pengguna yang sedang berjalan, cache HF/XTTS, dan instalasi lama per pengguna. **Membiarkan penginstalan seluruh sistem tetap utuh** sehingga akun Windows lain di PC dapat tetap menggunakan aplikasi. |
| **[3] Khusus - terperinci** | ✅ untuk item sistem, ❌ untuk item pengguna | Y/N prompt untuk setiap kategori: folder aplikasi, pintasan, PATH mesin, instalasi lama per pengguna, konfigurasi/cache per pengguna, lalu mengelompokkan paket Python (TTS, tumpukan PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, utilitas pipa), dan terakhir opsional Python 3.11 dan Git. |

Setiap mode juga menghapus apa yang disimpan program untuk pengguna: konfigurasi dan log harian (`%APPDATA%\VideoTranslatorAI`), data program beserta runtime pemutar, JavaScript, dan Wav2Lip (`%LOCALAPPDATA%\VideoTranslatorAI`), berkas sementara waktu nyata (`%TEMP%\VideoTranslatorAI`), model MarianMT, serta kunci tersimpan (token HF, ElevenLabs) dari Credential Manager Windows. Kunci disimpan per akun Windows: setiap akun menghapus kuncinya sendiri dengan `[2]`.

**Tidak pernah dihapus secara otomatis:** Visual Studio C++ Build Tools (jika ada dari proses yang lebih lama) dan runtime Microsoft Visual C++, yang digunakan bersama oleh program lain. Gunakan *Aplikasi dan fitur* di Pengaturan Windows untuk menghapusnya secara manual jika diinginkan. Log pemasangan `%USERPROFILE%\VideoTranslatorAI-setup.log` sengaja dipertahankan.

### Linux/macOS

Tidak ada uninstaller khusus - hapus secara manual:

```bash
# Paket Python diinstal oleh penginstal otomatis GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Data pengguna dan cache model
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip ~/.cache/wav2lip
rm -rf ~/.config/videotranslatorai          # config (tema, urutan panel, pengaturan)
rm -rf ~/.local/share/fonts/VideoTranslatorAI   # font untuk skin
rm -rf ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt*   # model terjemahan MarianMT
rm -rf ~/.local/share/VideoTranslatorAI                          # data program (runtime JavaScript untuk yt-dlp)
rm -rf "${TMPDIR:-/tmp}/VideoTranslatorAI"                       # berkas sementara waktu nyata
# kunci tersimpan (token HF, ElevenLabs)
python3 -c "import keyring; [keyring.delete_password('VideoTranslatorAI', u) for u in ('hf_token', 'elevenlabs_api_key') if keyring.get_password('VideoTranslatorAI', u)]"
rm -f  ~/.videotranslatorai_config.json     # konfigurasi lama versi <= 1.9, jika ada
```

## Penggunaan

### Diagnostik

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Menjalankan diagnostik lingkungan lokal tanpa memulai terjemahan atau menginstal apa pun. `--preflight-lipsync` memperlakukan paket wajah Wav2Lip sesuai kebutuhan, yang berguna sebelum mengaktifkan **Lip Sync**. GUI memperlihatkan pemeriksaan dasar yang sama dari tombol **Diagnostik** pada panel log. `--preflight-player` memperlakukan pemutar video terintegrasi (python-mpv dan libmpv yang dapat dimuat) sesuai kebutuhan. `python -m videotranslator.libmpv_runtime check` menyelidiki libmpv saja (keluar 0 siap, 2 tidak tersedia).

**Berkas log:** semua yang ditampilkan panel log (setiap klik dan pilihan, hasil, langkah pemrosesan, kesalahan beserta detailnya) juga disimpan di `logs/videotranslator.log` di samping konfigurasi: `~/.config/videotranslatorai/logs/` di Linux, `%APPDATA%\VideoTranslatorAI\logs\` di Windows. Satu berkas per hari, 7 hari terakhir disimpan; tombol **Diagnostik** menampilkan jalurnya. Lampirkan saat melaporkan masalah. Kunci API dan teks yang diketik di kolom tidak pernah ditulis. Setiap baris menampilkan waktu, tingkat (info, peringatan, galat, dalam bahasa antarmuka, dengan peringatan dan galat berwarna di panel) dan area, misalnya [ui] untuk klik, [job] untuk terjemahan, [live] untuk waktu nyata; setiap kali dimulai ditulis kepala dengan versi, sistem, GPU, dan pengaturan.

### GUI

```bash
python video_translator_gui.py
```

**Tata letak:** Pengaturan terjemahan batch ada di kolom sebelah kanan, sebagai tumpukan panel pengaturan: **Input**, **Terjemahan**, **Profil alur kerja**, **Mulai**, dan bagian lanjutan yang dapat diciutkan (model, mesin terjemahan, audio, kloning suara, sinkronisasi bibir, diarisasi, opsi, kata cepat). Area luas di sebelah kiri adalah **pemutar video terintegrasi** (transportasi, playlist, audio asli A/B vs audio yang di-dubbing, subtitel, cuplikan, layar penuh), dengan bilah **terjemahan real-time** di bawahnya. Seret kartu berdasarkan judulnya atau dengan pegangan **≡** untuk memindahkannya ke atas atau ke bawah kolom; pesanan disimpan (`ui_panel_order`) dan dipulihkan pada permulaan berikutnya. Panel log di bagian bawah dapat disembunyikan dengan **Sembunyikan log**. Saat memulai, jendela terbuka di tengah monitor saat ini (yang ada di bawah penunjuk) dan dimaksimalkan, sehingga berfungsi dengan baik pada pengaturan multi-monitor.

**Kontrol pemutar video video:** ikon menggunakan warna fungsional yang konsisten di setiap tema, terlepas dari warna aksen yang dipilih:

| Kontrol | Warna |
|---------|--------|
| Putar video | Hijau |
| Jeda (menggantikan Putar sambil bermain) | kuning |
| Hentikan pemutaran | Merah karang |
| Sebelumnya/mundur 10 detik/maju 10 detik/berikutnya | Biru |
| Cuplikan | ungu |
| Buka map | Emas |

Melayang menambahkan latar belakang berwarna halus. Kontrol yang tidak tersedia bersifat netral; navigasi daftar putar tetap dapat digunakan setelah Berhenti. Keterangan alat dan indikator fokus keyboard tetap tersedia, jadi warna bukanlah satu-satunya cara untuk mengidentifikasi tindakan.

**Dari file lokal:**
1. Klik **Tambahkan** untuk memilih satu atau lebih file video
2. Pilih bahasa sumber dan target
3. Buka bagian **Model** dan pilih model Whisper (`small` adalah keseimbangan yang baik antara kecepatan/akurasi)
4. Pilih suara dan sesuaikan kecepatan TTS jika diperlukan
5. *(Opsional)* Di **Mesin terjemahan** pilih **Google** (default), **MarianMT** (lokal/offline), **DeepL Free**, atau **Ollama LLM** (lokal, direkomendasikan untuk sulih suara suara)
6. *(Opsional)* Aktifkan **Kloning Suara** (XTTS v2) dan/atau **identifikasi orang yang berbicara (diarisasi)**
7. *(Opsional)* Aktifkan **Sinkronisasi Bibir** (Wav2Lip)
8. Klik **Mulai Terjemahan**

**Dari YouTube (atau situs apa pun yang didukung):**
1. Tempelkan satu atau beberapa URL di kolom **URL** (satu URL per baris)
2. Konfigurasikan bahasa, model dan suara seperti biasa
3. Klik **⬇ Unduh & Terjemahkan**

> yt-dlp mendukung YouTube, Vimeo, Twitter/X, TikTok, dan [1000+ situs lain](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Pemberitahuan penggunaan wajar:** Mengunduh video melalui yt-dlp dianggap sebagai akses otomatis oleh platform seperti YouTube dan mungkin melanggar Persyaratan Layanan mereka. Penggunaan yang berat atau berulang dari alamat IP yang sama dapat mengakibatkan pemblokiran sementara (HTTP 429/kesalahan masuk diperlukan). Gunakan VPN atau putar IP Anda jika Anda mengalami kegagalan pengunduhan. Alat ini ditujukan untuk penggunaan pribadi dan non-komersial saja. Pendistribusian ulang konten terjemahan dapat melanggar hak cipta - selalu hormati hak pencipta aslinya.

### Terjemahan waktu nyata (subtitel dan sulih suara eksperimental)

Tonton file lokal atau tautan video sesuai permintaan yang telah diselesaikan dengan terjemahan terjemahan dan terjemahan lisan opsional. Gunakan bilah di bawah pemutar:

**Dari tautan:**

1. Tempelkan tautan di bidang **URL**
2. Tetapkan bahasa sumber dan target, pilih suara dan sesuaikan penggeser **Delay**
3. Pilih **Suara yang disulihsuarakan** dan/atau **Subtitel**
4. Untuk hanya mendengar suara terjemahan, pilih **Mute original audio** sebelum memulai (dalam bahasa Italia: **Silenzia originale**, di samping kotak centang subtitle)
5. Klik **Terjemahkan secara real time** - tautan terselesaikan dan terjemahan dimulai

**Dari file yang dimuat:** memuat video ke pemutar (Input -> Tambah, lalu pilih), biarkan kolom URL kosong, pilih pengaturan langsung yang sama, dan klik **Terjemahkan secara real time**. URL mendapat prioritas jika kolomnya tidak kosong.

- **Mesin:** MarianMT (offline, default), Google, DeepL, atau Ollama. Pengenalan ucapan (Whisper) berjalan secara lokal. Model offline memerlukan pengunduhan awal.
- **Jeda:** pada file dalam mode tertunda, berapa detik terjemahan yang dikumpulkan sebelum gambar berlanjut setelah jeda (minimal 8 dtk dengan suara, 4 dtk hanya dengan subtitle). Jika gambar terus berhenti, cadangan bertambah 4 dtk sampai 30 dtk dan bilah memberi tahu.
- **Dubbing suara:** pemutaran ucapan Edge-TTS eksperimental melalui instance mpv kedua. Ini memerlukan akses internet dan terpisah dari kloning suara batch.
- **Suara ElevenLabs:** opsional, di Pengaturan lanjutan > Kloning Suara > **Suara langsung ElevenLabs**. Masukkan kunci API, periksa, pilih model yang berbicara dalam bahasa tujuan dan sebuah suara. Teks terjemahan dikirim ke ElevenLabs (berbayar per karakter); kunci tetap di keyring sistem. Jika kunci atau kuota gagal, Edge-TTS melanjutkan. Juga dapat dibuka dari tombol **ElevenLabs…** di bilah waktu nyata, yang barisnya menunjukkan suara yang akan dipakai sulih suara.
  - Paket gratis ElevenLabs (diperiksa pada 27 September 2026): melalui API hanya suara bawaan (Roger, Sarah, George, River...) yang berfungsi, dengan 10.000 karakter per bulan dan paling banyak 4 permintaan sekaligus. Jendela menandai suara yang memerlukan paket berbayar.
  - Suara dari pustaka ElevenLabs, suara hasil kloning, dan karakter tambahan memerlukan langganan ElevenLabs berbayar, dibeli dari ElevenLabs dengan harga dan ketentuannya sendiri ([ElevenLabs pricing](https://elevenlabs.io/pricing)). VideoTranslatorAI tetap gratis, tidak berafiliasi dengan ElevenLabs, dan tidak membutuhkannya: Edge-TTS adalah suara bawaan yang gratis.
  - Model untuk waktu nyata, audio pertama setelah sekitar: Flash v2.5 0,2 dtk, Turbo v2.5 0,2 dtk, v3 Conversational 0,4 dtk. Multilingual v2 (0,9 dtk) dan v3 (1-2 dtk) terdengar lebih kaya tetapi tertinggal dari video; Turbo v2 dan Flash v2 hanya berbahasa Inggris.
  - Saat ElevenLabs menolak sebuah kalimat (kunci, paket, suara atau model tidak ditemukan, bahasa, karakter habis, terlalu banyak permintaan), bilah waktu nyata menyebutkan alasannya dan log menyimpan pesan asli dari ElevenLabs.
- **Bungkam audio asli:** tersedia sebelum memulai dan selama penerjemahan. Ini membungkam seluruh soundtrack asli, termasuk musik dan efek, namun membiarkan suara terjemahan tetap terdengar. Itu tidak mengisolasi orang yang berbicara dalam audio asli. Matikan untuk memulihkan soundtrack; itu diatur ulang ketika sesi langsung berakhir. Tombol speaker pemutar adalah tombol mute umum, bukan kontrol independen ini.
- **Jeda dan cari:** kontrol pemutar video terhubung ke sesi langsung; sinkronisasi audio ujung ke ujung masih memerlukan uji penerimaan khusus platform.
- **Batasan saat ini:** kalibrasi waktu audio dan uji penerimaan di Windows masih terbuka. Siaran langsung yang masih berlangsung tidak didukung; label mode langsung tidak berarti siaran yang sedang berjalan dapat diterima terus-menerus.

Untuk video sulih suara yang disimpan, gunakan **Unduh & Terjemahkan** / **Mulai Terjemahan** alih-alih pratinjau waktu nyata.

### Blok mesin terjemahan dan VPN

Dua blok berbeda dapat terjadi, dengan perbaikan berbeda:

| Blokir | Gejala | Perbaiki |
|-------|---------|-----|
| **Unduh** (yt-dlp) | "Masuk untuk mengonfirmasi bahwa Anda bukan bot", HTTP 429 | **VPN** / putar IP, atau masuk ke YouTube di browser Anda (cookie dibaca secara otomatis) |
| **Terjemahan** (titik akhir gratis Google) | "Google Translate tidak dapat menerjemahkan... tingkat permintaan dibatasi/diblokir" | Gunakan **MarianMT** (offline) atau **Ollama** (lokal) - tidak ada batasan tarif permintaan. VPN juga membantu. Aliran batch sekarang **kembali ke MarianMT secara otomatis** ketika Google diblokir. |

### Tema dan penampilan

Klik ikon roda gigi di header untuk membuka **Pengaturan**:

- **Tema**: Otomatis (mengikuti mode gelap/terang OS), Graphite (default), Slate, Light, Neon.
- **Skin**: Dex dan Handheld (konsol genggam, font piksel, bingkai tebal), CRT dan CRT Amber (monitor fosfor tahun 80-an; video juga mendapat lengkungan dan garis pindai melalui shader mpv). Graphite tetap menjadi bawaan.
- **Warna aksen**: default per tema, atau biru, teal, ungu, hijau, kuning, mawar.
- **Ukuran teks**: kecil, normal, besar, ekstra besar.
- **Bahasa antarmuka**: 26 bahasa.

Perubahan segera diterapkan, tanpa memulai ulang, dan disimpan dalam file konfigurasi (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Pulihkan default** mengembalikan tema Graphite, aksen default, ukuran teks normal, dan urutan default panel pengaturan.

### Baris perintah

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Semua opsi:**

| opsi CLI | Deskripsi | Bawaan |
|------|-------------|---------|
| `--lang-source` | Bahasa sumber (`auto` untuk deteksi otomatis) | `auto` |
| `--lang-target` | Kode bahasa target (misalnya `it`, `fr`, `de`) | `it` |
| `--voice` | Nama suara Edge-TTS | auto |
| `--model` | Model Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Penyesuaian kecepatan TTS (misalnya `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian`, atau `deepl` | `google` |
| `--deepl-key` | Kunci API DeepL Free | - |
| `--diarize` | Aktifkan identifikasi orang yang berbicara (diarisasi) (pyannote) | - |
| `--hf-token` | Token HuggingFace untuk diarisasi | - |
| `--lipsync` | Terapkan sinkronisasi bibir Wav2Lip setelah sulih suara suara | - |
| `--subs-only` | Hasilkan `.srt` saja, lewati dubbing suara | - |
| `--no-subs` | Lewati generasi `.srt` | - |
| `--no-demucs` | Lewati pemisahan suara/musik | - |
| `--output` / `-o` | Jalur file keluaran | auto |
| `--output-dir` | Folder untuk file yang diterjemahkan (satu tempat, Windows dan Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Memproses banyak file | - |
| `--voicebox` | Mengkloning suara lewat server Voicebox yang berjalan | - |
| `--voicebox-url` | Alamat Voicebox | `http://127.0.0.1:17493` |
| `--voicebox-engine` | Mesin Voicebox (`chatterbox`, `qwen`, ...) | `chatterbox` |

### tes integrasi dengan model nyata

Rangkaian pengujian default menghindari pengunduhan model nyata dan kerja GPU yang lama. Untuk menjalankan pemeriksaan empiris keikutsertaan untuk tumpukan lokal yang diinstal:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Pemeriksaan ini memvalidasi impor Wav2Lip yang sebenarnya, ketersediaan Torch CUDA, ketersediaan daemon Ollama, dan faster-Whisper pada ucapan sintetis. Mereka sengaja gagal atau dilewati ketika status driver/daemon/model lokal belum siap.

**Contoh:**

```bash
# Terjemahkan video Italia ke Bahasa Inggris dengan MarianMT lokal
# (mengunduh model ~298 MB pada penggunaan pertama, kemudian offline sepenuhnya)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Terjemahkan dengan kloning suara + identifikasi orang yang berbicara (diarisasi)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Terjemahkan dengan sinkronisasi bibir
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Hanya subtitle (tidak ada dubbing suara)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Model Whisper

| Model | Ukuran | Kecepatan | Akurasi |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` adalah versi sulingan dari `large-v3` (4 lapisan decoder vs 32) - kualitas mendekati besar pada kecepatan tingkat `medium`. Direkomendasikan default pada GPU modern ketika kecepatan transkripsi penting; penurunan kualitas pada materi multibahasa kecil.

> Model diunduh secara otomatis saat pertama kali digunakan.

> Tidak yakin model mana yang cocok untuk PC Anda? Buka **Model untuk PC ini** di pengaturan model: jendela itu menyarankan satu model sesuai perangkat keras Anda dan bisa mengukurnya.

## CLI modul mandiri

Paket modular memperlihatkan empat alat yang dapat diakses oleh pengguna yang dapat dipanggil secara langsung tanpa meluncurkan pipeline penuh:

```bash
# Pra-penerbangan video untuk kehadiran wajah (Wav2Lip akan dilewati jika tidak ada).
python3 -m videotranslator.face_detector path/to/video.mp4
# keluar 0 = ada wajah, keluar 1 = tidak ada wajah

# Analisis *_metrics.csv yang diproduksi oleh build_dubbed_track.
# Melaporkan P50/P75/P90/P95 dari pre_stretch_ratio, rincian pita audibilitas,
# penggunaan mesin peregangan, dan outlier terburuk N teratas dengan teks targetnya.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Sanitasi teks untuk TTS (menulis ulang titik dua, titik koma, elipsis, tanda hubung).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Perkirakan kesulitan sulih suara suara dari file segmen .srt atau .json SEBELUM menjalankan TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Setiap alat memiliki `-h`/`--help` untuk opsi lengkap. Mereka mandiri dan menggunakan kembali modul yang sama dengan yang diandalkan oleh saluran sulih suara suara, sehingga keluarannya tetap konsisten dengan waktu proses.

## Lisensi

MIT

### Komponen pihak ketiga

Kode repositori adalah MIT. Pemasang mengunduh komponen di bawah ini dari sumbernya sendiri pada waktu pemasangan; proyek tidak mendistribusikannya kembali.

- **libmpv** (https://github.com/mpv-player/mpv), mesin pemutar video terintegrasi. Windows: LGPL yang dibuat oleh zhongfly (https://github.com/zhongfly/mpv-winbuild) dicoba terlebih dahulu; GPL yang disematkan yang dibuat oleh shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) adalah cadangannya. `mpv-runtime\BUILD.txt` mencatat sumber, ragam lisensi, dan penerapan mpv, dan teks lisensi berada di sebelah DLL. Linux: paket distribusi (`libmpv2`, `libmpv1`, `mpv-libs` atau `mpv`).
- **FFmpeg** di dalam libmpv (LGPL atau GPL, mengikuti build libmpv).
- **python-mpv** (`mpv` di PyPI), GPLv2+ atau LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), digunakan oleh penginstal Windows untuk mengekstrak libmpv dan dihapus setelahnya.
- **Vulkan loader** (Khronos, MIT, dan Apache-2.0), diunduh di Windows hanya jika `vulkan-1.dll` tidak ada.
- **edge-tts** (LGPLv3), digunakan oleh pipeline sulih suara suara.
- **Model MarianMT** (Helsinki-NLP), diunduh dari Hugging Face Hub saat pertama kali digunakan di bawah lisensi mereka sendiri (Apache-2.0 untuk model `opus-mt`, CC-BY-4.0 untuk `opus-mt-tc-big`).
- **Voicebox** (MIT, https://github.com/jamiepine/voicebox), opsional, dipasang terpisah oleh pengguna; mesinnya punya lisensi sendiri (Chatterbox MIT dengan tanda air audio, bobot TADA di bawah Llama 3.2 Community License).
- **ElevenLabs** (https://elevenlabs.io), layanan daring opsional yang dipakai dengan akun dan kunci API milik pengguna sendiri, sesuai ketentuannya sendiri.
- Font **Pixelify Sans** dan **VT323** (SIL Open Font License 1.1), dipakai oleh skin: satu-satunya berkas pihak ketiga yang disertakan di repositori, di `assets/fonts` bersama teks lisensinya.
