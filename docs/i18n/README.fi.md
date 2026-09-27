# 🎬 Video Translator AI

[Englanti](../../README.md) | [Kaikki käännökset](README.md)

**Lue tämä sivu:** [Bahasa Indonesia](README.id.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Nederlands](README.nl.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Suomi](README.fi.md) · [Svenska](README.sv.md) · [Tiếng Việt](README.vi.md) · [Türkçe](README.tr.md) · [Ελληνικά](README.el.md) · [Русский](README.ru.md) · [Українська](README.uk.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Tekoälyllä toimiva videoäänen jälkiäänitystyökalu, joka litteroi, kääntää ja uudelleenäänittää videot automaattisesti 26 kielelle paikallisilla käsittelyvaihtoehdoilla eikä oletuksena vaadi API-avaimia. Whisper puheentunnistus toimii paikallisesti; Edge-TTS, Google Translate ja DeepL vaativat Internet-yhteyden. Valinnaiset ominaisuudet (DeepL, puhuvien ihmisten tunnistaminen (diarisaatio)) voivat vaatia API-avaimen tai pääsytunnuksen.

> **v2.0** - modulaarinen paketti, paikallinen Ollama-käännös, laatuprofiilien orkestrointi, asennettavat Python-metatiedot ja integraatiotestit oikeilla malleilla. Katso täydellinen luettelo muutoksista kohdasta [GitHub Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) ja toimitushistoria.

## Miten se toimii

1. **Transkriptio** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) litteroi äänen (GPU-kiihdytetty)
2. **Äänen ja musiikin erottaminen** - [Demucs](https://github.com/facebookresearch/demucs) eristää laulun taustamusiikista
3. **Käännös** - MarianMT (paikallinen, offline), Google Translate, DeepL Free tai **Ollama LLM** (Qwen3, paikkatietoiset tiiviit käännökset)
4. **puhuvien ihmisten tunnistus (diarisaatio)** *(valinnainen)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) tunnistaa, kuka puhuu kussakin segmentissä
5. **äänen jälkiäänitys** - [Edge-TTS](https://github.com/rany2/edge-tts) (400+ ääntä) tai [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (äänen kloonaus, jokaiselle keskustelun puhujalle)
6. **Mixing** - dubattu ääni sekoitettuna takaisin alkuperäiseen taustamusiikkiin
7. **Normalointi** - lopullinen ääni normalisoitu -23 LUFS:ään (EBU R128 -lähetysstandardi)
8. **Lip Sync** *(valinnainen)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synkronoi suun liikkeet kopioituun ääneen

## Ominaisuudet

- 🖥️ Teemallinen GUI (Tkinter) - komentoriviä ei tarvita; Graphite, Slate, Light ja Neon teemat, korostusvärit, tekstin koko ja asetuspaneelit, joita voit järjestää uudelleen vetämällä
- 🕹️ **Teemat** - leikkisät tyylit asetuksista: Dex ja Handheld muistuttavat taskukonsolia (pikselifontti, paksut kehykset), CRT ja CRT Amber 80-luvun fosforinäyttöä, ja videossakin on kaarevuus ja juovat
- 🔊 **Kuuntele ennen valintaa** - äänen vieressä oleva kaiutinkuvake toistaa esimerkkilauseen kohdekielellä (Edge-TTS) tai ElevenLabs-äänen maksuttoman näytteen
- 🌍 **26 kohdekieltä** useilla äänillä kielellä
- 🌐 **Käyttöliittymä 26 kielellä** - käyttöliittymä itse mukautuu kielellesi
- 🎬 **YouTube- ja URL-tuki** - liitä mikä tahansa YouTube-linkki ja käännä suoraan (yt-dlp:n avulla)
- ▶️ **Integroitu videosoitin** (libmpv/mpv) - värikoodatut siirtosäätimet, soittolista, alkuperäinen A/B vs. jälkiäänitetty ääni, tekstityksen vaihto, tilannekuva, koko näyttö, avoin kansio
- ⏱️ **Reaaliaikainen käännös** - katso paikallista tiedostoa tai tilausvideon linkkiä käännetyillä tekstityksillä ja viiveen liukusäätimellä; moottorit MarianMT / Google / DeepL / Ollama. Jälkiäänitys käyttää Edge-TTS:ää tai valinnaisesti ElevenLabsin ääniä toisen mpv-instanssin kautta; päällekkäiset lauseet odottavat, nopeutuvat tai häivytetään. Käynnissä olevia suoria lähetyksiä ei vielä tueta.
- 🎵 Äänen/musiikin erotus Demucsilla (säilyttää taustamusiikin)
- 🔇 **Mykistä alkuperäinen ääni**, joka on käytettävissä ennen suoraa käännöstä ja sen aikana, hiljentää videon ääniraidan ja pitää käännetyn äänen kuultavana. Kytke se pois päältä palauttaaksesi alkuperäisen äänen; se nollautuu, kun live-istunto päättyy.
- 🧠 **MarianMT** - täysin paikallinen, offline-hermokäännös (Helsinki-NLP, ei pyyntöjen määrärajoja, ei API-avainta)
- 🤖 **Ollama LLM-käännös** *(uusi versiossa 2.0)* - paikallinen LLM (Qwen3, Llama, Mistral), joka tuottaa paikkatietoisia tiiviitä käännöksiä luonnolliseen äänen jälkiäänitykseen, tunnistaa/asentaa/käynnistää/vetää mallin automaattisesti ensimmäisellä käyttökerralla
- 🎙️ **Äänen kloonaus** - Coqui XTTS v2 kloonaa henkilön, joka puhuu alkuperäisen äänen äänellä kohdekielellä (~1,8 Gt malli), segmenttikohtaisella mukautumisnopeudella ja usean siemenen uudelleenyrityksellä hallusinaatioissa
- 👥 **puhuvien ihmisten tunnistaminen (diarisaatio)** - pyannote-audio 3.1 tunnistaa useita puhuvia ihmisiä; XTTS kloonaa jokaisen äänen erikseen
- 💋 **Lip Sync** - Wav2Lip GAN synkronoi suun liikkeet kopioituun ääneen (~416 MB malli)
- 🔊 **Äänen normalisointi** - automaattinen -23 LUFS äänenvoimakkuuden normalisointi (EBU R128)
- ✏️ Tekstityseditori - tarkista ja korjaa tekstitykset ennen äänen kopiointia
- 📦 Eräkäsittely - käännä useita videoita tai URL-osoitteita kerralla
- ⚡ GPU-kiihdytys CUDA:n kautta (palautuu automaattisesti prosessoriin)
- 📄 Valinnainen `.srt` tekstityksen vienti
- 🔁 **DeepL Free** käännösmoottori (valinnainen - 500 000 merkkiä kuukaudessa, vaatii ilmaisen API-avaimen)
- 🔧 **Automaattinen asennus** - puuttuvat Python-paketit ja ffmpeg asennetaan automaattisesti ensimmäisen käynnistyksen yhteydessä
- 🧮 **Mallit tälle tietokoneelle** - tunnistaa suorittimen, RAM-muistin, näytönohjaimen, VRAM-muistin ja vapaan levytilan, suosittelee puheentunnistuksen, käännöksen ja äänen malleja nopeuden, tasapainon tai laadun mukaan, lataa ja tarkistaa Whisper-mallit ja mittaa ne omalla videollasi
- 🗣️ **ElevenLabsin äänet** *(valinnainen, verkossa, maksullinen)* - luonnollisia monikielisiä ääniä live-jälkiäänitykseen omalla API-avaimellasi; jos avain tai kiintiö pettää, Edge-TTS jatkaa
- 🧬 **Äänen kloonaus Voiceboxilla** *(valinnainen)* - kloonaa puhujan äänen erillisen paikallisen [Voicebox](https://github.com/jamiepine/voicebox)-palvelimen kautta; jos se ei ole käynnissä, video käyttää Edge-TTS:ää

## Tuetut kielet

arabia, kiina, tšekki, tanska, hollanti, englanti, suomi, ranska, saksa, kreikka, hindi, unkari, indonesia, italia, japani, korea, norja, puola, portugali, romania, venäjä, espanja, ruotsi, turkki, ukraina, vietnami

## Ääniluettelo

Edge-TTS-äänikatalogi on määritetty `LANGUAGES`:ssä lähellä `video_translator_gui.py`:n yläosaa. Tämä sanakirja on totuuden lähde kohdekielten nimille, GUI-äänivalintapainikkeille ja CLI-varaäänelle, kun `--voice` jätetään pois.

Claude/projektin ylläpitohuomautukset heijastavat tämän sijainnin `CLAUDE.md`:ssä kohdassa **Voice Catalog Source Of Truth**, joten tulevat koodiagentit tietävät, mihin ääniä päivitetään ja mihin README osoittaa käyttäjiä.

## Käännösmoottorit

| Moottori | Asennus | Rajoitukset | Laatu |
|--------|-------|--------|---------|
| **Google Translate** *(oletus)* | Ei mitään | Epävirallinen kaapiminen - voidaan rajoittaa suurissa videoissa | ★★★★ |
| **MarianMT** | Ei mitään - lataa ~298 Mt kieliparia kohden ensimmäisellä käyttökerralla | Ei mitään - täysin offline-tilassa latauksen jälkeen | ★★★★ |
| **DeepL Free** | Ilmainen API-avain osoitteessa [deepl.com](https://www.deepl.com/pro-api) | 500k merkkiä/kk | ★★★★★ |
| **Ollama LLM** *(suositellaan äänen jälkiäänitykseen - uusi versiossa 2.0)* | Automaattinen asennus ensimmäisellä käyttökerralla (~1 Gt Ollama + 5 Gt malli) | Ei mitään - täysin paikallinen | ★★★★★ |

> **MarianMT** käyttää [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP) malleja, jotka tallennetaan paikallisesti välimuistiin ensimmäisen latauksen jälkeen. Edellyttää nimenomaista lähdekieltä (automaattista tunnistusta ei tueta - valitse lähdekieli manuaalisesti). Tarvittavat Python-paketit (`sacremoses`, `sentencepiece`) asennetaan automaattisesti ensimmäisen valinnan yhteydessä, jos ne puuttuvat.

> **Ollama LLM** *(uusi v2.0:ssa)* on suositeltu äänen jälkiäänityskone, koska se tuottaa käännöksiä tietoisena kohdeaikavälistä. Kun MarianMT kääntää kirjaimellisesti ja tuottaa italiaa/espanjaa/ranskaa noin 25 % pidempään kuin englantia (pakottaen äänen pakkaamisen TTS:ään), LLM:tä kehotetaan pitämään jokainen segmentti tiiviinä ja luonnollisena puhuttaessa, jolloin saavutetaan tyypillinen 0,85-0,95:n suhde lähteeseen. Oletusmalli on `qwen3:8b` (5,2 Gt levyllä, ~6 Gt VRAM); `qwen3:4b` (~3 Gt) on kevyt vaihtoehto, `qwen3:14b` laadukkaampi vaihtoehto. Liukulinja tunnistaa Ollama-binaarin automaattisesti, asentaa sen automaattisesti virallisen asennusohjelman kautta ensimmäisellä käyttökerralla (suostumuksella), käynnistää demonin ja vetää valitun mallin - manuaalista asennusta ei tarvita. Vaihtaa automaattisesti malliin Google Translate, jos jotain puuttuu.

## Äänen kloonaus (XTTS v2)

Kun tämä on käytössä, sovellus poimii puhujan äänen alkuperäisestä videosta ja käyttää sitä viitteenä äänen kloonaamiseen kohdekielellä.

- Tuetut kielet: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Muilla 9 kielellä Edge-TTS:ää käytetään automaattisesti varavaihtoehtona
- Malli (~1,8 Gt) latautuu automaattisesti ensimmäisellä käyttökerralla laitteeseen `~/.local/share/tts/`
- **VAD-suodatettu viite** (v1.4): 10-15 s jatkuvaa puhetta valittuna alkuperäisestä äänestä [silero-vad](https://github.com/snakers4/silero-vad):n kautta äänen kloonauksen laadun parantamiseksi
- **Sukupolvinopeus** konfiguroitavissa (`xtts_speed`, oletus `1.25`): korkeammat arvot vähentävät jälkikäsittelyn äänenpakkausartefakteja, kun käännetty teksti on pidempi kuin lähdepaikka. Viritä `~/.config/videotranslatorai/config.json` tai CLI `--xtts-speed` kautta
- Toimii CUDA:lla tai CPU:lla

## puhuvien ihmisten tunnistaminen (diarisaatio) (pyannote-audio)

Kun tämä on käytössä, sovellus tunnistaa, kuka puhuu kussakin segmentissä. Yhdessä Voice Cloningin kanssa jokaisen puhujan ääni kloonataan erikseen - ihanteellinen haastatteluihin, podcasteihin ja monen henkilön videoihin.

- Vaatii ilmaisen [HuggingFace-tunnuksen](https://huggingface.co/settings/tokens) (kertaluonteinen rekisteröinti)
- **Token tallennetaan turvallisesti** (v1.4) käyttöjärjestelmän avainrenkaan kautta: Windows Credential Manager, macOS Keychain, Linux Secret Service. Automaattinen siirto aiemmasta tavallisesta JSON-tallennustilasta
- Ensimmäisen latauksen jälkeen toimii täysin offline-tilassa
- Malli: `pyannote/speaker-diarization-3.1`

## Huulten synkronointi (Wav2Lip)

Kun tämä on käytössä, sovellus käyttää Wav2Lip GAN:ia synkronoimaan kohteen suun liikkeet jälkiäänitetyn äänen kanssa - henkilö näyttää puhuvan käännettyä kieltä.

- Malli (~416 MB) ja repo kloonattu automaattisesti ensimmäisellä käyttökerralla `~/.local/share/wav2lip/`
- Toimii CUDA:lla (suositus) tai CPU:lla
- Lisää käsittelyaikaa merkittävästi
- Toimii parhaiten videoissa, joissa on yksi, selvästi näkyvä kasvo

## Mallit tälle tietokoneelle

Lisäasetukset > Malli > **Mallit tälle tietokoneelle** avaa ikkunan, joka lukee laitteiston (suoritin, RAM, näytönohjain ja käytettävä VRAM, vapaa levytila) muuttamatta mitään ja suosittelee mallin jokaiseen vaiheeseen: puheentunnistus tiedostoille ja livenä, käännös ja ääni.

- Valitse **Nopeus**, **Tasapainoinen** tai **Laatu**: jokainen suositus kertoo perusteensa.
- Kaikki muut vaihtoehdot ovat yhä valittavissa ja arvioitu tälle koneelle: mahtuu, tiukka, liian suuri, levytila ei riitä tai verkkopalvelu.
- **Lataa** hakee puuttuvan Whisper-mallin edistymisen ja Peruuta-painikkeen kera ja tarkistaa jokaisen tiedoston Hugging Facen tarkistussummilla; mitään ei ladata ennen painallusta.
- **Suorituskykytesti** mittaa valitun mallin ladatulla videolla (lataus, ensimmäinen lause, nopeus); ääni ei koskaan poistu koneelta.
- **Käytä** ottaa mallit käyttöön; **Palauta edellinen** tuo aiemman valinnan takaisin. NVIDIA-näytönohjaimia käytetään CUDAn kautta; AMD- (ROCm) ja Apple-näytönohjaimet näytetään, mutta niissä puhemallit toimivat suorittimella.

## Voicebox (äänen kloonaus paikallisella palvelimella)

[Voicebox](https://github.com/jamiepine/voicebox) (MIT) on erillinen ääniä kloonaava ohjelma. Asenna ja käynnistä se itse; tämä sovellus kutsuu vain sen paikallista API:a eikä koskaan asenna sitä.

- Lisäasetukset > Äänen kloonaus > **Voicebox**: aseta osoite (oletus `http://127.0.0.1:17493`), moottori (oletuksena `chatterbox`) ja paina **Tarkista**.
- Jokaiselle videolle kloonataan väliaikainen ääni puhujan puhtaasta näytteestä (yksi puhujaa kohden puhujien erottelulla), ja se poistetaan lopuksi.
- Vain tämän koneen osoite hyväksytään, koska Voiceboxin API:ssa ei ole todennusta.
- Jos Voicebox ei vastaa tai ei tue kohdekieltä, video jälkiäänitetään Edge-TTS:llä.

## Vaatimukset

- Python 3.10+ (Windowsin asennusohjelma 3.11.9 automaattisesti)
- Windows 10/11 (x64), Linux tai macOS
- **NVIDIA GPU erittäin suositeltavaa** - katso GPU-taulukko alla
- 20 Gt vapaata levytilaa täydelle asennukselle (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg ja kaikki Python-paketit asennetaan automaattisesti** ensimmäisen käynnistyksen yhteydessä, jos ne puuttuvat. Ei vaadi manuaalista asetusta.

**Valinnainen järjestelmäriippuvuus** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Asennettaessa sitä käytetään sävelkorkeuden säilyttämiseen ajan venytykseen profiiliohjatulla laatukaistalla (oletusarvo 1,15-1,50, jopa 1,65 kovalle sisällölle), mikä poistaa jäljelle jääneen "orava"-efektin kloonatuista XTTS-äänistä. Putkilinja toimii ennallaan ilman sitä (automaattinen palautus ffmpeg `atempo`:ään). Laatuprofiilit suosivat nyt ylimääräisiä lyhyitä käännösten uudelleenyrityksiä äärimmäisen äänen nopeutumisen sijaan.

### GPU-tuki

Putkilinjassa käytetään viittä GPU-kiihdytettyä komponenttia (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). GPU-kattavuus ei ole yhtenäinen eri toimittajilla:

| GPU | Windows | Linux | Huomautuksia |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx tai uudempi, CUDA 12.4 -ohjain) | ✅ täysi kiihtyvyys | ✅ täysi kiihtyvyys | **Suositus.** Kaikki 5 komponenttia toimivat GPU:lla. |
| **AMD** (Radeon) | ⚠️ epätäydellinen (DirectML ei tue XTTS:ää ja faster-whisper:tä) | ⚠️ osittainen (ROCm toimii Demucsissa/XTTS:ssä/pyannotessa, mutta faster-whisper tukee vain CUDA:ta) | Toimii, mutta Whisper-transkriptio pysyy CPU:ssa ja hallitsee kokonaisaikaa. |
| **Intel Arc** | ⚠️ Epäkypsä PyTorch XPU -tuki | ⚠️ sama | Ei testattu. |
| **Ei mitään (vain CPU)** | ✅ toimii | ✅ toimii | Odotettavissa **10-20x hitaampi** kuin reaaliaikainen. 5 minuutin leikkeen litterointi Whisper large-v3:lla voi kestää yli 50 minuuttia. |

**Suositeltu NVIDIA VRAM:**

| VRAM | Tyypilliset näytönohjaimet | Kokemus |
|------|---------------|-----------|
| 6 Gt | GTX 1660, RTX 2060 | Käyttökelpoinen, ei voi ajaa XTTS + Wav2Lip samanaikaisesti |
| 8 Gt | RTX 3060 Ti, 4060 | Täysi putkisto, ei marginaalia |
| **12 GB+** | **RTX 3060 12 Gt, 4070, 4080** | **Suositus - mukava** |
| 24 Gt | RTX 3090, 4090 | Varakapasiteetti suurille erille |

## Asennus

### Windows

1. Kloonaa tai lataa tämä arkisto
2. Napsauta hiiren kakkospainikkeella `setup_windows.bat` → **Suorita järjestelmänvalvojana** → valikko näyttää `[1] Install`
3. Asennusohjelma automaattisesti:
   - Asentaa Python 3.11:n, jos sitä ei ole (järjestelmänlaajuinen)
   - Asentaa Git for Windows:n, jos sitä ei ole
   - Asentaa kaikki Python-riippuvuudet (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps jne.)
   - Lataa ja asentaa ffmpeg
   - Asentaa integroidun videosoittimen (python-mpv plus libmpv-koontiversio `mpv-runtime`:ssä). Vaihe on valinnainen: jos se epäonnistuu, kaikki muu toimii ja soitinpaneeli selittää, mitä puuttuu
   - Luo **julkisen työpöydän pikakuvakkeen** (näkyy kaikille PC:n Windows-tileille)

> Asennusohjelma on **monen käyttäjän**: kaikki on asennettu koko järjestelmään `%ProgramFiles%\VideoTranslatorAI`:n alla ja jokainen koneen Windows-käyttäjä löytää pikakuvakkeen valmiina käyttöön. VS C++ Build Tools -työkaluja **ei enää tarvita** - huollettu `coqui-tts`-haarukka tarjoaa esikäännetyt Python-pyöräpaketit.

### Linux / macOS

```bash
# Kloonaa repo
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Valinnainen: asenna testattu NVIDIA CUDA 12.4 PyTorch -pino eteen
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Valinnainen: esiasenna kaikki Python-ajonaikaiset paketit graafisen käyttöliittymän sallimisen sijaan
# asenna puuttuvat paketit ensimmäisellä kerralla
pip install --break-system-packages -r requirements.txt

# Valinnainen: integroitu videosoitin (libmpv jakelusta, python-mpv PyPI:stä)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Valinnainen: asenna projekti muokattavana Python-paketina
pip install --break-system-packages --no-deps -e .

# Käynnistä lähteestä
python video_translator_gui.py

# Tai muokattavan/paketin asennuksen jälkeen
videotranslatorai
videotranslatorai --preflight
```

> Ensimmäisellä käynnistyksellä graafinen käyttöliittymä havaitsee puuttuvat paketit (faster-whisper, Demucs, Edge-TTS jne.) ja asentaa ne automaattisesti, suoratoistaen tulosteen loki-ikkunaan. ffmpeg asennetaan myös automaattisesti `apt-get` / `dnf` / `pacman` (Linux) kautta tai ladataan GitHubista (Windows).

> Otsikossa näkyy **Pelaaja**-merkki. Kun libmpv tai python-mpv puuttuu, vasen ruutu kertoo, mitä puuttuu ja tarjoaa **Install player**: Linuxissa se käyttää paketinhallintaa pkexecin kautta (siis `sudo -n`) ja näyttää manuaalisen komennon, kun kumpikaan ei toimi; Windowsissa se kysyy ennen libmpv:n lataamista nykyiselle käyttäjälle (noin 32 Mt).

### Vaatimusprofiilit

| Tiedosto | Tarkoitus |
|------|---------|
| `requirements.txt` | Täysi, taaksepäin yhteensopiva suoritusaikainen asennus. |
| `requirements-core.txt` | GUI/CLI:n käyttämät oletusputket. |
| `requirements-optional.txt` | XTTS, MarianMT tokenisers, diarisointi, VAD, avaimenperä. |
| `requirements-wav2lip.txt` | Wav2Lip-ajoaika ja kasvojentunnistuspino (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | PyTorch-pino testattu NVIDIA CUDA 12.4 -pyörillä. |
| `requirements-player.txt` | Integroitu videosoitin: python-mpv (vaatii libmpv:n järjestelmästä tai Windowsin asennusohjelmasta). |
| `requirements-dev.txt` | Kevyet riippuvuudet, joita käytetään CI/yksikkötesteissä. |

## Poista asennus

### Windows

Suorita `setup_windows.bat` (napsauta hiiren kakkospainikkeella → **Suorita järjestelmänvalvojana**) ja valitse valikosta `[3] Uninstall`. Tarjolla on kolme asennuksen poiston alitilaa:

| tila | Admin vaaditaan | Laajuus |
|------|----------------|-------|
| **[1] Täysi asennuksen poisto - yksi napsautus** | ✅ | Poistaa sovelluskansion, julkisen työpöydän pikakuvakkeen, ffmpegin koneen PATH:sta, jokaisen käyttäjän HF-mallin välimuistin (Whisper/XTTS) ja konfiguroinnin (`HF token`) ja kaikki asennusohjelman asentamat Python AI -paketit. Lopussa se myös kysyy (opt-in), poistetaanko **Python 3.11** ja **Git for Windows** hiljainen asennus niiden rekisterin hiljaisten asennuksen poistomerkkijonojen kautta. |
| **[2] Vain nykyinen käyttäjä** | ❌ | Poistaa vain käynnissä olevan käyttäjän VTAI-määrityksen, HF/XTTS-välimuistin ja vanhan käyttäjäkohtaisen asennuksen. **Jättää järjestelmän laajuisen asennuksen ennalleen**, jotta muut tietokoneen Windows-tilit voivat jatkaa sovelluksen käyttöä. |
| **[3] Muokattu - rakeinen** | ✅ järjestelmäkohteille, ❌ käyttäjäkohteille | Y/N-kysymys jokaisesta luokasta: sovelluskansio, pikakuvake, järjestelmän PATH, vanhat käyttäjäkohtaiset asennukset, käyttäjien asetukset ja välimuistit, sitten Python-pakettiryhmät (TTS, PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip-riippuvuudet, pyannote ja käsittelyketjun aputyökalut) sekä lopuksi valinnainen Python 3.11:n ja Gitin poisto. |

Jokainen tila poistaa myös sen, mitä ohjelma säilyttää käyttäjälle: asetukset ja päivittäiset lokit (`%APPDATA%\VideoTranslatorAI`), ohjelman tiedot soittimen, JavaScriptin ja Wav2Lipin ajoympäristöineen (`%LOCALAPPDATA%\VideoTranslatorAI`), reaaliajan väliaikaistiedostot (`%TEMP%\VideoTranslatorAI`), MarianMT-mallit sekä tallennetut avaimet (HF-tunnus, ElevenLabs) Windowsin tunnistetietojen hallinnasta. Avaimet ovat Windows-tilikohtaisia: kukin tili poistaa omansa valinnalla `[2]`.

**Ei koskaan poistettu automaattisesti:** Visual Studio C++ Build Tools (jos olemassa vanhemmista ajoista). Voit poistaa ne manuaalisesti Windowsin asetuksissa käyttämällä *Sovelluksia ja ominaisuuksia*.

### Linux / macOS

Ei erillistä asennuksen poistoohjelmaa - poista manuaalisesti:

```bash
# GUI:n automaattisen asennusohjelman asentamat Python-paketit
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Käyttäjätiedot ja mallivälimuistit
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip ~/.cache/wav2lip
rm -rf ~/.config/videotranslatorai          # konfiguraatio (teemat, paneelien järjestys, asetukset)
rm -rf ~/.local/share/fonts/VideoTranslatorAI   # teemojen fontit
rm -rf ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt*   # MarianMT-käännösmallit
rm -rf ~/.local/share/VideoTranslatorAI                          # ohjelman tiedot (JavaScript-ajoympäristö yt-dlp:lle)
rm -rf "${TMPDIR:-/tmp}/VideoTranslatorAI"                       # reaaliajan väliaikaistiedostot
# tallennetut avaimet (HF-tunnus, ElevenLabs)
python3 -c "import keyring; [keyring.delete_password('VideoTranslatorAI', u) for u in ('hf_token', 'elevenlabs_api_key') if keyring.get_password('VideoTranslatorAI', u)]"
rm -f  ~/.videotranslatorai_config.json     # versioiden <= 1.9 vanha konfiguraatio, jos sellainen on
```

## Käyttö

### Diagnostiikka

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Suorittaa paikallisen ympäristön diagnostiikkaa aloittamatta kääntämistä tai asentamatta mitään. `--preflight-lipsync` käsittelee Wav2Lip-kasvopaketteja tarpeen mukaan, mikä on hyödyllistä ennen **Lip Syncin** käyttöönottoa. GUI paljastaa saman perustarkistuksen lokipaneelin **Diagnostiikka**-painikkeesta. `--preflight-player` käsittelee integroitua videosoitinta (python-mpv ja ladattava libmpv) tarpeen mukaan. `python -m videotranslator.libmpv_runtime check` tutkii vain libmpv:tä (poistumis 0 valmis, 2 ei käytettävissä).

**Lokitiedosto:** kaikki, mitä lokipaneeli näyttää (jokainen napsautus ja valinta, tulokset, käsittelyvaiheet, virheet tietoineen), tallentuu myös tiedostoon `logs/videotranslator.log` asetusten viereen: `~/.config/videotranslatorai/logs/` Linuxissa, `%APPDATA%\VideoTranslatorAI\logs\` Windowsissa. Yksi tiedosto päivässä, viimeiset 7 päivää säilytetään; **Diagnostiikka**-painike näyttää polun. Liitä se, kun ilmoitat ongelmasta. API-avaimia ja kenttiin kirjoitettua tekstiä ei koskaan kirjoiteta. Jokainen rivi näyttää ajan, tason (tieto, varoitus, virhe, käyttöliittymän kielellä, varoitukset ja virheet värillisinä paneelissa) ja alueen, esimerkiksi [ui] napsautuksille, [job] käännöksille, [live] reaaliajalle; jokainen käynnistys kirjoittaa otsakkeen, jossa on versio, järjestelmä, GPU ja asetukset.

### GUI

```bash
python video_translator_gui.py
```

**Asettelu:** eräkäännösasetukset näkyvät oikealla olevassa sarakkeessa asetuspaneeleina: **Syöte**, **Käännös**, **Työnkulkuprofiili**, **Aloita** ja kokoontaitettavat lisäosat (malli, käännöskone, ääni, äänen kloonaus, huulten synkronointi, päiväkirja, asetukset, hotwords). Suuri alue vasemmalla on **integroitu videosoitin** (kuljetus, soittolista, A/B-alkuperäinen vs. jälkiäänitetty ääni, tekstitys, tilannekuva, koko näyttö), jonka alla on **reaaliaikainen käännös** -palkki. Vedä korttia sen otsikon tai **≡**-kahvan avulla siirtääksesi sitä ylös tai alas sarakkeessa. tilaus tallennetaan (`ui_panel_order`) ja palautetaan seuraavan käynnistyksen yhteydessä. Alareunassa oleva lokipaneeli voidaan piilottaa **Piilota loki** -toiminnolla. Ikkuna avautuu käynnistettäessä keskitettynä nykyiseen näyttöön (osoittimen alla olevaan) ja maksimoituna, joten se toimii hyvin usean näytön asetuksissa.

**Videovideosoittimen säätimet:** kuvakkeet käyttävät yhdenmukaisia toiminnallisia värejä jokaisessa teemassa valitusta korostusväristä riippumatta:

| Ohjaus | Väri |
|---------|--------|
| Toista video | Vihreä |
| Tauko (korvaa Toista toiston aikana) | Amber |
| Pysäytä toisto | Korallin punainen |
| Edellinen / taaksepäin 10 s / eteenpäin 10 s / seuraava | Sininen |
| Tilannekuva | Violetti |
| Avaa kansio | Kulta |

Liikkuminen lisää hienovaraisen sävytetyn taustan. Säätimet, jotka eivät ole käytettävissä, ovat neutraaleja; soittolistan navigointi pysyy käytettävissä Stop-toiminnon jälkeen. Työkaluvihjeet ja näppäimistön tarkennusilmaisimet ovat edelleen käytettävissä, joten värit eivät ole ainoa tapa tunnistaa toimintoja.

**Paikallisista tiedostoista:**
1. Valitse yksi tai useampi videotiedosto napsauttamalla **Lisää**
2. Valitse lähde- ja kohdekieli
3. Avaa **Malli**-osio ja valitse Whisper-malli (`small` on hyvä tasapaino nopeuden ja tarkkuuden välillä)
4. Valitse ääni ja säädä TTS-nopeutta tarvittaessa
5. *(Valinnainen)* Valitse **Käännösmoottorissa** **Google** (oletus), **MarianMT** (paikallinen/offline), **DeepL Free** tai **Ollama LLM** (paikallinen, suositellaan äänen jälkiäänitykseen).
6. *(Valinnainen)* Ota käyttöön **äänikloonaus** (XTTS v2) ja/tai **puhuvien ihmisten tunnistaminen (diarisaatio)**
7. *(Valinnainen)* Ota käyttöön **Lip Sync** (Wav2Lip)
8. Napsauta **Aloita käännös**

**YouTubesta (tai mistä tahansa tuetuista sivustoista):**
1. Liitä yksi tai useampi URL-osoite **URL**-kenttään (yksi per rivi)
2. Määritä kieli, malli ja ääni tavalliseen tapaan
3. Napsauta **⬇ Lataa ja käännä**

> yt-dlp tukee YouTubea, Vimeoa, Twitter/X:ää, TikTokia ja [1000+ muuta sivustoa](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Reilun käytön huomautus:** Videoiden lataaminen yt-dlp:n kautta katsotaan YouTuben kaltaisten alustojen automaattiseksi pääsyksi, ja se voi rikkoa niiden käyttöehtoja. Raskas tai toistuva käyttö samasta IP-osoitteesta voi johtaa tilapäisiin estoihin (HTTP 429 / sisäänkirjautumisen edellyttämät virheet). Käytä VPN:ää tai käännä IP-osoitettasi, jos kohtaat latausvirheitä. Tämä työkalu on tarkoitettu vain henkilökohtaiseen, ei-kaupalliseen käyttöön. Käännetyn sisällön levittäminen voi loukata tekijänoikeuksia - kunnioita aina alkuperäisen sisällöntuottajan oikeuksia.

### Reaaliaikainen käännös (tekstitys ja kokeellinen äänikopiointi)

Katso paikallinen tiedosto tai ratkaistu on-demand-videolinkki käännetyillä tekstityksillä ja valinnaisella puhekäännöksellä. Käytä soittimen alla olevaa palkkia:

**Linkin kautta:**

1. Liitä linkki **URL**-kenttään
2. Aseta lähde- ja kohdekieli, valitse ääni ja säädä **Viive**-liukusäädintä
3. Valitse **Tekstitys** ja/tai **Tekstitys**
4. Jos haluat kuulla vain käännetyn äänen, valitse **Mykistä alkuperäinen ääni** ennen aloittamista (italiaksi: **Silenzia originale**, tekstityksen valintaruudun vierestä)
5. Napsauta **Käännä reaaliajassa** - linkki on ratkaistu ja käännös alkaa

**Ladatusta tiedostosta:** lataa video soittimeen (Syöte -> Lisää ja valitse se), jätä URL-kenttä tyhjäksi, valitse samat live-asetukset ja napsauta **Käännä reaaliajassa**. URL-osoite on ensisijainen, kun kenttä ei ole tyhjä.

- **Moottore:** MarianMT (offline, oletus), Google, DeepL tai Ollama. Puheentunnistus (Whisper) toimii paikallisesti. Offline-mallit tarvitsevat ensimmäisen latauksen.
- **Viive:** viivästetyssä tilassa tiedostolla, kuinka monta sekuntia käännöstä kerätään ennen kuin kuva jatkuu tauon jälkeen (vähintään 8 s äänellä, 4 s pelkillä tekstityksillä). Jos kuva pysähtyy yhä uudelleen, puskuri kasvaa 4 s kerrallaan 30 sekuntiin asti ja palkki kertoo siitä.
- **Ääneen jälkiäänitys:** kokeellinen Edge-TTS-puheen toisto toisen mpv-instanssin kautta. Se vaatii Internet-yhteyden ja on erillään erääänen kloonauksesta.
- **ElevenLabsin ääni:** valinnainen, kohdassa Lisäasetukset > Äänen kloonaus > **ElevenLabsin live-ääni**. Anna API-avain, tarkista se, valitse kohdekieltä puhuva malli ja ääni. Käännetty teksti lähetetään ElevenLabsille (maksu merkkien mukaan); avain pysyy järjestelmän avainnipussa. Jos avain tai kiintiö pettää, Edge-TTS jatkaa. Se avautuu myös reaaliaikapalkin **ElevenLabs…**-painikkeesta; palkin rivi kertoo, mitä ääntä dubbaus käyttää.
  - ElevenLabsin maksuton tilaus (tarkistettu 27. syyskuuta 2026): API:n kautta toimivat vain oletusäänet (Roger, Sarah, George, River...), 10 000 merkkiä kuukaudessa ja enintään 4 pyyntöä kerrallaan. Ikkuna merkitsee äänet, jotka vaativat maksullisen tilauksen.
  - ElevenLabs-kirjaston äänet, kloonatut äänet ja lisää merkkejä vaativat maksullisen ElevenLabs-tilauksen, joka ostetaan ElevenLabsilta sen omin hinnoin ja ehdoin ([ElevenLabs pricing](https://elevenlabs.io/pricing)). VideoTranslatorAI pysyy maksuttomana, ei ole sidoksissa ElevenLabsiin eikä tarvitse sitä: Edge-TTS on maksuton oletusääni.
  - Reaaliaikaan sopivat mallit, ensimmäinen ääni noin: Flash v2.5 0,2 s, Turbo v2.5 0,2 s, v3 Conversational 0,4 s. Multilingual v2 (0,9 s) ja v3 (1-2 s) kuulostavat rikkaammilta mutta jäävät videosta jälkeen; Turbo v2 ja Flash v2 puhuvat vain englantia.
  - Kun ElevenLabs hylkää repliikin (avain, tilaus, ääntä tai mallia ei löydy, kieli, merkit loppu, liikaa pyyntöjä), reaaliaikapalkki kertoo syyn ja loki säilyttää ElevenLabsin oman viestin.
- **Mykistä alkuperäinen ääni:** käytettävissä sekä ennen käännöksen aloittamista että sen aikana. Se hiljentää koko alkuperäisen ääniraidan, mukaan lukien musiikin ja tehosteet, mutta jättää käännetyn äänen kuuluviin. Se ei eristä alkuperäisessä äänessä puhuvaa henkilöä. Kytke se pois päältä palauttaaksesi ääniraidan; se nollautuu, kun live-istunto päättyy. Soittimen kaiutinpainike on yleinen mykistys, ei tämä itsenäinen säädin.
- **Keskeytä ja etsi:** videosoittimen säätimet on yhdistetty live-istuntoon; päästä päähän -äänen synkronointi vaatii edelleen alustakohtaisia ​​hyväksyntätestejä.
- **Nykyiset rajoitukset:** äänen ajoituksen kalibrointi ja hyväksyntä Windowsissa ovat vielä kesken. Yhä kasvavia suoria lähetyksiä ei tueta; live-tilan nimi ei tarkoita, että käynnissä olevaa lähetystä luettaisiin jatkuvasti.

Jos haluat tallentaa jälkiäänitetyn videon, käytä **Lataa ja käännä** / **Aloita käännös** reaaliaikaisen esikatselun sijaan.

### Käännösmoottorilohkot ja VPN

Kaksi erilaista lohkoa voi tapahtua eri korjauksin:

| Estä | Oire | Korjaa |
|-------|---------|-----|
| **Lataa** (yt-dlp) | "Kirjaudu sisään vahvistaaksesi, että et ole robotti", HTTP 429 | **VPN** / käännä IP-osoitetta tai kirjaudu sisään YouTubeen selaimessasi (evästeet luetaan automaattisesti) |
| **Käännös** (Googlen ilmainen päätepiste) | "Google Translate ei voinut kääntää... pyyntöjen määrä rajoitettu/estetty" | Käytä **MarianMT** (offline) tai **Ollama** (paikallinen) - ei pyyntöjen määrärajoitusta. VPN auttaa myös. Erävirta nyt **palautuu MarianMT:hen automaattisesti**, kun Google estetään. |

### Teemat ja ulkoasu

Napsauta otsikossa olevaa rataskuvaketta avataksesi **Asetukset**:

- **Teema**: Automaattinen (seuraa käyttöjärjestelmän tummaa/vaaleaa tilaa), Graphite (oletus), Slate, Light, Neon.
- **Teemat**: Dex ja Handheld (taskukonsoli, pikselifontti, paksut kehykset), CRT ja CRT Amber (80-luvun fosforinäyttö; myös video saa kaarevuuden ja juovat mpv-varjostimella). Oletuksena pysyy Graphite.
- **Aksenttiväri**: oletusväri teeman mukaan tai sininen, sinivihreä, violetti, vihreä, keltainen, ruusu.
- **Tekstin koko**: pieni, normaali, suuri, erittäin suuri.
- **Käyttöliittymän kieli**: 26 kieltä.

Muutokset tulevat voimaan välittömästi, ilman uudelleenkäynnistystä, ja ne tallennetaan asetustiedostoon (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Palauta oletukset** palauttaa Graphite-teeman, oletuskorostuksen, normaalin tekstikoon ja asetuspaneelien oletusjärjestyksen.

### Komentorivi

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Kaikki vaihtoehdot:**

| CLI-vaihtoehto | Kuvaus | Oletus |
|------|-------------|---------|
| `--lang-source` | Alkuperäinen kieli (`auto` automaattista tunnistusta varten) | `auto` |
| `--lang-target` | Kohdekielikoodi (esim. `it`, `fr`, `de`) | `it` |
| `--voice` | Edge-TTS-äänen nimi | auto |
| `--model` | Whisper-malli (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | TTS-nopeuden säätö (esim. `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` tai `deepl` | `google` |
| `--deepl-key` | DeepL Free API-avain | - |
| `--diarize` | Ota käyttöön puhuvien ihmisten tunnistaminen (diarisointi) (pyannote) | - |
| `--hf-token` | HuggingFace-merkki päiväkirjaa varten | - |
| `--lipsync` | Käytä Wav2Lip-huulisynkronointia äänen jälkiäänityksen jälkeen | - |
| `--subs-only` | Luo vain `.srt`, ohita äänen jälkiäänitys | - |
| `--no-subs` | Ohita `.srt`-sukupolvi | - |
| `--no-demucs` | Ohita äänen ja musiikin erottelu | - |
| `--output` / `-o` | Tulostustiedoston polku | auto |
| `--output-dir` | Kansio käännetyille tiedostoille (yksi paikka, Windows ja Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Käsittele useita tiedostoja | - |
| `--voicebox` | Kloonaa äänen käynnissä olevan Voicebox-palvelimen kautta | - |
| `--voicebox-url` | Voiceboxin osoite | `http://127.0.0.1:17493` |
| `--voicebox-engine` | Voiceboxin moottori (`chatterbox`, `qwen`, ...) | `chatterbox` |

### integraatiotestit todellisten mallien kanssa

Oletustestipaketti välttää todelliset mallilataukset ja pitkän GPU-työn. Opt-in empiiristen tarkistusten suorittaminen asennetulle paikalliselle pinolle:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Nämä tarkistukset vahvistavat todellisen Wav2Lip-tuonnin, Torch CUDA:n saatavuuden, Ollama-daemonin saatavuuden ja synteettisen puheen faster-Whisper. Ne epäonnistuvat tai ohitetaan tarkoituksella, kun paikallinen ajurin/daemonin/mallin tila ei ole valmis.

**Esimerkkejä:**

```bash
# Käännä italialainen video englanniksi paikallisen MarianMT:n avulla
# (lataa ~298 Mt mallin ensimmäisellä käyttökerralla, sitten täysin offline-tilassa)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Käännä äänikloonauksella + puhuvien ihmisten tunnistaminen (diarisointi)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Käännä huulisynkronoinnin avulla
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Vain tekstitykset (ei jälkiäänitystä)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Whisper mallit

| Malli | Koko | Nopeus | Tarkkuus |
|-------|------|-------|----------|
| tiny | 75 Mt | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 Mt | ⚡⚡⚡ | ★★☆☆ |
| small | 465 Mt | ⚡⚡ | ★★★☆ |
| medium | 1,5 Gt | ⚡ | ★★★★ |
| large-v2/v3 | 3 Gt | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 Gt | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` on `large-v3`:n tislattu versio (4 dekooderikerrosta vs 32) - lähes suuri laatu suunnilleen `medium`-tason nopeudella. Suositeltava oletusarvo nykyaikaiselle GPU:lle, kun transkriptionopeudella on merkitystä; monikielisen aineiston laadun heikkeneminen on vähäistä.

> Mallit ladataan automaattisesti ensimmäisellä käyttökerralla.

> Etkö tiedä, mikä malli sopii koneellesi? Avaa **Mallit tälle tietokoneelle** mallin asetuksista: se suosittelee mallia laitteistosi perusteella ja voi mitata sen.

## Erilliset moduulin CLI:t

Modulaarinen paketti paljastaa neljä käyttäjäkohtaista työkalua, jotka voidaan käynnistää suoraan ilman koko putkilinjan käynnistämistä:

```bash
# Esilennä video kasvojen läsnäoloa varten (Wav2Lip ohittaa, jos se ei ole paikalla).
python3 -m videotranslator.face_detector path/to/video.mp4
# exit 0 = kasvot läsnä, exit 1 = ei kasvoja

# Analysoi build_dubbed_track:n tuottama *_metrics.csv.
# Raportit P50/P75/P90/P95 kohteesta pre_stretch_ratio, kuuluvuuskaistan rikkoutuminen,
# venyttää moottorin käyttöä ja N pahimpia poikkeamia kohdetekstillään.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Puhdista teksti TTS:ää varten (kirjoittaa uudelleen kaksoispisteet, puolipisteet, ellipsit, viivat).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Arvioi äänen jälkiäänityksen vaikeus .srt- tai .json-segmenttitiedostosta ENNEN TTS:n suorittamista.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Jokaisessa työkalussa on `-h`/`--help` kaikkia lisävarusteita varten. Ne ovat itsenäisiä ja käyttävät uudelleen samoja moduuleja, joihin äänen jälkiäänitysputkisto luottaa, joten niiden tulos pysyy yhtenäisenä suoritusajan kanssa.

## Lisenssi

MIT

### Kolmannen osapuolen komponentit

Arkiston koodi on MIT. Asentajat lataavat alla olevat komponentit omista lähteistään asennuksen yhteydessä; hanke ei jaa niitä uudelleen.

- **libmpv** (https://github.com/mpv-player/mpv), integroidun videosoittimen moottori. Windows: zhongflyn (https://github.com/zhongfly/mpv-winbuild) LGPL-versiota kokeillaan ensin; shinchiron kiinnitetty GPL-koonnos (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) on varavaihtoehto. `mpv-runtime\BUILD.txt` tallentaa lähteen, lisenssin ja mpv-sitoumuksen, ja lisenssiteksti on DLL:n vieressä. Linux: jakelupaketti (`libmpv2`, `libmpv1`, `mpv-libs` tai `mpv`).
- **FFmpeg** libmpv:n sisällä (LGPL tai GPL, libmpv-koontiversion mukaan).
- **python-mpv** (`mpv` PyPI:ssä), GPLv2+ tai LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), jota Windowsin asennusohjelma käyttää libmpv:n purkamiseen ja poistetaan myöhemmin.
- **Vulkan loader** (Khronos, MIT ja Apache-2.0), ladataan Windowsiin vain, kun `vulkan-1.dll` puuttuu.
- **edge-tts** (LGPLv3), jota äänen jälkiäänitysputkisto käyttää.
- **MarianMT-mallit** (Helsinki-NLP), ladattu Hugging Face Hubista ensimmäisellä käyttökerralla omilla lisenssillään (Apache-2.0 `opus-mt`-malleille, CC-BY-4.0 `opus-mt-tc-big`-malleille).
- **Voicebox** (MIT, https://github.com/jamiepine/voicebox), valinnainen, käyttäjän erikseen asentama; sen moottoreilla on omat lisenssinsä (Chatterbox MIT äänivesileimalla, TADA-painot Llama 3.2 Community License -lisenssillä).
- **ElevenLabs** (https://elevenlabs.io), valinnainen verkkopalvelu, jota käytetään käyttäjän omalla tilillä ja API-avaimella palvelun omin ehdoin.
- Fontit **Pixelify Sans** ja **VT323** (SIL Open Font License 1.1), joita teemat käyttävät: repositorion ainoat kolmannen osapuolen tiedostot, hakemistossa `assets/fonts` lisenssitekstien vieressä.
