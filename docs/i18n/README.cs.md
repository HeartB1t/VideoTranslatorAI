# 🎬 Video Translator AI

[anglicky](../../README.md) | [Všechny překlady](README.md)

**Přečtěte si tuto stránku v:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Nástroj pro dabování videí pomocí umělé inteligence, který automaticky přepisuje, překládá a dabuje videa do 26 jazyků. Nabízí místní zpracování a ve výchozím nastavení nevyžaduje klíče API. Rozpoznávání řeči Whisper běží lokálně; Edge-TTS, Google Translate a DeepL vyžadují připojení k internetu. Volitelné funkce (DeepL, rozlišení mluvčích) mohou vyžadovat klíč API nebo přístupový token.

> **v2.0** - modulární balíček, místní překlad přes Ollama, řízení pomocí profilů kvality, metadata pro instalaci balíčku Python a volitelné integrační testy se skutečnými modely. Úplný seznam změn naleznete v [přehledu vydání na GitHubu](https://github.com/HeartB1t/VideoTranslatorAI/releases) a historii commitů.

## Jak to funguje

1. **Přepis** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) přepisuje zvuk (urychlený GPU)
2. **Oddělení hlasu a hudby** - [Demucs](https://github.com/facebookresearch/demucs) izoluje vokály od hudby na pozadí
3. **Překlad** - MarianMT (místní, offline), Google Translate, DeepL Free nebo **Ollama LLM** (Qwen3, stručné překlady pro sloty)
4. **identifikace mluvících lidí (diarizace)** *(volitelné)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifikuje, kdo mluví v každém segmentu
5. **Dabing** - [Edge-TTS](https://github.com/rany2/edge-tts) (více než 400 hlasů) nebo [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (klonování hlasu pro každého mluvčího)
6. **Míchání** - dabovaný hlas smíchaný s původní hudbou na pozadí
7. **Normalizace** - finální zvuk normalizován na -23 LUFS (vysílací standard EBU R128)
8. **Synchronizace rtů** *(volitelné)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synchronizuje pohyby úst s dabovaným zvukem

## Vlastnosti

- 🖥️ Tématické GUI (Tkinter) - není potřeba žádný příkazový řádek; Motivy Graphite, Slate, Light a Neon, zvýrazňující barvy, velikost textu a panely nastavení, které můžete změnit přetažením
- 🌍 **26 cílových jazyků** s více hlasy na jazyk
- 🌐 **UI ve 26 jazycích** - samotné rozhraní se přizpůsobí vašemu jazyku
- 🎬 **Podpora YouTube a URL** - vložte jakýkoli odkaz na YouTube a překládejte přímo (využívá yt-dlp)
- ▶️ **Integrovaný přehrávač videa** (libmpv/mpv) - barevně odlišené ovládání přehrávání, seznam skladeb, porovnání původního a dabovaného zvuku A/B, přepínání titulků, snímek obrazovky, celá obrazovka a otevření složky
- ⏱️ **Překlad v reálném čase** - sledujte místní soubor nebo video na vyžádání z vyřešeného odkazu s přeloženými titulky a posuvníkem zpoždění ve stylu YouTube; překladače MarianMT / Google / DeepL / Ollama. Experimentální dabing využívá Edge-TTS a druhou instanci mpv. Zpracování překrývajících se hlasů a ověření se skutečným zvukem a ve Windows stále probíhají; průběžně přibývající živé vysílání zatím není podporováno. Viz [stav implementace živého překladu](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Oddělení hlasu a hudby pomocí Demucs (zachovává hudbu na pozadí)
- 🔇 **Vypnout původní zvuk**, které je k dispozici před a během živého překladu, ztiší zvukovou stopu videa a zároveň zachová přeložený hlas slyšitelný. Vypnutím obnovíte původní zvuk; po skončení živé relace se resetuje.
- 🧠 **MarianMT** - plně místní, offline neurální překlad (Helsinki-NLP, žádné limity počtu požadavků, žádný klíč API)
- 🤖 **Překlad Ollama LLM** *(novinka ve v2.0)* - místní LLM (Qwen3, Llama, Mistral) produkující stručné překlady s podporou slotu pro přirozený hlasový dabing, autodetekce/instalace/spuštění/stažení modelu při prvním použití
- 🎙️ **Klonování hlasu** - Coqui XTTS v2 klonuje osobu, která mluví hlasem původního zvuku v cílovém jazyce (~1,8 GB model), s adaptivní rychlostí na segmenty a opakovaným pokusem o halucinace
- 👥 **identifikace mluvících lidí (diarizace)** - pyannote-audio 3.1 identifikuje více mluvících lidí; XTTS klonuje každý hlas zvlášť
- 💋 **Lip Sync** - Wav2Lip GAN synchronizuje pohyby úst s dabovaným zvukem (~416 MB model)
- 🔊 **Normalizace zvuku** - automatická normalizace hlasitosti -23 LUFS (EBU R128)
- ✏️ Editor titulků - zkontrolujte a opravte titulky před hlasovým dabingem
- 📦 Dávkové zpracování - překládejte více videí nebo adres URL najednou
- ⚡ Akcelerace GPU přes CUDA (automaticky přejde zpět na CPU)
- 📄 Volitelný export titulků `.srt`
- 🔁 **DeepL Free** překladatelský modul (volitelný - 500 000 znaků/měsíc, vyžaduje bezplatný klíč API)
- 🔧 **Automatická instalace** - chybějící balíčky Pythonu a ffmpeg se nainstalují automaticky při prvním spuštění

## Podporované jazyky

arabština, čínština, čeština, dánština, holandština, angličtina, finština, francouzština, němčina, řečtina, hindština, maďarština, indonéština, italština, japonština, korejština, norština, polština, portugalština, rumunština, ruština, španělština, švédština, turečtina, ukrajinština, vietnamština

## Hlasový katalog

Hlasový katalog Edge-TTS je definován v `LANGUAGES` v horní části `video_translator_gui.py`. Tento slovník je zdrojem pravdy pro názvy cílových jazyků, hlasové přepínače GUI a nouzový hlas CLI, když je vynechán `--voice`.

Claude/poznámky k údržbě projektu odrážejí toto umístění v `CLAUDE.md` pod **Voice Catalog Source Of Truth**, takže budoucí kódoví agenti vědí, kde aktualizovat hlasy a kam uživatele README nasměruje.

## Překladové motory

| Motor | Nastavení | Limity | Kvalita |
|--------|-------|--------|---------|
| **Google Translate** *(výchozí)* | žádný | Neoficiální škrábání - může být u velkých videí omezeno | ★★★★ |
| **MarianMT** | Žádné - stažení ~298 MB na jazykový pár při prvním použití | Žádné - po stažení zcela offline | ★★★★ |
| **DeepL Free** | Bezplatný klíč API na [deepl.com](https://www.deepl.com/pro-api) | 500 tisíc znaků/měsíc | ★★★★★ |
| **Ollama LLM** *(doporučeno pro hlasový dabing - novinka ve verzi 2.0)* | Automaticky nainstalováno při prvním použití (~1 GB Ollama + 5 GB model) | Žádné - plně místní | ★★★★★ |

> **MarianMT** používá modely [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) uložené v místní mezipaměti po prvním stažení. Vyžaduje explicitní zdrojový jazyk (automatická detekce není podporována - vyberte zdrojový jazyk ručně). Požadované balíčky Python (`sacremoses`, `sentencepiece`) se nainstalují automaticky při prvním výběru, pokud chybí.

> **Ollama LLM** *(novinka ve v2.0)* je doporučeným nástrojem pro dabing hlasu, protože vytváří překlady s vědomím cílového časového úseku. Tam, kde MarianMT překládá doslovně a produkuje italštinu / španělštinu / francouzštinu ~ o 25 % déle než angličtinu (vynucuje slyšitelnou kompresi zvuku na TTS), je LLM vybídnuta, aby udržovala každý segment stručný a přirozený pro mluvený projev, přičemž dosahuje typického poměru znaků 0,85-0,95 oproti zdroji. Výchozí model je `qwen3:8b` (5,2 GB na disku, ~6 GB VRAM); `qwen3:4b` (~3 GB) je lehčí varianta, `qwen3:14b` ta kvalitnější. Potrubí automaticky detekuje binární soubor Ollama, automaticky jej nainstaluje prostřednictvím oficiálního instalátoru při prvním použití (s vyskakovacím oknem souhlasu), spustí démona a stáhne vybraný model - není potřeba žádné ruční nastavení. Pokud něco chybí, automaticky se přepne na Google Translate.

## Klonování hlasu (XTTS v2)

Když je tato možnost povolena, aplikace extrahuje hlas mluvčího z původního videa a použije jej jako referenci ke klonování hlasu do cílového jazyka.

- Podporované jazyky: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- U zbývajících 9 jazyků se Edge-TTS používá automaticky jako záložní
- Model (~1,8 GB) stažen automaticky při prvním použití do `~/.local/share/tts/`
- **Reference filtrovaná VAD** (v1.4): 10-15 s nepřetržité řeči vybrané z původního zvuku prostřednictvím [silero-vad](https://github.com/snakers4/silero-vad) pro lepší kvalitu klonování hlasu
- **Rychlost generování** konfigurovatelná (`xtts_speed`, výchozí `1.25`): vyšší hodnoty snižují artefakty komprese zvuku po zpracování, když je přeložený text delší než zdrojový slot. Ladění přes `~/.config/videotranslatorai/config.json` nebo CLI `--xtts-speed`
- Běží na CUDA nebo CPU

## identifikace mluvících lidí (diarizace) (pyannote-audio)

Když je tato možnost povolena, aplikace identifikuje, kdo v každém segmentu mluví. V kombinaci s klonováním hlasu je hlas každého mluvčího klonován samostatně - ideální pro rozhovory, podcasty a videa pro více osob.

- Vyžaduje bezplatný [HuggingFace token](https://huggingface.co/settings/tokens) (jednorázová registrace)
- **Token uložený bezpečně** (v1.4) prostřednictvím svazku klíčů OS: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automatická migrace z předchozího úložiště JSON ve formátu prostého textu
- Po prvním stažení funguje plně offline
- Model: `pyannote/speaker-diarization-3.1`

## Lip Sync (Wav2Lip)

Když je tato možnost povolena, aplikace použije Wav2Lip GAN k synchronizaci pohybů úst subjektu s dabovaným zvukem - zdá se, že osoba mluví přeloženým jazykem.

- Model (~416 MB) a repo klonovány automaticky při prvním použití do `~/.local/share/wav2lip/`
- Běží na CUDA (doporučeno) nebo CPU
- Výrazně prodlužuje dobu zpracování
- Funguje nejlépe u videí s jedním, jasně viditelným obličejem

## Požadavky

- Python 3.10+ (instalační program Windows automaticky poskytuje verzi 3.11.9)
- Windows 10/11 (x64), Linux nebo macOS
- **Důrazně doporučujeme GPU NVIDIA** - viz tabulka GPU níže
- 20 GB volného místa na disku pro plnou instalaci (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg a všechny balíčky Pythonu se nainstalují automaticky** při prvním spuštění, pokud chybí. Není potřeba žádné ruční nastavení.

**Volitelná systémová závislost** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Když je nainstalován, používá se k natahování času se zachováním výšky tónu v pásmu kvality řízeného profilem (výchozí 1,15-1,50, až 1,65 pro tvrdý obsah), čímž se odstraní zbytkový efekt "chipmunk" na klonovaných hlasech XTTS. Potrubí běží beze změny (automatický přechod na ffmpeg `atempo`). Kvalitní profily nyní preferují extra krátké opakování překladu před extrémním zrychlením zvuku.

### podpora GPU

Pipeline využívá pět GPU akcelerovaných komponent (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). Pokrytí GPU není u různých dodavatelů jednotné:

| GPU | Windows | Linux | Poznámky |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx nebo novější, ovladač CUDA 12.4) | ✅ plné zrychlení | ✅ plné zrychlení | **Doporučeno.** Všech 5 komponent běží na GPU. |
| **AMD** (Radeon) | ⚠️ neúplné (DirectML nepodporuje XTTS a faster-whisper) | ⚠️ částečné (ROCm funguje pro Demucs/XTTS/pyannote, ale faster-whisper podporuje pouze CUDA) | Funguje, ale přepis Whisper zůstává na CPU a dominuje celkovému času. |
| **Intel Arc** | ⚠️ nezralá podpora PyTorch XPU | ⚠️ stejně | Netestováno. |
| **Žádné (pouze CPU)** | ✅ funguje | ✅ funguje | Očekávejte **10-20× pomalejší** než v reálném čase. Přepis 5minutového klipu může trvat déle než 50 minut, než se přepíše pomocí Whisper large-v3. |

**Doporučená NVIDIA VRAM:**

| VRAM | Typické grafické karty | Zkušenosti |
|------|---------------|-----------|
| 6 GB | GTX 1660, RTX 2060 | Použitelné, nelze spustit XTTS + Wav2Lip současně |
| 8 GB | RTX 3060 Ti, 4060 | Plný kanál, žádná marže |
| **12 GB+** | **RTX 3060 12GB, 4070, 4080** | **Doporučeno - pohodlné** |
| 24 GB | RTX 3090, 4090 | Volná kapacita pro velké dávky |

## Instalace

### Windows

1. Naklonujte nebo stáhněte toto úložiště
2. Klikněte pravým tlačítkem na `setup_windows.bat` → **Spustit jako správce** → nabídka zobrazí `[1] Install`
3. Instalátor automaticky:
   - Nainstaluje Python 3.11, pokud není přítomen (v rámci celého systému)
   - Nainstaluje Git for Windows, pokud není přítomen
   - Nainstaluje všechny závislosti Pythonu (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps atd.)
   - Stáhne a nainstaluje ffmpeg
   - Nainstaluje integrovaný přehrávač videa (python-mpv plus sestavení libmpv v `mpv-runtime`). Tento krok je volitelný: pokud selže, vše ostatní funguje a panel přehrávače vysvětluje, co chybí
   - Vytvoří **Public Desktop zástupce** (viditelný pro každý účet Windows na PC)

> Instalační program je **pro více uživatelů**: vše je nainstalováno v celém systému pod `%ProgramFiles%\VideoTranslatorAI` a jakýkoli uživatel Windows na počítači najde zástupce připraveného k použití. Nástroje VS C++ Build Tools **již nejsou vyžadovány** - udržovaná vidlice `coqui-tts` poskytuje předkompilované balíčky koleček Pythonu.

### Linux / macOS

```bash
# Klonujte repo
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Volitelné: nainstalujte testovaný zásobník NVIDIA CUDA 12.4 PyTorch dopředu
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Volitelné: předinstalujte všechny balíčky běhového prostředí Pythonu namísto ponechání GUI
# nainstalovat chybějící balíčky při prvním spuštění
pip install --break-system-packages -r requirements.txt

# Volitelné: integrovaný přehrávač videa (libmpv z distribuce, python-mpv z PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Volitelné: nainstalujte projekt jako upravitelný balíček Pythonu
pip install --break-system-packages --no-deps -e .

# Spustit ze zdroje
python video_translator_gui.py

# Nebo po instalaci upravitelného/balíčku
videotranslatorai
videotranslatorai --preflight
```

> Při prvním spuštění GUI detekuje všechny chybějící balíčky (faster-whisper, Demucs, Edge-TTS atd.) a automaticky je nainstaluje, přičemž výstup streamuje do okna protokolu. ffmpeg se také instaluje automaticky přes `apt-get` / `dnf` / `pacman` (Linux) nebo stahuje z GitHubu (Windows).

> V záhlaví je odznak **Hráč**. Když chybí libmpv nebo python-mpv, v levém podokně je napsáno, co chybí, a nabízí se **Instalovat přehrávač**: v Linuxu používá správce balíčků přes pkexec (pak `sudo -n`) a zobrazuje ruční příkaz, když nefunguje ani jeden; ve Windows se zeptá před stažením libmpv pro aktuálního uživatele (asi 32 MB).

### Profily požadavků

| Soubor | Účel |
|------|---------|
| `requirements.txt` | Plná, zpětně kompatibilní instalace runtime. |
| `requirements-core.txt` | Výchozí balíčky potrubí používané GUI/CLI. |
| `requirements-optional.txt` | XTTS, tokenizéry MarianMT, diarizace, VAD, klíčenka. |
| `requirements-wav2lip.txt` | Runtime Wav2Lip a zásobník detekce obličejů (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Stoh PyTorch testován s koly NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Integrovaný přehrávač videa: python-mpv (potřebuje libmpv ze systému nebo z instalačního programu Windows). |
| `requirements-dev.txt` | Odlehčené závislosti používané testy CI/jednotka. |

## Odinstalovat

### Windows

Spusťte `setup_windows.bat` (klikněte pravým tlačítkem → **Spustit jako správce**) a z nabídky vyberte `[3] Uninstall`. K dispozici jsou tři dílčí režimy odinstalace:

| Režim | Je vyžadován administrátor | Rozsah |
|------|----------------|-------|
| **[1] Úplné odinstalování - jedním kliknutím** | ✅ | Odebere složku aplikace, zástupce Public Desktop, ffmpeg z PATH počítače, mezipaměť HF modelu každého uživatele (Whisper/XTTS) a konfiguraci (`HF token`) a všechny balíčky Python AI nainstalované instalačním programem. Na konci se také zeptá (opt-in), zda má tiše odinstalovat **Python 3.11** a **Git for Windows** prostřednictvím jejich řetězců tichého odinstalování v registru. |
| **[2] Pouze aktuální uživatel** | ❌ | Odebere pouze konfiguraci VTAI běžícího uživatele, mezipaměť HF/XTTS a starší instalaci pro uživatele. **Instalaci celého systému ponechá nedotčenou**, takže ostatní účty Windows v počítači mohou aplikaci nadále používat. |
| **[3] Vlastní - podrobné** | ✅ pro systémové položky, ❌ pro uživatelské položky | Výzva Y/N pro každou kategorii: složka aplikace, zástupce, systémová proměnná PATH, starší instalace jednotlivých uživatelů, jejich konfigurace a mezipaměti, poté skupiny balíčků Pythonu (TTS, PyTorch, Whisper+ctranslate2, Demucs, závislosti Wav2Lip, pyannote a pomocné nástroje pipeline) a nakonec volitelně Python 3.11 a Git. |

**Nikdy se automaticky neodstraňuje:** Nástroje pro sestavení Visual Studio C++ (pokud existují ze starších běhů). Chcete-li je v případě potřeby ručně odebrat, použijte *Aplikace a funkce* v Nastavení systému Windows.

### Linux / macOS

Žádný vyhrazený odinstalační program - odstraňte ručně:

```bash
# Balíčky Pythonu nainstalované automatickým instalačním programem GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Mezipaměti uživatelských dat a modelů
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (témata, pořadí panelů, nastavení)
rm -f  ~/.videotranslatorai_config.json     # starší konfigurace verzí <= 1.9, pokud existuje
```

## Využití

### Diagnostika

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Spouští diagnostiku místního prostředí bez spuštění překladu nebo instalace čehokoli. `--preflight-lipsync` zachází s balíčky obličejů Wav2Lip podle potřeby, což je užitečné před povolením **Synchronizace rtů**. GUI zobrazí stejnou základní kontrolu z tlačítka **Diagnostika** na panelu protokolu. `--preflight-player` zpracovává integrovaný videopřehrávač (python-mpv a načítatelný libmpv) podle potřeby. `python -m videotranslator.libmpv_runtime check` testuje samotný libmpv (výstup 0 připraven, 2 nedostupné).

### GUI

```bash
python video_translator_gui.py
```

**Rozvržení:** nastavení dávkového překladu jsou zobrazena ve sloupci napravo jako hromada panelů nastavení: **Vstup**, **Překlad**, **Profil pracovního postupu**, **Start** a skládací pokročilé sekce (model, překladový modul, zvuk, klonování hlasu, synchronizace rtů, diarizace, možnosti, klíčová slova). Velká oblast vlevo je **integrovaný videopřehrávač** (přenos, seznam skladeb, A/B originál vs. dabovaný zvuk, titulky, snímek, celá obrazovka) s lištou **překlad v reálném čase** pod ním. Přetažením karty za její název nebo za **≡** úchyt ji posunete ve sloupci nahoru nebo dolů; objednávka je uložena (`ui_panel_order`) a obnovena při příštím spuštění. Panel protokolu ve spodní části lze skrýt pomocí **Skrýt protokol**. Při spuštění se okno otevře se středem na aktuálním monitoru (ten pod ukazatelem) a maximalizované, takže se chová dobře v nastavení s více monitory.

**Ovládací prvky přehrávače videa:** Ikony používají konzistentní funkční barvy v každém motivu, nezávisle na zvolené zvýrazňující barvě:

| Ovládání | Barva |
|---------|--------|
| Přehrát video | Zelená |
| Pozastavit (nahrazuje přehrávání během přehrávání) | Amber |
| Zastavit přehrávání | Korálově červená |
| Předchozí / zpět 10 s / vpřed 10 s / další | Modrá |
| Snímek | Fialová |
| Otevřete složku | Zlato |

Vznášení přidá jemné tónované pozadí. Nedostupné ovládací prvky jsou neutrální; navigace v seznamu skladeb zůstane použitelná i po zastavení. Popisky nástrojů a indikátory zaměření klávesnice zůstávají k dispozici, takže barva není jediným způsobem, jak identifikovat akce.

**Z místních souborů:**
1. Kliknutím na **Přidat** vyberte jeden nebo více souborů videa
2. Vyberte zdrojový a cílový jazyk
3. Otevřete sekci **Model** a vyberte model Whisper (`small` představuje dobrý poměr rychlosti/přesnosti)
4. Vyberte hlas a v případě potřeby upravte rychlost TTS
5. *(Volitelné)* V **Překladovém modulu** vyberte **Google** (výchozí), **MarianMT** (místní/offline), **DeepL Free** nebo **Ollama LLM** (místní, doporučeno pro hlasový dabing)
6. *(Volitelné)* Povolit **Klonování hlasu** (XTTS v2) a/nebo **identifikace mluvících lidí (diarizace)**
7. *(Volitelné)* Povolit **Synchronizaci rtů** (Wav2Lip)
8. Klikněte na **Spustit překlad**

**Z YouTube (nebo jakéhokoli podporovaného webu):**
1. Vložte jednu nebo více adres URL do pole **URL** (jedna na řádek)
2. Nakonfigurujte jazyk, model a hlas jako obvykle
3. Klikněte na **⬇ Stáhnout a přeložit**

> yt-dlp podporuje YouTube, Vimeo, Twitter/X, TikTok a [1000+ dalších webů](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Oznámení o spravedlivém použití:** Stahování videí přes yt-dlp je platformami jako YouTube považováno za automatický přístup a může porušovat jejich smluvní podmínky. Silné nebo opakované používání ze stejné IP adresy může mít za následek dočasné blokování (chyby HTTP 429 / požadované přihlášení). Pokud dojde k selhání stahování, použijte VPN nebo otočte svou IP. Tento nástroj je určen pouze pro osobní, nekomerční použití. Redistribuce přeloženého obsahu může porušovat autorská práva - vždy respektujte práva původního tvůrce.

### Překlad v reálném čase (titulky a experimentální dabing)

Sledujte místní soubor nebo vyřešený odkaz na video na vyžádání s přeloženými titulky a volitelným mluveným překladem. Použijte lištu pod přehrávačem:

**Z odkazu:**

1. Vložte odkaz do pole **URL**
2. Nastavte zdrojový a cílový jazyk, vyberte hlas a upravte posuvník **Zpoždění**
3. Vyberte **Dabovaný hlas** a/nebo **Titulky**
4. Chcete-li slyšet pouze přeložený hlas, před zahájením vyberte **Vypnout původní zvuk** (v italštině: **Silenzia originale**, vedle zaškrtávacího políčka titulků)
5. Klikněte na **Přeložit v reálném čase** - odkaz je vyřešen a překlad se spustí

**Z načteného souboru:** načtěte video do přehrávače (Vstup -> Přidat, poté jej vyberte), ponechte pole URL prázdné, zvolte stejná nastavení živého vysílání a klikněte na **Přeložit v reálném čase**. Adresa URL má prioritu, pokud pole není prázdné.

- **Engine:** MarianMT (offline, výchozí), Google, DeepL nebo Ollama. Rozpoznávání řeči (Whisper) běží lokálně. Offline modely vyžadují první stažení.
- **Dabování hlasu:** experimentální přehrávání řeči Edge-TTS prostřednictvím druhé instance mpv. Vyžaduje přístup k internetu a je oddělený od dávkového klonování hlasu.
- **Vypnout původní zvuk:** k dispozici před zahájením i během překladu. Ztiší celý původní soundtrack včetně hudby a efektů, ale přeložený hlas ponechá slyšitelný. Neizoluje osobu, která mluví v původním zvuku. Vypnutím obnovíte zvukovou stopu; po skončení živé relace se resetuje. Tlačítko reproduktoru přehrávače je obecné ztlumení, nikoli toto nezávislé ovládání.
- **Pozastavit a vyhledat:** ovládací prvky přehrávače videa jsou připojeny k živé relaci; end-to-end audio synchronizace stále vyžaduje testy akceptace specifické pro platformu.
- **Aktuální limity:** Zpracování překrývání/zatmívání klipů, kalibrace časování zvuku a akceptace Windows zůstávají otevřené. Rostoucí živé vysílání zatím není podporováno; označení živého režimu neznamená podporu pro přijímání vysílání, jak roste. Viz [stav implementace a zbývající práce](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Pro uložené dabované video použijte místo náhledu v reálném čase **Stáhnout a přeložit** / **Zahájit překlad**.

### Bloky překladového enginu a VPN

Mohou nastat dva různé bloky s různými opravami:

| Blokovat | Symptom | Opravit |
|-------|---------|-----|
| **Stáhnout** (yt-dlp) | „Přihlaste se a potvrďte, že nejste robot“, HTTP 429 | **VPN** / otočte IP nebo buďte přihlášeni na YouTube ve svém prohlížeči (soubory cookie se načítají automaticky) |
| **Překlad** (bezplatný koncový bod Google) | "Google Translate nelze přeložit... četnost požadavků omezena/blokována" | Použijte **MarianMT** (offline) nebo **Ollama** (místní) - žádný limit počtu požadavků. Pomáhá také VPN. Dávkový tok nyní **spadá zpět do MarianMT automaticky**, když je Google zablokován. |

### Témata a vzhled

Kliknutím na ikonu ozubeného kola v záhlaví otevřete **Nastavení**:

- **Motiv**: Automaticky (sleduje tmavý/světlý režim OS), Graphite (výchozí), Slate, Light, Neon.
- **Barva zvýraznění**: výchozí pro motiv nebo modrá, modrozelená, fialová, zelená, jantarová, růžová.
- **Velikost textu**: malá, normální, velká, extra velká.
- **Jazyk rozhraní**: 26 jazyků.

Změny se projeví okamžitě, bez restartu, a uloží se do konfiguračního souboru (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Restore defaults** obnoví motiv Graphite, výchozí akcent, normální velikost textu a výchozí pořadí panelů nastavení.

### Příkazový řádek

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Všechny možnosti:**

| Možnost CLI | Popis | Výchozí |
|------|-------------|---------|
| `--lang-source` | Zdrojový jazyk (`auto` pro automatickou detekci) | `auto` |
| `--lang-target` | Kód cílového jazyka (např. `it`, `fr`, `de`) | `it` |
| `--voice` | Název hlasu Edge-TTS | auto |
| `--model` | Model Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Nastavení rychlosti TTS (např. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` nebo `deepl` | `google` |
| `--deepl-key` | Klíč API DeepL Free | - |
| `--diarize` | Povolit identifikaci mluvících lidí (diarizace) (pyannote) | - |
| `--hf-token` | Token HuggingFace pro diarizování | - |
| `--lipsync` | Po hlasovém dabingu použijte synchronizaci rtů Wav2Lip | - |
| `--subs-only` | Generovat pouze `.srt`, přeskočit hlasový dabing | - |
| `--no-subs` | Přeskočte generaci `.srt` | - |
| `--no-demucs` | Přeskočte oddělení hlasu a hudby | - |
| `--output` / `-o` | Cesta k výstupnímu souboru | auto |
| `--output-dir` | Složka pro přeložené soubory (jedno místo, Windows a Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Zpracujte více souborů | - |

### integrační testy s reálnými modely

Výchozí testovací sada se vyhýbá stahování skutečných modelů a dlouhé práci s GPU. Chcete-li spustit empirické kontroly nainstalovaného místního zásobníku:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Tyto kontroly ověřují skutečné importy Wav2Lip, dostupnost Torch CUDA, dostupnost démona Ollama a faster-Whisper na syntetickou řeč. Záměrně selžou nebo přeskakují, když místní ovladač/démon/stav modelu není připraven.

**Příklady:**

```bash
# Přeložte italské video do angličtiny s místním MarianMT
# (stáhne ~298 MB model při prvním použití, poté plně offline)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Překlad s klonováním hlasu + identifikace mluvících lidí (diarizace)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Překládejte pomocí synchronizace rtů
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Pouze titulky (bez dabingu)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Modely Whisper

| Model | Velikost | Rychlost | Přesnost |
|-------|------|-------|----------|
| tiny | 75 MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465 MB | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3 GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` je destilovaná verze `large-v3` (4 vrstvy dekodéru oproti 32) - téměř velká kvalita při rychlosti zhruba `medium`. Doporučená výchozí hodnota na moderním GPU, když záleží na rychlosti přepisu; pokles kvality u vícejazyčného materiálu je malý.

> Modely se stahují automaticky při prvním použití.

## Samostatný modul CLI

Modulární balíček odhaluje čtyři uživatelské nástroje, které lze vyvolat přímo bez spouštění celého kanálu:

```bash
# Pre-flight video pro přítomnost obličeje (Wav2Lip by přeskočit, pokud chybí).
python3 -m videotranslator.face_detector path/to/video.mp4
# východ 0 = přítomný obličej, východ 1 = žádný obličej

# Analyzujte soubor *_metrics.csv vytvořený společností build_dubbed_track.
# Hlásí P50/P75/P90/P95 z pre_stretch_ratio, porucha pásma slyšitelnosti,
# rozšíří využití motoru a prvních N nejhorších odlehlých hodnot s jejich cílovým textem.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Dezinfikuje text pro TTS (přepíše dvojtečky, středníky, elipsy, pomlčky).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Odhadněte obtížnost dabingu hlasu ze souboru segmentů .srt nebo .json PŘED spuštěním TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Každý nástroj má `-h`/`--help` pro plné možnosti. Jsou soběstačné a opakovaně používají stejné moduly, na které se spoléhá potrubí hlasového dabingu, takže jejich výstup zůstává konzistentní s běhovým prostředím.

## Licence

MIT

### Komponenty třetích stran

Kód úložiště je MIT. Instalační programy stahují komponenty níže ze svých vlastních zdrojů v době instalace; projekt je nepřerozděluje.

- **libmpv** (https://github.com/mpv-player/mpv), motor integrovaného přehrávače videa. Windows: nejprve je vyzkoušeno sestavení LGPL od zhongfly (https://github.com/zhongfly/mpv-winbuild); záložní GPL sestavení od shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/). `mpv-runtime\BUILD.txt` zaznamenává zdroj, verzi licence a potvrzení mpv a text licence je umístěn vedle knihovny DLL. Linux: distribuční balíček (`libmpv2`, `libmpv1`, `mpv-libs` nebo `mpv`).
- **FFmpeg** uvnitř libmpv (LGPL nebo GPL, po sestavení libmpv).
- **python-mpv** (`mpv` na PyPI), GPLv2+ nebo LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), používaný instalačním programem Windows k extrahování libmpv a následně odstraněn.
- **Zavaděč Vulkan** (Khronos, MIT a Apache-2.0), stažen do systému Windows pouze v případě, že chybí `vulkan-1.dll`.
- **edge-tts** (LGPLv3), používaný kanálem dabingu.
- **Modely MarianMT** (Helsinki-NLP), stažené z Hugging Face Hub při prvním použití pod vlastními licencemi (Apache-2.0 pro modely `opus-mt`, CC-BY-4.0 pro `opus-mt-tc-big`).
