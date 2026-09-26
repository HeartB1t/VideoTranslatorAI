# 🎬 Video Translator AI

[angol](../../README.md) | [Minden fordítás](README.md)

**Olvassa el ezt az oldalt:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

A mesterséges intelligencia által vezérelt videó hangszinkronizálási eszköz, amely automatikusan átírja, lefordítja és újraszinkronizálja a videókat 26 nyelvre, helyi feldolgozási lehetőségekkel, és alapértelmezés szerint nincs szükség API-kulcsokra. A Whisper beszédfelismerés helyben fut; Az Edge-TTS, a Google Translate és a DeepL internetkapcsolatot igényel. Az opcionális funkciókhoz (DeepL, beszélő emberek azonosítása (diarizálás)) API-kulcsra vagy hozzáférési tokenre lehet szükség.

> **v2.0** - moduláris csomag, helyi Ollama fordítás, minőségi profil hangszerelés, telepíthető Python-metaadatok és választható integrációs tesztek valós modellekkel. A változtatások teljes listáját a [GitHub-kiadások](https://github.com/HeartB1t/VideoTranslatorAI/releases) és a véglegesítési előzmények részben találja.

## Hogyan működik

1. **Átírás** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) átírja a hangot (GPU-gyorsítással)
2. **Hang/zene szétválasztás** - A [Demucs](https://github.com/facebookresearch/demucs) elkülöníti az énekhangot a háttérzenétől
3. **Fordítás** - MarianMT (helyi, offline), Google Translate, DeepL Free vagy **Ollama LLM** (Qwen3, réseket ismerő tömör fordítások)
4. **beszélő emberek azonosítása (diarizálás)** *(nem kötelező)* - A [pyannote-audio](https://github.com/pyannote/pyannote-audio) azonosítja, hogy ki beszél az egyes szegmensekben
5. **hang szinkronizálás** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ hang) vagy [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (hangklónozás, a beszélgetés minden egyes beszélőjéhez)
6. **Keverés** - szinkronhang visszakeverve eredeti háttérzenével
7. **Normalizálás** - a végső hang -23 LUFS-re normalizálva (EBU R128 sugárzási szabvány)
8. **Ajkak szinkronizálása** *(opcionális)* - A [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) szinkronizálja a száj mozgását a szinkronizált hanghoz

## Jellemzők

- 🖥️ Tematikus GUI (Tkinter) - nincs szükség parancssorra; Graphite, Slate, Light és Neon témák, kiemelő színek, szövegméret és beállítási panelek, amelyeket húzással átrendezhet
- 🌍 **26 célnyelv** nyelvenként több hanggal
- 🌐 **UI 26 nyelven** - maga a felület igazodik az Ön nyelvéhez
- 🎬 **YouTube és URL-támogatás** - illesszen be bármilyen YouTube-linket, és fordítsa le közvetlenül (az yt-dlp segítségével)
- ▶️ **Integrált videolejátszó** (libmpv/mpv) - színkódolt átviteli vezérlők, lejátszási lista, A/B eredeti vs szinkronhang, feliratok váltása, pillanatfelvétel, teljes képernyő, mappa megnyitása
- ⏱️ **Valós idejű fordítás** - nézzen meg egy helyi fájlt vagy egy megoldott igény szerinti videólinket lefordított feliratokkal és egy YouTube-stílusú késleltetési csúszkával; motorok MarianMT / Google / DeepL / Ollama. A kísérleti hangszinkronizálás Edge-TTS-t és egy második mpv-példányt használ. A hangátfedés kezelése és a valódi hang/Windows elfogadás folyamatban van; a növekvő élő adások még nem támogatottak. Lásd az [élő megvalósítási állapot](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Hang/zene elválasztás a Demucs segítségével (megtartja a háttérzenét)
- 🔇 Az élő fordítás előtt és közben elérhető **Eredeti hang némítása** elnémítja a videó hangsávját, miközben a lefordított hang hallható marad. Kapcsolja ki az eredeti hang visszaállításához; az élő munkamenet végén visszaáll.
- 🧠 **MarianMT** - teljesen lokális, offline neurális fordítás (Helsinki-NLP, nincs kérési sebességkorlát, nincs API kulcs)
- 🤖 **Ollama LLM fordítás** *(új a 2.0-s verzióban)* - helyi LLM (Qwen3, Llama, Mistral), amely résigényes tömör fordításokat készít a természetes hangszinkronhoz, automatikusan felismeri/telepíti/indítja/lehúzza a modellt első használatkor
- 🎙️ **Hang klónozás** - A Coqui XTTS v2 klónozza az eredeti hang hangján beszélő személyt a célnyelven (~1,8 GB-os modell), szegmensenkénti adaptív sebességgel és többmagos újrapróbálkozással a hallucinációkra
- 👥 **beszélő emberek azonosítása (diarizáció)** - a pyannote-audio 3.1 több beszélőt azonosít; Az XTTS minden hangot külön klónoz
- 💋 **Lip Sync** - A Wav2Lip GAN szinkronizálja a szájmozgásokat a szinkronizált hanghoz (~416 MB modell)
- 🔊 **Hang normalizálás** - automatikus -23 LUFS hangerő normalizálás (EBU R128)
- ✏️ Feliratszerkesztő - a hangszinkronizálás előtt tekintse át és javítsa ki a feliratokat
- 📦 Kötegelt feldolgozás - több videó vagy URL lefordítása egyszerre
- ⚡ GPU-gyorsítás CUDA-n keresztül (automatikusan visszaesik a CPU-ra)
- 📄 Opcionális `.srt` felirat exportálás
- 🔁 **DeepL Free** fordítómotor (opcionális - 500 000 karakter/hó, ingyenes API-kulcs szükséges)
- 🔧 **Automatikus telepítés** - a hiányzó Python-csomagok és az ffmpeg automatikusan telepítésre kerülnek az első indításkor

## Támogatott nyelvek

arab, kínai, cseh, dán, holland, angol, finn, francia, német, görög, hindi, magyar, indonéz, olasz, japán, koreai, norvég, lengyel, portugál, román, orosz, spanyol, svéd, török, ukrán, vietnami

## Hang katalógus

Az Edge-TTS hangkatalógus a `LANGUAGES`-ben, a `video_translator_gui.py` tetején található. Ez a szótár az igazság forrása a célnyelvek neveihez, a GUI hangrádiógombjaihoz és a CLI tartalék hangjához, ha a `--voice` kimarad.

A Claude/projekt karbantartási megjegyzései tükrözik ezt a helyet a `CLAUDE.md`-ben a **Voice Catalog Source Of Truth** alatt, így a jövőbeli kódügynökök tudják, hol kell frissíteni a hangokat, és hová mutat a README a felhasználókat.

## Fordító motorok

| Motor | Beállítás | Korlátok | Minőség |
|--------|-------|--------|---------|
| **Google Translate** *(alapértelmezett)* | Egyik sem | Nem hivatalos kaparás - nagyméretű videóknál le lehet tiltani | ★★★★ |
| **MarianMT** | Nincs - az első használatkor nyelvpáronként ~298 MB letöltés | Nincs - letöltés után teljesen offline | ★★★★ |
| **DeepL Free** | Ingyenes API-kulcs a [deepl.com](https://www.deepl.com/pro-api) oldalon | 500 ezer karakter/hó | ★★★★★ |
| **Ollama LLM** *(hangszinkronhoz ajánlott - új a 2.0-s verzióban)* | Automatikus telepítés első használatkor (~1 GB Ollama + 5 GB modell) | Nincs - teljesen helyi | ★★★★★ |

> A **MarianMT** [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) modelleket használ, az első letöltés után helyi gyorsítótárban. Explicit forrásnyelv szükséges (az automatikus felismerés nem támogatott - válassza ki manuálisan a forrásnyelvet). A szükséges Python-csomagok (`sacremoses`, `sentencepiece`) automatikusan települnek az első kiválasztáskor, ha hiányoznak.

> Az **Ollama LLM** *(új a 2.0-s verzióban)* az ajánlott motor a hangszinkronizáláshoz, mivel a fordításokat a célidőrés tudatában készíti. Ahol a MarianMT szó szerint fordítja, és az olasz/spanyol/francia nyelvet kb. 25%-kal hosszabb ideig állítja elő, mint az angolt (hallható hangtömörítést kényszerítve a TTS-re), az LLM arra kéri, hogy minden szegmens tömör és természetes legyen a beszédben, így a tipikus karakterarány 0,85-0,95 a forráshoz viszonyítva. Az alapértelmezett modell a `qwen3:8b` (5,2 GB lemezen, ~6 GB VRAM); A `qwen3:4b` (~3 GB) a könnyű, a `qwen3:14b` a jobb minőségű opció. A folyamat automatikusan felismeri az Ollama bináris fájlt, első használatkor automatikusan telepíti a hivatalos telepítőn keresztül (beleegyezés felugró ablakkal), elindítja a démont és lehívja a kiválasztott modellt - nincs szükség manuális beállításra. Automatikusan átvált a Google Translate-re, ha valami hiányzik.

## Hangklónozás (XTTS v2)

Ha engedélyezve van, az alkalmazás kivonja a beszélő hangját az eredeti videóból, és referenciaként használja a hang célnyelvi klónozására.

- Támogatott nyelvek: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- A fennmaradó 9 nyelv esetében az Edge-TTS automatikusan tartalékként használatos
- A modell (~1,8 GB) az első használatkor automatikusan letöltődik a `~/.local/share/tts/` fájlba
- **VAD-szűrt referencia** (v1.4): 10-15 mp folyamatos beszéd az eredeti hangból a [silero-vad](https://github.com/snakers4/silero-vad) segítségével kiválasztva a jobb hangklónozási minőség érdekében
- **Állítási sebesség** konfigurálható (`xtts_speed`, alapértelmezett `1.25`): a magasabb értékek csökkentik az utófeldolgozási hangtömörítési melléktermékeket, ha a lefordított szöveg hosszabb, mint a forráshely. Hangolás a `~/.config/videotranslatorai/config.json` vagy a CLI `--xtts-speed` segítségével
- CUDA-n vagy CPU-n fut

## beszélő emberek azonosítása (diarizáció) (pyannote-audio)

Ha engedélyezve van, az alkalmazás azonosítja, hogy ki beszél az egyes szegmensekben. A Voice Cloning funkcióval kombinálva minden felszólaló hangját külön klónozzák - ideális interjúkhoz, podcastokhoz és többszemélyes videókhoz.

- Ingyenes [HuggingFace token](https://huggingface.co/settings/tokens) szükséges (egyszeri regisztráció)
- **Token biztonságosan tárolva** (v1.4) az operációs rendszer kulcstartóján keresztül: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatikus áttelepítés a korábbi egyszerű szöveges JSON-tárhelyről
- Az első letöltés után teljesen offline módban működik
- Típus: `pyannote/speaker-diarization-3.1`

## Ajak szinkronizálás (Wav2Lip)

Ha engedélyezve van, az alkalmazás a Wav2Lip GAN-t alkalmazza, hogy szinkronizálja az alany szájmozgását a szinkronizált hanggal - úgy tűnik, hogy a személy beszéli a lefordított nyelvet.

- Modell (~416 MB) és repo automatikusan klónozva első használatkor `~/.local/share/wav2lip/`
- CUDA-n (ajánlott) vagy CPU-n fut
- Jelentősen megnöveli a feldolgozási időt
- Egyetlen, jól látható arcú videóknál működik a legjobban

## Követelmények

- Python 3.10+ (a Windows telepítőprogram 3.11.9 automatikusan)
- Windows 10/11 (x64), Linux vagy macOS
- **NVIDIA GPU erősen ajánlott** - lásd az alábbi GPU-táblázatot
- 20 GB szabad lemezterület a teljes telepítéshez (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **Az ffmpeg és az összes Python-csomag automatikusan települ** az első indításkor, ha hiányzik. Nincs szükség kézi beállításra.

**Opcionális rendszerfüggőség** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Telepítéskor a hangmagasság-megőrző időnyújtásra szolgál a profilvezérelt minőségi sávban (alapértelmezett 1,15-1,50, kemény tartalom esetén 1,65-ig), eltávolítva a klónozott XTTS-hangok maradék "mókus"-effektusát. A folyamat változatlanul fut nélküle (automatikus visszaállás az ffmpeg `atempo`-re). A minőségi profilok most az extra rövid fordítási újrapróbálkozásokat részesítik előnyben az extrém hanggyorsítás helyett.

### GPU támogatás

A folyamat öt GPU-gyorsított komponenst használ (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). A GPU-lefedettség nem egységes a gyártók között:

| GPU | Windows | Linux | Megjegyzések |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx vagy újabb, CUDA 12.4 illesztőprogram) | ✅ teljes gyorsulás | ✅ teljes gyorsulás | **Ajánlott.** Mind az 5 összetevő GPU-n fut. |
| **AMD** (Radeon) | ⚠️ hiányos (A DirectML nem támogatja az XTTS-t és a faster-whisper-t) | ⚠️ Részleges (a ROCm működik Demucs/XTTS/pyannote esetén, de a faster-whisper csak a CUDA-t támogatja) | Működik, de a Whisper átírás a CPU-n marad, és uralja a teljes időt. |
| **Intel Arc** | ⚠️ éretlen PyTorch XPU támogatás | ⚠️ Ugyanaz | Nem tesztelt. |
| **Nincs (csak CPU)** | ✅ működik | ✅ működik | Várhatóan **10-20-szor lassabb**, mint a valós időben. Egy 5 perces klip 50-nél több percig tarthat, csak a Whisper large-v3 segítségével történő átírása. |

**Ajánlott NVIDIA VRAM:**

| VRAM | Jellemző videokártyák | Tapasztalat |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Használható, nem futtatható egyszerre az XTTS + Wav2Lip |
| 8 GB | RTX 3060 Ti, 4060 | Teljes csővezeték, margó nélkül |
| **12 GB+** | **RTX 3060 12 GB, 4070, 4080** | **Ajánlott - kényelmes** |
| 24 GB | RTX 3090, 4090 | Tartalék kapacitás nagy tételekhez |

## Telepítés

### Windows

1. Klónozza vagy töltse le ezt a tárolót
2. Kattintson jobb gombbal a `setup_windows.bat` → **Futtatás rendszergazdaként** elemre → a menüben megjelenik a `[1] Install`
3. A telepítő automatikusan:
   - Telepíti a Python 3.11-et, ha nincs jelen (rendszerszintű)
   - Telepíti a Git for Windows-t, ha nincs jelen
   - Telepíti az összes Python-függőséget (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps stb.)
   - Letölti és telepíti az ffmpeg-et
   - Telepíti az integrált videolejátszót (python-mpv plusz egy libmpv build a `mpv-runtime`-ben). A lépés nem kötelező: ha nem sikerül, minden más működik, és a lejátszópanel elmagyarázza, mi hiányzik
   - Létrehoz egy **Public Desktop parancsikont** (látható minden Windows-fiókban a számítógépen)

> A telepítő **többfelhasználós**: minden a rendszerre telepítve van a `%ProgramFiles%\VideoTranslatorAI` alatt, és a gép bármely Windows-felhasználója készen találja a parancsikont. A VS C++ Build Toolsra **már nincs szükség** - a karbantartott `coqui-tts` villa előre összeállított Python kerékcsomagokat biztosít.

### Linux / macOS

```bash
# A repo klónozása
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Opcionális: telepítse a tesztelt NVIDIA CUDA 12.4 PyTorch stacket előre
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Nem kötelező: telepítse elő az összes Python futásidejű csomagot a grafikus felhasználói felület engedélyezése helyett
# telepítse a hiányzó csomagokat első futtatásra
pip install --break-system-packages -r requirements.txt

# Opcionális: az integrált videolejátszó (libmpv a disztribúcióból, python-mpv a PyPI-ből)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Nem kötelező: telepítse a projektet szerkeszthető Python-csomagként
pip install --break-system-packages --no-deps -e .

# Indítsa el a forrásból
python video_translator_gui.py

# Vagy szerkeszthető/csomagos telepítés után
videotranslatorai
videotranslatorai --preflight
```

> Az első indításkor a grafikus felület észleli a hiányzó csomagokat (faster-whisper, Demucs, Edge-TTS stb.), és automatikusan telepíti őket, és a kimenetet a naplóablakba továbbítja. Az ffmpeg szintén automatikusan települ a `apt-get` / `dnf` / `pacman` (Linux) keresztül, vagy letölthető a GitHubról (Windows).

> A fejlécben egy **Játékos** jelvény látható. Ha hiányzik a libmpv vagy a python-mpv, a bal oldali ablaktáblában megjelenik, hogy mi hiányzik, és felajánlja a **Lejátszó telepítése** lehetőséget: Linuxon a csomagkezelőt használja a pkexecen keresztül (akkor `sudo -n`), és a kézi parancsot mutatja, ha egyik sem működik; Windowson rákérdez, mielőtt letölti a libmpv-t az aktuális felhasználóhoz (kb. 32 MB).

### Követelményprofilok

| Fájl | Cél |
|------|---------|
| `requirements.txt` | Teljes, visszafelé kompatibilis futásidejű telepítés. |
| `requirements-core.txt` | A GUI/CLI által használt alapértelmezett folyamatcsomagok. |
| `requirements-optional.txt` | XTTS, MarianMT tokenizátorok, naplózás, VAD, kulcstartó. |
| `requirements-wav2lip.txt` | Wav2Lip futásidejű és arcfelismerési verem (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | A PyTorch stack NVIDIA CUDA 12.4 kerekekkel tesztelve. |
| `requirements-player.txt` | Integrált videolejátszó: python-mpv (libmpv szükséges a rendszerből vagy a Windows telepítőből). |
| `requirements-dev.txt` | A CI/egységtesztek által használt könnyű függőségek. |

## Eltávolítás

### Windows

Futtassa a `setup_windows.bat`-t (jobb gombbal kattintson → **Futtatás rendszergazdaként**), és válassza ki a `[3] Uninstall` elemet a menüből. Három eltávolítási almód kínálkozik:

| mód | Admin szükséges | Hatály |
|------|----------------|-------|
| **[1] Teljes eltávolítás - egy kattintás** | ✅ | Eltávolítja az alkalmazásmappát, a nyilvános asztal parancsikonját, az ffmpeg-et a gép PATH-járól, minden felhasználó HF-modell gyorsítótárát (Whisper/XTTS) és konfigurációját (`HF token`), valamint a telepítő által telepített összes Python AI-csomagot. A végén azt is megkérdezi (feliratkozás), hogy csendesen távolítsa-e el a **Python 3.11** és **Git for Windows** rendszerleíró adatbázis csendes eltávolítási karakterláncain keresztül. |
| **[2] Csak jelenlegi felhasználó** | ❌ | Csak a futó felhasználó VTAI konfigurációját, HF/XTTS gyorsítótárát és a régi felhasználónkénti telepítést távolítja el. **Érintetlenül hagyja a rendszerszintű telepítést**, így a számítógépen lévő többi Windows-fiók továbbra is használhatja az alkalmazást. |
| **[3] Egyéni - szemcsés** | ✅ rendszerelemekhez, ❌ felhasználói elemekhez | Y/N-kérdés minden kategóriához: alkalmazásmappa, parancsikon, rendszerszintű PATH, régi felhasználónkénti telepítések, felhasználói beállítások és gyorsítótárak, majd Python-csomagcsoportok (TTS, PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip-függőségek, pyannote és a feldolgozási folyamat segédprogramjai), végül a Python 3.11 és a Git opcionális eltávolítása. |

**Soha nem távolítják el automatikusan:** Visual Studio C++ Build Tools (ha van régebbi futtatásokból). Használja az *Alkalmazásokat és funkciókat* a Windows beállításaiban, ha kívánja, kézzel távolítsa el őket.

### Linux / macOS

Nincs dedikált eltávolító - távolítsa el manuálisan:

```bash
# A grafikus felhasználói felület automatikus telepítője által telepített Python-csomagok
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Felhasználói adatok és modell gyorsítótárak
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # konfiguráció (témák, panelek sorrendje, beállítások)
rm -f  ~/.videotranslatorai_config.json     # <= 1.9-es verziók örökölt konfigurációja, ha van
```

## Használat

### Diagnosztika

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Lefuttatja a helyi környezet diagnosztikáját anélkül, hogy elkezdené a fordítást vagy bármit telepítene. A `--preflight-lipsync` igény szerint kezeli a Wav2Lip arccsomagokat, ami hasznos a **Lip Sync** engedélyezése előtt. A grafikus felhasználói felület ugyanazt az alapellenőrzést teszi közzé a naplópanel **Diagnosztika** gombjával. A `--preflight-player` igény szerint kezeli az integrált videolejátszót (python-mpv és egy betölthető libmpv). A `python -m videotranslator.libmpv_runtime check` egyedül a libmpv-t vizsgálja (kilépés 0 kész, 2 nem érhető el).

### GUI

```bash
python video_translator_gui.py
```

**Elrendezés:** A kötegelt fordítási beállítások a jobb oldali oszlopban találhatók, beállításpanelek halmazaként: **Bevitel**, **Fordítás**, **Munkafolyamat-profil**, **Start** és az összecsukható speciális szakaszok (modell, fordítómotor, hang, hangklónozás, ajakszinkronizálás, naplózás, opciók, hotwords). A bal oldalon található nagy terület az **integrált videolejátszó** (szállítás, lejátszási lista, A/B eredeti vs szinkronhang, feliratok, pillanatkép, teljes képernyő), alatta a **valós idejű fordítás** sávval. Húzza a kártyát a címe vagy a **≡** fogantyú alapján felfelé vagy lefelé az oszlopban; a rendelés mentésre kerül (`ui_panel_order`), és a következő indításkor visszaáll. Az alsó naplópanel elrejthető a **Napló elrejtése** funkcióval. Indításkor az ablak az aktuális monitor (a mutató alatti) középpontjában nyílik meg, és maximalizálva, így jól viselkedik többmonitoros beállítás esetén.

**Video-videolejátszó vezérlői:** Az ikonok minden témában egységes funkcionális színeket használnak, függetlenül a kiválasztott kiemelő színtől:

| Irányítás | Szín |
|---------|--------|
| Videó lejátszása | zöld |
| Szünet (a Lejátszás lejátszás közben helyettesíti) | Amber |
| Lejátszás leállítása | Korall vörös |
| Előző / vissza 10 s / előre 10 s / következő | kék |
| Pillanatkép | Violet |
| Nyissa meg a mappát | Arany |

A lebegés finoman színezett hátteret ad. A nem elérhető vezérlők semlegesek; A lejátszási lista navigációja a Stop után is használható marad. Az eszköztippek és a billentyűzet fókuszjelzői továbbra is elérhetők, így nem a szín az egyetlen módja a műveletek azonosításának.

**Helyi fájlokból:**
1. Kattintson a **Hozzáadás** gombra egy vagy több videofájl kiválasztásához
2. Válassza ki a forrás- és célnyelvet
3. Nyissa meg a **Modell** részt, és válasszon egy Whisper modellt (a `small` jó egyensúlyt biztosít a sebesség/pontosság között)
4. Válasszon hangot, és szükség esetén állítsa be a TTS sebességét
5. *(Opcionális)* A **Fordítómotorban** válassza a **Google** (alapértelmezett), **MarianMT** (helyi/offline), **DeepL Free** vagy **Ollama LLM** (helyi, hangszinkronizáláshoz ajánlott) lehetőséget.
6. *(Opcionális)* Engedélyezze a **Hang klónozást** (XTTS v2) és/vagy **a beszélő emberek azonosítását (diarizálás)**
7. *(Opcionális)* **Ajkszinkronizálás** (Wav2Lip) engedélyezése
8. Kattintson a **Fordítás indítása** gombra

**A YouTube-ról (vagy bármely támogatott webhelyről):**
1. Illesszen be egy vagy több URL-t az **URL** mezőbe (soronként egyet)
2. A szokásos módon konfigurálja a nyelvet, a modellt és a hangot
3. Kattintson a **⬇ Letöltés és fordítás** elemre

> Az yt-dlp támogatja a YouTube-ot, a Vimeót, a Twitter/X-et, a TikTokot és [1000+ egyéb webhelyet](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Fair use megjegyzés:** A videók yt-dlp-n keresztüli letöltése az olyan platformok által, mint a YouTube, automatikus hozzáférésnek minősül, és megsértheti az Általános Szerződési Feltételeket. Az azonos IP-címről történő intenzív vagy ismételt használat ideiglenes blokkolásokat eredményezhet (HTTP 429 / bejelentkezési hibák). Használjon VPN-t, vagy forgassa el az IP-címét, ha letöltési hibákat tapasztal. Ez az eszköz kizárólag személyes, nem kereskedelmi használatra készült. A lefordított tartalom továbbterjesztése sértheti a szerzői jogokat - mindig tartsa tiszteletben az eredeti alkotó jogait.

### Valós idejű fordítás (feliratok és kísérleti hangszinkron)

Nézzen meg egy helyi fájlt vagy egy megoldott igény szerinti videólinket lefordított feliratokkal és opcionális szóbeli fordítással. Használja a lejátszó alatti sávot:

**A linkről:**

1. Illesszen be egy linket az **URL** mezőbe
2. Állítsa be a forrás- és célnyelvet, válasszon hangot, és állítsa be a **Késleltetés** csúszkát
3. Válassza a **Szinkronizált hang** és/vagy a **Feliratok** lehetőséget
4. Ha csak a lefordított hangot szeretné hallani, a kezdés előtt válassza az **Eredeti hang némítása** lehetőséget (olaszul: **Silenzia originale**, a felirat jelölőnégyzete mellett)
5. Kattintson a **Valós idejű fordítás** lehetőségre - a link feloldódik, és elindul a fordítás

**Betöltött fájlból:** töltsön be egy videót a lejátszóba (Bevitel -> Hozzáadás, majd válassza ki), hagyja üresen az URL mezőt, válassza ki ugyanazokat az élő beállításokat, majd kattintson a **Valós idejű fordítás** lehetőségre. Az URL elsőbbséget élvez, ha a mező nem üres.

- **Motor:** MarianMT (offline, alapértelmezett), Google, DeepL vagy Ollama. A beszédfelismerés (Whisper) helyileg fut. Az offline modellekhez először le kell tölteni.
- **Hangszinkronizálás:** kísérleti Edge-TTS beszédlejátszás egy második mpv-példányon keresztül. Internet-hozzáférést igényel, és különálló a kötegelt hangklónozástól.
- **Eredeti hang némítása:** A fordítás megkezdése előtt és közben is elérhető. Elnémítja a teljes eredeti hangsávot, beleértve a zenét és az effektusokat is, de hallhatóvá teszi a lefordított hangot. Nem izolálja az eredeti hanganyagban beszélő személyt. Kapcsolja ki a hangsáv visszaállításához; az élő munkamenet végén visszaáll. A lejátszó hangszóró gombja az általános némítás, nem ez a független vezérlő.
- **Szünet és keresés:** A videolejátszó vezérlői az élő munkamenethez csatlakoznak; A végpontok közötti hangszinkronizáláshoz továbbra is platform-specifikus elfogadási tesztekre van szükség.
- **Jelenlegi korlátok:** A klipek átfedésének/elhalványításának kezelése, a hangidőzítés kalibrálása és a Windows elfogadása nyitva marad. A növekvő élő adások még nem támogatottak; az élő mód címke nem jelenti azt, hogy támogatja a közvetítés növekedését. Lásd a [megvalósítás állapota és hátralévő munka](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Mentett szinkronizált videóhoz használja a **Letöltés és fordítás** / **Fordítás indítása** lehetőséget a valós idejű előnézet helyett.

### Fordítómotor blokkok és VPN

Két különböző blokk történhet, különböző javításokkal:

| Blokk | Tünet | Fix |
|-------|---------|-----|
| **Letöltés** (yt-dlp) | "Jelentkezzen be, hogy megerősítse, hogy nem bot", HTTP 429 | **VPN** / IP-cím elforgatása, vagy jelentkezzen be a YouTube-ra a böngészőjében (a cookie-k beolvasása automatikusan történik) |
| **Fordítás** (Google ingyenes végpont) | "Google Translate nem tudta lefordítani... a kérés sebessége korlátozott/blokkolva" | Használja a **MarianMT** (offline) vagy **Ollama** (helyi) szolgáltatást - nincs kérési sebességkorlátozás. A VPN is segít. A kötegelt folyamat mostantól **automatikusan visszatér a MarianMT-hez**, ha a Google le van tiltva. |

### Témák és megjelenés

Kattintson a fogaskerék ikonra a fejlécben a **Beállítások** megnyitásához:

- **Téma**: Automatikus (követi az operációs rendszer sötét/világos üzemmódját), Graphite (alapértelmezett), Slate, Light, Neon.
- **Kiemelési szín**: alapértelmezett témánként, vagy kék, kékeszöld, lila, zöld, borostyán, rózsa.
- **Szövegméret**: kicsi, normál, nagy, extra nagy.
- **Interfész nyelve**: 26 nyelv.

A változtatások azonnal, újraindítás nélkül érvényesülnek, és a konfigurációs fájlba kerülnek (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). Az **Alapértelmezések visszaállítása** visszaállítja a Graphite témát, az alapértelmezett ékezetet, a normál szövegméretet és a beállítási panelek alapértelmezett sorrendjét.

### Parancssor

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Minden lehetőség:**

| CLI opció | Leírás | Alapértelmezett |
|------|-------------|---------|
| `--lang-source` | Forrásnyelv (`auto` az automatikus felismeréshez) | `auto` |
| `--lang-target` | Célnyelvi kód (pl. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS hangnév | auto |
| `--model` | Whisper modell (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS sebességbeállítás (pl. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` vagy `deepl` | `google` |
| `--deepl-key` | DeepL Free API kulcs | - |
| `--diarize` | A beszélő emberek azonosításának engedélyezése (naplóírás) (pyannote) | - |
| `--hf-token` | HuggingFace token naplózáshoz | - |
| `--lipsync` | A hangszinkronizálás után alkalmazza a Wav2Lip ajakszinkronizálást | - |
| `--subs-only` | Csak a `.srt` generálása, a hangszinkron kihagyása | - |
| `--no-subs` | `.srt` generáció kihagyása | - |
| `--no-demucs` | A hang/zene szétválasztásának kihagyása | - |
| `--output` / `-o` | Kimeneti fájl elérési útja | auto |
| `--output-dir` | Mappa a lefordított fájlokhoz (egy helyen, Windows és Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Több fájl feldolgozása | - |

### integrációs tesztek valós modellekkel

Az alapértelmezett tesztcsomag elkerüli a valódi modellletöltéseket és a hosszú GPU-munkát. A telepített helyi verem engedélyezési empirikus ellenőrzésének futtatása:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Ezek az ellenőrzések érvényesítik a valódi Wav2Lip importálást, a Torch CUDA elérhetőségét, az Ollama démon elérhetőségét és a faster-Whisper szintetikus beszédet. Szándékosan meghiúsulnak vagy kihagyják, ha a helyi illesztőprogram/démon/modell állapot nem áll készen.

**Példák:**

```bash
# Fordítsa le az olasz videót angolra a helyi MarianMT-vel
# (~298 MB modell letöltése első használatkor, majd teljesen offline állapotban)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Fordítás hangklónozással + beszélő emberek azonosítása (diarizálás)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Fordítás ajakszinkronnal
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Csak feliratok (hangszinkron nincs)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper modellek

| Modell | Méret | Sebesség | Pontosság |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> A `large-v3-turbo` a `large-v3` desztillált változata (4 dekóderréteg vs 32) - közel nagy minőség, nagyjából `medium`-szintű sebességgel. Javasolt alapértelmezés modern GPU-n, ha az átírási sebesség számít; a többnyelvű anyagok minősége csekély mértékű.

> A modellek első használatkor automatikusan letöltődnek.

## Önálló modul CLI-k

A moduláris csomag négy felhasználóbarát eszközt tesz elérhetővé, amelyek közvetlenül, a teljes folyamat elindítása nélkül hívhatók meg:

```bash
# Készítsen elő egy videót az arc jelenléte érdekében (a Wav2Lip kihagyja, ha nincs jelen).
python3 -m videotranslator.face_detector path/to/video.mp4
# kilépés 0 = arc jelen van, kilépés 1 = nincs arc

# Elemezze a build_dubbed_track által készített *_metrics.csv fájlt.
# P50/P75/P90/P95 jelentések a pre_stretch_ratio-ről, a hallási sáv meghibásodása,
# meghosszabbítja a motorhasználatot, és az első N legrosszabb kiugró értékeket a célszövegükkel.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Szövegtisztítás a TTS-hez (átírja a kettőspontokat, pontosvesszőket, ellipsziseket, kötőjeleket).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# A TTS futtatása ELŐTT becsülje meg a hangszinkronizálási nehézséget egy .srt vagy .json szegmensfájlból.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Mindegyik szerszám rendelkezik `-h`/`--help`-vel a teljes opcióhoz. Önállóak, és ugyanazokat a modulokat használják újra, amelyekre a hangszinkronizálási folyamat támaszkodik, így kimenetük konzisztens marad a futásidővel.

## Licenc

MIT

### Harmadik féltől származó összetevők

Az adattár kódja MIT. A telepítők a telepítéskor letöltik az alábbi összetevőket saját forrásukból; a projekt nem osztja újra őket.

- **libmpv** (https://github.com/mpv-player/mpv), az integrált videolejátszó motorja. Windows: először a zhongfly LGPL buildjét (https://github.com/zhongfly/mpv-winbuild) próbáljuk ki; a shinchiro rögzített GPL buildje (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) a tartalék. A `mpv-runtime\BUILD.txt` rögzíti a forrást, a licenc ízét és az mpv véglegesítést, és a licenc szövege a DLL mellett található. Linux: a terjesztési csomag (`libmpv2`, `libmpv1`, `mpv-libs` vagy `mpv`).
- **FFmpeg** a libmpv-n belül (LGPL vagy GPL, a libmpv buildjét követve).
- **python-mpv** (`mpv` PyPI-n), GPLv2+ vagy LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), a Windows telepítője a libmpv kibontására használta, majd törölte.
- **Vulkan loader** (Khronos, MIT és Apache-2.0), csak akkor tölthető le Windows rendszerre, ha a `vulkan-1.dll` hiányzik.
- **edge-tts** (LGPLv3), a hangszinkronizálási folyamat használja.
- **MarianMT modellek** (Helsinki-NLP), letöltve a Hugging Face Hub-ról első használatkor saját licencük alapján (Apache-2.0 a `opus-mt` modellekhez, CC-BY-4.0 a `opus-mt-tc-big`-hez).
