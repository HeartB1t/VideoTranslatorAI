# 🎬 Video Translator AI

[Inglés](../../README.md) | [Todas las traducciones](README.md)

**Lea esta página en:** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Herramienta de doblaje de voz y video basada en inteligencia artificial que transcribe, traduce y vuelve a doblar videos automáticamente a 26 idiomas, con opciones de procesamiento local y sin necesidad de claves API de forma predeterminada. El reconocimiento de voz Whisper se ejecuta localmente; Edge-TTS, Google Translate y DeepL requieren una conexión a Internet. Las funciones opcionales (DeepL, identificación de personas que hablan (diarización)) pueden requerir una clave API o un token de acceso.

> **v2.0**: paquete modular, traducción local de Ollama, orquestación de perfiles de calidad, metadatos de Python instalables y pruebas de integración opcionales con modelos reales. Consulte [Versiones de GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases) y el historial de confirmaciones para obtener la lista completa de cambios.

## como funciona

1. **Transcripción** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcribe el audio (acelerado por GPU)
2. **Separación de voz/música** - [Demucs](https://github.com/facebookresearch/demucs) aísla las voces de la música de fondo
3. **Traducción** - MarianMT (local, fuera de línea), Google Translate, DeepL Free o **Ollama LLM** (Qwen3, traducciones concisas que admiten ranuras)
4. **identificación de personas que hablan (diarización)** *(opcional)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifica quién habla en cada segmento
5. **doblaje de voz** - [Edge-TTS](https://github.com/rany2/edge-tts) (más de 400 voces) o [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (clonación de voz, para cada hablante de la conversación)
6. **Mezcla**: voz doblada mezclada con música de fondo original
7. **Normalización**: audio final normalizado a -23 LUFS (estándar de transmisión EBU R128)
8. **Lip Sync** *(opcional)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) sincroniza los movimientos de la boca con el audio doblado.

## Características

- 🖥️ GUI temática (Tkinter): no se necesita línea de comando; Temas Graphite, Slate, Light y Neon, colores de acento, tamaño de texto y paneles de configuración que puede reordenar arrastrando
- 🌍 **26 idiomas de destino** con múltiples voces por idioma
- 🌐 **UI en 26 idiomas**: la interfaz se adapta a tu idioma
- 🎬 **Compatibilidad con YouTube y URL**: pegue cualquier enlace de YouTube y traduzca directamente (con tecnología de yt-dlp)
- ▶️ **Reproductor de vídeo integrado** (libmpv/mpv): controles de transporte codificados por colores, lista de reproducción, audio original A/B versus audio doblado, alternancia de subtítulos, instantánea, pantalla completa, carpeta abierta
- ⏱️ **Traducción en tiempo real**: vea un archivo local o un enlace de video a pedido resuelto con subtítulos traducidos y un control deslizante de demora estilo YouTube; Motores MarianMT/Google/DeepL/Ollama. El doblaje de voz experimental utiliza Edge-TTS y una segunda instancia de mpv. El manejo de la superposición de voz y la aceptación de audio real/Windows siguen en progreso; Las transmisiones en vivo en crecimiento aún no son compatibles. Consulte el [estado de implementación en vivo](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Separación de voz/música a través de Demucs (mantiene la música de fondo)
- 🔇 **Silenciar audio original**, disponible antes y durante la traducción en vivo, silencia la banda sonora del video mientras mantiene audible la voz traducida. Desactívelo para restaurar el audio original; se reinicia cuando finaliza la sesión en vivo.
- 🧠 **MarianMT**: traducción neuronal fuera de línea totalmente local (Helsinki-NLP, sin límites de tasa de solicitudes, sin clave API)
- 🤖 **Traducción de Ollama LLM** *(nuevo en v2.0)* - LLM local (Qwen3, Llama, Mistral) produce traducciones concisas con reconocimiento de ranuras para doblaje de voz natural, detecta/instala/inicia/extrae automáticamente el modelo en el primer uso
- 🎙️ **Clonación de voz**: Coqui XTTS v2 clona a la persona que habla con la voz del audio original en el idioma de destino (modelo de ~1,8 GB), con velocidad adaptativa por segmento y reintento de múltiples semillas en alucinaciones.
- 👥 **identificación de personas que hablan (diarización)** - pyannote-audio 3.1 identifica varias personas que hablan; XTTS clona cada voz por separado
- 💋 **Lip Sync**: Wav2Lip GAN sincroniza los movimientos de la boca con el audio doblado (modelo de ~416 MB)
- 🔊 **Normalización de audio** - normalización automática de volumen de -23 LUFS (EBU R128)
- ✏️ Editor de subtítulos: revise y corrija los subtítulos antes del doblaje de voz
- 📦 Procesamiento por lotes: traduce varios videos o URL a la vez
- ⚡ Aceleración de GPU a través de CUDA (vuelve a la CPU automáticamente)
- 📄 Exportación de subtítulos opcional `.srt`
- 🔁 **DeepL Free** motor de traducción (opcional: 500 000 caracteres/mes, requiere una clave API gratuita)
- 🔧 **Instalación automática**: los paquetes de Python que faltan y ffmpeg se instalan automáticamente en el primer inicio

## Idiomas soportados

Árabe, chino, checo, danés, holandés, inglés, finlandés, francés, alemán, griego, hindi, húngaro, indonesio, italiano, japonés, coreano, noruego, polaco, portugués, rumano, ruso, español, sueco, turco, ucraniano, vietnamita

## Catálogo de voz

El catálogo de voz Edge-TTS se define en `LANGUAGES` cerca de la parte superior de `video_translator_gui.py`. Ese diccionario es la fuente de verdad para los nombres del idioma de destino, los botones de opción de voz de la GUI y la voz alternativa de CLI cuando se omite `--voice`.

Las notas de Claude/project-maintenance reflejan esta ubicación en `CLAUDE.md` en **Voice Catalog Source Of Truth**, para que los futuros agentes de código sepan dónde actualizar las voces y hacia dónde apunta el README a los usuarios.

## Motores de traducción

| motor | Configuración | Límites | Calidad |
|--------|-------|--------|---------|
| **Google Translate** *(predeterminado)* | Ninguno | Scraping no oficial: puede verse limitado en videos grandes | ★★★★ |
| **MarianMT** | Ninguno: descargas ~298 MB por par de idiomas en el primer uso | Ninguno: completamente fuera de línea después de la descarga | ★★★★ |
| **DeepL Free** | Clave API gratuita en [deepl.com](https://www.deepl.com/pro-api) | 500.000 caracteres/mes | ★★★★★ |
| **Ollama LLM** *(recomendado para doblaje de voz - nuevo en v2.0)* | Se instala automáticamente en el primer uso (~1 GB Ollama + modelo de 5 GB) | Ninguno - completamente local | ★★★★★ |

> **MarianMT** utiliza modelos [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP), almacenados en caché localmente después de la primera descarga. Requiere un idioma de origen explícito (no se admite la detección automática; seleccione el idioma de origen manualmente). Los paquetes de Python necesarios (`sacremoses`, `sentencepiece`) se instalan automáticamente en la primera selección si faltan.

> **Ollama LLM** *(nuevo en v2.0)* es el motor recomendado para el doblaje de voz porque produce traducciones que tienen en cuenta el intervalo de tiempo de destino. Mientras que MarianMT traduce literalmente y produce italiano/español/francés aproximadamente un 25% más que el inglés (lo que obliga a la compresión de audio audible en el TTS), se solicita al LLM que mantenga cada segmento conciso y natural para la entrega hablada, logrando una proporción de caracteres típica de 0,85-0,95 frente a la fuente. El modelo predeterminado es `qwen3:8b` (5,2 GB en disco, ~6 GB de VRAM); `qwen3:4b` (~3 GB) es la opción liviana, `qwen3:14b` la de mayor calidad. La canalización detecta automáticamente el binario de Ollama, lo instala automáticamente a través del instalador oficial en el primer uso (con una ventana emergente de consentimiento), inicia el demonio y extrae el modelo elegido; no se requiere configuración manual. Cambia automáticamente a Google Translate si falta algo.

## Clonación de voz (XTTS v2)

Cuando está habilitada, la aplicación extrae la voz del hablante del video original y la usa como referencia para clonar la voz en el idioma de destino.

- Idiomas admitidos: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Para los 9 idiomas restantes, Edge-TTS se utiliza automáticamente como alternativa
- Modelo (~1,8 GB) descargado automáticamente en el primer uso en `~/.local/share/tts/`
- **Referencia filtrada por VAD** (v1.4): 10-15 s de voz continua seleccionada del audio original mediante [silero-vad](https://github.com/snakers4/silero-vad) para una mejor calidad de clonación de voz
- **Velocidad de generación** configurable (`xtts_speed`, predeterminado `1.25`): los valores más altos reducen los artefactos de compresión de audio de posprocesamiento cuando el texto traducido es más largo que la ranura de origen. Sintonice a través de `~/.config/videotranslatorai/config.json` o CLI `--xtts-speed`
- Se ejecuta en CUDA o CPU

## identificación de personas que hablan (diarización) (pyannote-audio)

Cuando está habilitada, la aplicación identifica quién habla en cada segmento. Combinado con Voice Cloning, la voz de cada hablante se clona por separado, ideal para entrevistas, podcasts y vídeos de varias personas.

- Requiere un [token HuggingFace](https://huggingface.co/settings/tokens) gratuito (registro único)
- **Token almacenado de forma segura** (v1.4) a través del conjunto de claves del sistema operativo: Windows Credential Manager, macOS Keychain, Linux Secret Service. Migración automática desde almacenamiento JSON de texto plano anterior
- Después de la primera descarga, funciona completamente sin conexión
- Modelo: `pyannote/speaker-diarization-3.1`

## Sincronización de labios (Wav2Lip)

Cuando está habilitada, la aplicación aplica Wav2Lip GAN para sincronizar los movimientos de la boca del sujeto con el audio doblado: la persona parece hablar el idioma traducido.

- Modelo (~416 MB) y repositorio clonados automáticamente en el primer uso en `~/.local/share/wav2lip/`
- Se ejecuta en CUDA (recomendado) o CPU
- Aumenta significativamente el tiempo de procesamiento
- Funciona mejor en vídeos con una sola cara claramente visible

## Requisitos

- Python 3.10+ (el instalador de Windows aprovisiona 3.11.9 automáticamente)
- Windows 10/11 (x64), Linux o macOS
- **Se recomienda encarecidamente la GPU NVIDIA**: consulte la tabla de GPU a continuación
- 20 GB de espacio libre en disco para una instalación completa (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg y todos los paquetes de Python se instalan automáticamente** en el primer inicio si faltan. No se requiere configuración manual.

**Dependencia del sistema opcional** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Cuando se instala, se utiliza para preservar el tono y ampliar el tiempo en la banda de calidad controlada por perfil (predeterminado 1,15-1,50, hasta 1,65 para contenido duro), eliminando el efecto residual de "ardilla" en las voces XTTS clonadas. La canalización se ejecuta sin cambios sin él (retroceso automático a ffmpeg `atempo`). Los perfiles de calidad ahora prefieren reintentos de traducción más cortos que una aceleración extrema del audio.

### Soporte de GPU

La canalización utiliza cinco componentes acelerados por GPU (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). La cobertura de GPU no es uniforme entre proveedores:

| GPU | Windows | Linux | Notas |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx o posterior, controlador CUDA 12.4) | ✅ aceleración total | ✅ aceleración total | **Recomendado.** Los 5 componentes se ejecutan en GPU. |
| **AMD** (Radeón) | ⚠️ incompleto (DirectML no es compatible con XTTS y faster-whisper) | ⚠️ parcial (ROCm funciona para Demucs/XTTS/pyannote pero faster-whisper solo admite CUDA) | Funciona, pero la transcripción Whisper permanece en la CPU y domina el tiempo total. |
| **Intel Arc** | ⚠️ Compatibilidad inmadura con PyTorch XPU | ⚠️ mismo | No probado. |
| **Ninguno (solo CPU)** | ✅ funciona | ✅ funciona | Espere **10-20 veces más lento** que en tiempo real. Un clip de 5 minutos puede tardar más de 50 minutos en transcribirse con Whisper large-v3. |

**VRAM NVIDIA recomendada:**

| VRAM | Tarjetas gráficas habituales | Experiencia |
|------|---------------|-----------|
| 6GB | GTX 1660, RTX 2060 | Utilizable, no se puede ejecutar XTTS + Wav2Lip simultáneamente |
| 8GB | RTX 3060 Ti, 4060 | Pipeline completo, sin margen |
| **12GB+** | **RTX 3060 12GB, 4070, 4080** | **Recomendado - cómodo** |
| 24GB | RTX 3090, 4090 | Capacidad adicional para lotes grandes |

## Instalación

### Windows

1. Clona o descarga este repositorio
2. Haga clic derecho en `setup_windows.bat` → **Ejecutar como administrador** → el menú muestra `[1] Install`
3. El instalador automáticamente:
   - Instala Python 3.11 si no está presente (en todo el sistema)
   - Instala Git for Windows si no está presente
   - Instala todas las dependencias de Python (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps, etc.)
   - Descarga e instala ffmpeg
   - Instala el reproductor de video integrado (python-mpv más una compilación libmpv en `mpv-runtime`). El paso es opcional: si falla, todo lo demás funciona y el panel del reproductor explica lo que falta
   - Crea un **acceso directo al escritorio público** (visible para todas las cuentas de Windows en la PC)

> El instalador es **multiusuario**: todo se instala en todo el sistema bajo `%ProgramFiles%\VideoTranslatorAI` y cualquier usuario de Windows en la máquina encuentra el acceso directo listo para usar. Las herramientas de compilación VS C++ **ya no son necesarias**: la bifurcación `coqui-tts` mantenida proporciona paquetes de ruedas Python precompilados.

### Linux/macOS

```bash
# Clonar el repositorio
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Opcional: instale la pila PyTorch NVIDIA CUDA 12.4 probada por adelantado
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Opcional: preinstale todos los paquetes de tiempo de ejecución de Python en lugar de dejar que la GUI
# instalar los paquetes faltantes en la primera ejecución
pip install --break-system-packages -r requirements.txt

# Opcional: el reproductor de vídeo integrado (libmpv de la distribución, python-mpv de PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arco: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Opcional: instale el proyecto como un paquete Python editable
pip install --break-system-packages --no-deps -e .

# Lanzar desde la fuente
python video_translator_gui.py

# O, después de editar/instalar el paquete
videotranslatorai
videotranslatorai --preflight
```

> En el primer inicio, la GUI detecta cualquier paquete faltante (faster-whisper, Demucs, Edge-TTS, etc.) y los instala automáticamente, transmitiendo la salida a la ventana de registro. ffmpeg también se instala automáticamente a través de `apt-get` / `dnf` / `pacman` (Linux) o se descarga desde GitHub (Windows).

> El encabezado muestra una insignia de **Jugador**. Cuando falta libmpv o python-mpv, el panel izquierdo dice lo que falta y ofrece **Instalar reproductor**: en Linux usa el administrador de paquetes a través de pkexec (luego `sudo -n`) y muestra el comando manual cuando ninguno de los dos funciona; en Windows pregunta antes de descargar libmpv para el usuario actual (aproximadamente 32 MB).

### Perfiles de requisitos

| Archivo | Propósito |
|------|---------|
| `requirements.txt` | Instalación en tiempo de ejecución completa y compatible con versiones anteriores. |
| `requirements-core.txt` | Paquetes de canalización predeterminados utilizados por GUI/CLI. |
| `requirements-optional.txt` | XTTS, tokenizadores MarianMT, diarización, VAD, llavero. |
| `requirements-wav2lip.txt` | Pila de detección de rostros y tiempo de ejecución de Wav2Lip (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Pila de PyTorch probada con ruedas NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Reproductor de vídeo integrado: python-mpv (necesita libmpv del sistema o del instalador de Windows). |
| `requirements-dev.txt` | Dependencias ligeras utilizadas por CI/pruebas unitarias. |

## Desinstalar

### Windows

Ejecute `setup_windows.bat` (haga clic derecho → **Ejecutar como administrador**) y seleccione `[3] Uninstall` en el menú. Se ofrecen tres submodos de desinstalación:

| Modo | Se requiere administrador | Alcance |
|------|----------------|-------|
| **[1] Desinstalación completa: un clic** | ✅ | Elimina la carpeta de la aplicación, el acceso directo del escritorio público, ffmpeg de la RUTA de la máquina, el caché del modelo HF de cada usuario (Whisper/XTTS) y la configuración (`HF token`) y todos los paquetes de Python AI instalados por el instalador. Al final, también pregunta (optar por participar) si se desea desinstalar silenciosamente **Python 3.11** y **Git for Windows** a través de sus cadenas de desinstalación silenciosa del registro. |
| **[2] Solo usuario actual** | ❌ | Elimina solo la configuración VTAI del usuario en ejecución, la caché HF/XTTS y la instalación heredada por usuario. **Deja intacta la instalación de todo el sistema** para que otras cuentas de Windows en la PC puedan seguir usando la aplicación. |
| **[3] Personalizado - granular** | ✅ para elementos del sistema, ❌ para elementos de usuario | Mensaje S/N para cada categoría: carpeta de aplicaciones, acceso directo, RUTA de la máquina, instalaciones heredadas por usuario, configuraciones/cachés por usuario, luego paquetes de Python agrupados (TTS, pila de PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, utilidades de canalización) y, finalmente, Python 3.11 y Git opcionales. |

**Nunca se elimina automáticamente:** Herramientas de compilación de Visual Studio C++ (si están presentes en ejecuciones anteriores). Utilice *Aplicaciones y características* en la configuración de Windows para eliminarlas manualmente si lo desea.

### Linux/macOS

Sin desinstalador dedicado; elimínelo manualmente:

```bash
# Paquetes de Python instalados por el autoinstalador de la GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Datos de usuario y cachés de modelos.
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (temas, orden de los paneles, configuraciones)
rm -f  ~/.videotranslatorai_config.json     # configuración heredada de versiones <= 1.9, si está presente
```

## Uso

### Diagnóstico

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Ejecuta diagnósticos del entorno local sin iniciar la traducción ni instalar nada. `--preflight-lipsync` trata los paquetes faciales Wav2Lip según sea necesario, lo cual resulta útil antes de habilitar **Lip Sync**. La GUI expone la misma verificación básica desde el botón **Diagnóstico** del panel de registro. `--preflight-player` trata el reproductor de vídeo integrado (python-mpv y un libmpv cargable) según sea necesario. `python -m videotranslator.libmpv_runtime check` prueba libmpv solo (salida 0 lista, 2 no disponibles).

### GUI

```bash
python video_translator_gui.py
```

**Diseño:** las configuraciones de traducción por lotes se encuentran en la columna de la derecha, como una pila de paneles de configuración: **Entrada**, **Traducción**, **Perfil de flujo de trabajo**, **Inicio** y las secciones avanzadas plegables (modelo, motor de traducción, audio, clonación de voz, sincronización de labios, diario, opciones, palabras activas). El área grande a la izquierda es el **reproductor de video integrado** (transporte, lista de reproducción, original A/B versus audio doblado, subtítulos, instantánea, pantalla completa), con la barra de **traducción en tiempo real** debajo. Arrastre una tarjeta por su título o por el controlador **≡** para moverla hacia arriba o hacia abajo en la columna; el orden se guarda (`ui_panel_order`) y se restaura en el siguiente inicio. El panel de registro en la parte inferior se puede ocultar con **Ocultar registro**. Al iniciar, la ventana se abre centrada en el monitor actual (el que está debajo del puntero) y maximizada, por lo que se comporta bien en una configuración de varios monitores.

**Controles del reproductor de video:** los íconos usan colores funcionales consistentes en cada tema, independientemente del color de acento seleccionado:

| controlar | Color |
|---------|--------|
| Reproducir vídeo | Verde |
| Pausa (reemplaza Reproducir mientras se juega) | ámbar |
| Detener la reproducción | rojo coral |
| Anterior / atrás 10 s / adelante 10 s / siguiente | azul |
| Instantánea | violeta |
| Abrir carpeta | oro |

Al pasar el cursor se agrega un fondo teñido sutil. Los controles no disponibles son neutrales; La navegación de la lista de reproducción sigue siendo utilizable después de Detener. La información sobre herramientas y los indicadores de enfoque del teclado siguen estando disponibles, por lo que el color no es la única forma de identificar acciones.

**De archivos locales:**
1. Haga clic en **Agregar** para seleccionar uno o más archivos de video.
2. Elija el idioma de origen y de destino
3. Abra la sección **Modelo** y seleccione un modelo Whisper (`small` es un buen equilibrio entre velocidad y precisión)
4. Elija una voz y ajuste la velocidad de TTS si es necesario
5. *(Opcional)* En **Motor de traducción** seleccione **Google** (predeterminado), **MarianMT** (local/sin conexión), **DeepL Free** o **Ollama LLM** (local, recomendado para doblaje de voz).
6. *(Opcional)* Habilite **Clonación de voz** (XTTS v2) y/o **identificación de personas que hablan (diarización)**
7. *(Opcional)* Habilitar **Sincronización de labios** (Wav2Lip)
8. Haga clic en **Iniciar traducción**

**Desde YouTube (o cualquier sitio compatible):**
1. Pegue una o más URL en el campo **URL** (una por línea)
2. Configurar idioma, modelo y voz como siempre
3. Haga clic en **⬇ Descargar y traducir**

> yt-dlp es compatible con YouTube, Vimeo, Twitter/X, TikTok y [más de 1000 sitios más](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Aviso de uso legítimo:** La descarga de videos a través de yt-dlp se considera acceso automatizado por parte de plataformas como YouTube y puede violar sus Términos de servicio. El uso intensivo o repetido de la misma dirección IP puede provocar bloqueos temporales (errores HTTP 429/requiere inicio de sesión). Utilice una VPN o rote su IP si encuentra fallas en la descarga. Esta herramienta está destinada únicamente para uso personal y no comercial. La redistribución del contenido traducido puede infringir los derechos de autor; respete siempre los derechos del creador original.

### Traducción en tiempo real (subtítulos y doblaje de voz experimental)

Mire un archivo local o un enlace de video a pedido resuelto con subtítulos traducidos y traducción hablada opcional. Usa la barra debajo del reproductor:

**Desde un enlace:**

1. Pega un enlace en el campo **URL**
2. Establezca el idioma de origen y de destino, elija una voz y ajuste el control deslizante **Retraso**
3. Seleccione **Voz doblada** y/o **Subtítulos**
4. Para escuchar solo la voz traducida, seleccione **Silenciar audio original** antes de comenzar (en italiano: **Silenzia originale**, junto a la casilla de verificación de subtítulos)
5. Haga clic en **Traducir en tiempo real**: el enlace se resuelve y comienza la traducción.

**Desde un archivo cargado:** cargue un video en el reproductor (Entrada -> Agregar, luego selecciónelo), deje el campo URL vacío, elija la misma configuración en vivo y haga clic en **Traducir en tiempo real**. Una URL tiene prioridad cuando el campo no está vacío.

- **Motor:** MarianMT (sin conexión, predeterminado), Google, DeepL u Ollama. El reconocimiento de voz (Whisper) se ejecuta localmente. Los modelos sin conexión necesitan una descarga inicial.
- **Doblaje de voz:** Reproducción de voz experimental Edge-TTS a través de una segunda instancia mpv. Requiere acceso a Internet y es independiente de la clonación de voz por lotes.
- **Silenciar audio original:** disponible tanto antes de comenzar como durante la traducción. Silencia toda la banda sonora original, incluida la música y los efectos, pero deja audible la voz traducida. No aísla a la persona que habla en el audio original. Desactívelo para restaurar la banda sonora; se reinicia cuando finaliza la sesión en vivo. El botón del altavoz del reproductor es el silencio general, no este control independiente.
- **Pausar y buscar:** los controles del reproductor de video están conectados a la sesión en vivo; La sincronización de audio de un extremo a otro aún necesita pruebas de aceptación específicas de la plataforma.
- **Límites actuales:** el manejo de superposición/desvanecimiento de clips, la calibración de temporización de audio y la aceptación de Windows permanecen abiertos. Las crecientes transmisiones en vivo aún no son compatibles; la etiqueta del modo en vivo no implica soporte para la ingesta de una transmisión a medida que crece. Consulte el [estado de implementación y trabajo restante](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Para un video doblado guardado, use **Descargar y traducir** / **Iniciar traducción** en lugar de la vista previa en tiempo real.

### Bloques de motor de traducción y VPN

Pueden ocurrir dos bloqueos diferentes, con diferentes soluciones:

| Bloquear | Síntoma | Arreglar |
|-------|---------|-----|
| **Descargar** (yt-dlp) | "Inicia sesión para confirmar que no eres un bot", HTTP 429 | **VPN** / rotar IP, o iniciar sesión en YouTube en su navegador (las cookies se leen automáticamente) |
| **Traducción** (punto final gratuito de Google) | "Google Translate no se pudo traducir... tasa de solicitud limitada/bloqueada" | Utilice **MarianMT** (fuera de línea) o **Ollama** (local): sin límite de tasa de solicitud. Una VPN también ayuda. El flujo por lotes ahora **vuelve a MarianMT automáticamente** cuando se bloquea Google. |

### Temas y apariencia

Haga clic en el ícono de ajustes en el encabezado para abrir **Configuración**:

- **Tema**: Automático (sigue el modo oscuro/claro del sistema operativo), Graphite (predeterminado), Slate, Light, Neon.
- **Color de acento**: predeterminado por tema, o azul, verde azulado, violeta, verde, ámbar, rosa.
- **Tamaño del texto**: pequeño, normal, grande, extra grande.
- **Idioma de la interfaz**: 26 idiomas.

Los cambios se aplican inmediatamente, sin reiniciar, y se guardan en el archivo de configuración (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Restaurar valores predeterminados** recupera el tema Graphite, el acento predeterminado, el tamaño de texto normal y el orden predeterminado de los paneles de configuración.

### línea de comando

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Todas las opciones:**

| Opción CLI | Descripción | Predeterminado |
|------|-------------|---------|
| `--lang-source` | Idioma de origen (`auto` para detección automática) | `auto` |
| `--lang-target` | Código de idioma de destino (por ejemplo, `it`, `fr`, `de`) | `it` |
| `--voice` | Nombre de voz Edge-TTS | auto |
| `--model` | Modelo Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Ajuste de velocidad TTS (por ejemplo, `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` o `deepl` | `google` |
| `--deepl-key` | Clave API DeepL Free | - |
| `--diarize` | Habilitar la identificación de personas que hablan (diarización) (pyannote) | - |
| `--hf-token` | Token HuggingFace para diarioización | - |
| `--lipsync` | Aplicar sincronización de labios Wav2Lip después del doblaje de voz | - |
| `--subs-only` | Generar solo `.srt`, omitir doblaje de voz | - |
| `--no-subs` | Omitir generación `.srt` | - |
| `--no-demucs` | Saltar separación de voz/música | - |
| `--output` / `-o` | Ruta del archivo de salida | auto |
| `--output-dir` | Carpeta para archivos traducidos (un solo lugar, Windows y Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Procesar múltiples archivos | - |

### pruebas de integración con modelos reales

El conjunto de pruebas predeterminado evita descargas de modelos reales y largos trabajos de GPU. Para ejecutar comprobaciones empíricas de suscripción voluntaria para la pila local instalada:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Estas comprobaciones validan las importaciones reales de Wav2Lip, la disponibilidad de Torch CUDA, la disponibilidad del demonio Ollama y faster-Whisper en voz sintética. Fallan o se saltan intencionalmente cuando el estado del controlador/demonio/modelo local no está listo.

**Ejemplos:**

```bash
# Traduce videos italianos a inglés con MarianMT local
# (descarga el modelo de ~298 MB en el primer uso, luego completamente fuera de línea)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Traducir con clonación de voz + identificación de personas que hablan (diarización)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Traducir con sincronización de labios
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Solo subtítulos (sin doblaje de voz)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Modelos Whisper

| modelo | Tamaño | Velocidad | Precisión |
|-------|------|-------|----------|
| tiny | 75 megas | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 megas | ⚡⚡⚡ | ★★☆☆ |
| small | 465 megas | ⚡⚡ | ★★★☆ |
| medium | 1,5 GB | ⚡ | ★★★★ |
| large-v2/v3 | 3GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` es una versión destilada de `large-v3` (4 capas de decodificador frente a 32): calidad casi alta a una velocidad aproximada del nivel `medium`. Valor predeterminado recomendado en una GPU moderna cuando la velocidad de transcripción importa; La caída de la calidad del material multilingüe es menor.

> Los modelos se descargan automáticamente en el primer uso.

## CLI de módulo independiente

El paquete modular expone cuatro herramientas orientadas al usuario que se pueden invocar directamente sin iniciar el proceso completo:

```bash
# Realice una verificación previa de un video para detectar la presencia de rostros (Wav2Lip se omitirá si no está).
python3 -m videotranslator.face_detector path/to/video.mp4
# salida 0 = cara presente, salida 1 = sin cara

# Analice un *_metrics.csv producido por build_dubbed_track.
# Reportes P50/P75/P90/P95 de pre_stretch_ratio, avería de banda de audibilidad,
# ampliar el uso del motor y los N peores valores atípicos con su texto de destino.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Desinfecta el texto para TTS (reescribe dos puntos, punto y coma, puntos suspensivos, guiones).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Calcule la dificultad del doblaje de voz a partir de un archivo de segmentos .srt o .json ANTES de ejecutar TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Cada herramienta tiene `-h`/`--help` para opciones completas. Son autónomos y reutilizan los mismos módulos en los que se basa el proceso de doblaje de voz, por lo que su salida se mantiene coherente con el tiempo de ejecución.

## Licencia

MIT

### Componentes de terceros

El código del repositorio es MIT. Los instaladores descargan los siguientes componentes de sus propias fuentes en el momento de la instalación; el proyecto no los redistribuye.

- **libmpv** (https://github.com/mpv-player/mpv), el motor del reproductor de vídeo integrado. Windows: primero se prueba la compilación LGPL de zhongfly (https://github.com/zhongfly/mpv-winbuild); una compilación GPL fijada por shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) es la alternativa. `mpv-runtime\BUILD.txt` registra la fuente, el tipo de licencia y la confirmación mpv, y el texto de la licencia se encuentra al lado de la DLL. Linux: el paquete de distribución (`libmpv2`, `libmpv1`, `mpv-libs` o `mpv`).
- **FFmpeg** dentro de libmpv (LGPL o GPL, siguiendo la compilación de libmpv).
- **python-mpv** (`mpv` en PyPI), GPLv2+ o LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), utilizado por el instalador de Windows para extraer libmpv y eliminado posteriormente.
- **Vulkan Loader** (Khronos, MIT y Apache-2.0), descargado en Windows solo cuando falta `vulkan-1.dll`.
- **edge-tts** (LGPLv3), utilizado por el canal de doblaje de voz.
- **Modelos MarianMT** (Helsinki-NLP), descargados de Hugging Face Hub en el primer uso bajo sus propias licencias (Apache-2.0 para los modelos `opus-mt`, CC-BY-4.0 para `opus-mt-tc-big`).
