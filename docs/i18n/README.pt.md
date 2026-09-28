# 🎬 Video Translator AI

[Inglês](../../README.md) | [Todas as traduções](README.md)

**Leia esta página em:** [Bahasa Indonesia](README.id.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Magyar](README.hu.md) · [Nederlands](README.nl.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Suomi](README.fi.md) · [Svenska](README.sv.md) · [Tiếng Việt](README.vi.md) · [Türkçe](README.tr.md) · [Ελληνικά](README.el.md) · [Русский](README.ru.md) · [Українська](README.uk.md) · [العربية](README.ar.md) · [हिन्दी](README.hi.md) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Ferramenta de dublagem de voz de vídeo com tecnologia de IA que transcreve, traduz e redobra automaticamente vídeos em 26 idiomas, com opções de processamento local e sem necessidade de chaves de API por padrão. O reconhecimento de fala Whisper é executado localmente; Edge-TTS, Google Translate e DeepL requerem uma conexão com a internet. Recursos opcionais (DeepL, identificação de pessoas que falam (diarização)) podem exigir uma chave API ou token de acesso.

![A janela principal do Video Translator AI: reprodutor de vídeo e painéis de tradução](../../assets/screenshot.png)

> **v2.0** - pacote modular, tradução local do Ollama, orquestração de perfil de qualidade, metadados Python instaláveis e testes de integração opcionais com modelos reais. Consulte [Versões do GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases) e o histórico de commits para obter a lista completa de alterações.

> **v2.1.0** - instalador do Windows reforçado (tempo de execução do Microsoft Visual C++, um log de instalação claro, autoatualização a partir das Versões do GitHub), logs mais limpos (uma barra de progresso avançando por download), decodificação de vídeo por software em máquinas sem GPU, e botões de transporte elevados. Consulte [Versões do GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases).

## Como funciona

1. **Transcrição** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcreve o áudio (acelerado por GPU)
2. **Separação voz/música** - [Demucs](https://github.com/facebookresearch/demucs) isola os vocais da música de fundo
3. **Tradução** - MarianMT (local, off-line), Google Translate, DeepL Free ou **Ollama LLM** (Qwen3, traduções concisas com reconhecimento de slot)
4. **identificação de pessoas falando (diarização)** *(opcional)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifica quem está falando em cada segmento
5. **dublagem de voz** - [Edge-TTS](https://github.com/rany2/edge-tts) (mais de 400 vozes) ou [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (clonagem de voz, para cada locutor da conversa)
6. **Mixagem** - voz dublada mixada com música de fundo original
7. **Normalização** - áudio final normalizado para -23 LUFS (padrão de transmissão EBU R128)
8. **Lip Sync** *(opcional)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) sincroniza os movimentos da boca com o áudio dublado

## Recursos

- 🖥️ GUI temática (Tkinter) - não precisa de linha de comando; Temas Graphite, Slate, Light e Neon, cores de destaque, tamanho do texto e painéis de configurações que você pode reordenar arrastando
- 🕹️ **Temas divertidos** - aspetos lúdicos nas definições: Dex e Handheld lembram uma consola portátil (letra pixelizada, molduras grossas), CRT e CRT Amber um monitor de fósforo dos anos 80, com curvatura e linhas de varrimento também no vídeo
- 🔊 **Ouça antes de escolher** - um ícone de altifalante junto à voz reproduz uma frase de exemplo no idioma de destino (Edge-TTS) ou a amostra gratuita de uma voz ElevenLabs
- 🌍 **26 idiomas de destino** com múltiplas vozes por idioma
- 🌐 **UI em 26 idiomas** - a própria interface se adapta ao seu idioma
- 🎬 **Suporte para YouTube e URL** - cole qualquer link do YouTube e traduza diretamente (desenvolvido por yt-dlp)
- ▶️ **Reprodutor de vídeo integrado** (libmpv/mpv) - controles de transporte codificados por cores, lista de reprodução, áudio A/B original vs dublado, alternância de legendas, instantâneo, tela cheia, pasta aberta
- ⏱️ **Tradução em tempo real** - veja um ficheiro local ou uma ligação de vídeo a pedido com legendas traduzidas e um controlo de atraso; motores MarianMT / Google / DeepL / Ollama. A dobragem usa o Edge-TTS ou, opcionalmente, vozes ElevenLabs através de uma segunda instância do mpv; as frases sobrepostas esperam, aceleram ou desvanecem. As transmissões em direto ainda não são suportadas.
- 🎵 Separação voz/música via Demucs (mantém a música de fundo)
- 🔇 **Silenciar áudio original**, disponível antes e durante a tradução ao vivo, silencia a trilha sonora do vídeo enquanto mantém a voz traduzida audível. Desative-o para restaurar o áudio original; ele é redefinido quando a sessão ao vivo termina.
- 🧠 **MarianMT** - tradução neural offline totalmente local (Helsinki-NLP, sem limites de taxa de solicitação, sem chave de API)
- 🤖 **Tradução Ollama LLM** *(novo na v2.0)* - LLM local (Qwen3, Llama, Mistral) produzindo traduções concisas com reconhecimento de slot para dublagem de voz natural, detecta automaticamente/instala/inicia/puxa o modelo no primeiro uso
- 🎙️ **Clonagem de voz** - Coqui XTTS v2 clona a pessoa que fala a voz do áudio original no idioma de destino (modelo de aproximadamente 1,8 GB), com velocidade adaptativa por segmento e repetição de múltiplas sementes em alucinações
- 👥 **identificação de pessoas falando (diarização)** - pyannote-audio 3.1 identifica múltiplas pessoas falando; XTTS clona cada voz separadamente
- 💋 **Lip Sync** - Wav2Lip GAN sincroniza os movimentos da boca com o áudio dublado (modelo de aproximadamente 416 MB)
- 🔊 **Normalização de áudio** - normalização automática de volume -23 LUFS (EBU R128)
- ✏️ Editor de legendas - revise e corrija as legendas antes da dublagem de voz
- 📦 Processamento em lote - traduza vários vídeos ou URLs de uma só vez
- ⚡ Aceleração de GPU via CUDA (volta para CPU automaticamente)
- 📄 Exportação opcional de legendas `.srt`
- 🔁 **DeepL Free** mecanismo de tradução (opcional - 500 mil caracteres/mês, requer chave de API gratuita)
- 🔧 **Instalação automática** - pacotes Python ausentes e ffmpeg são instalados automaticamente na primeira inicialização
- 🧮 **Modelos para este PC** - deteta CPU, RAM, GPU, VRAM e disco livre, recomenda modelos de reconhecimento de voz, tradução e voz para velocidade, equilíbrio ou qualidade, transfere e verifica os modelos Whisper e mede-os com o seu próprio vídeo
- 🗣️ **Vozes ElevenLabs** *(opcionais, online, pagas)* - vozes multilingues naturais para a dobragem ao vivo com a sua própria chave API; se a chave ou a quota falharem, o Edge-TTS assume
- 🧬 **Clonagem de voz com o Voicebox** *(opcional)* - clona a voz de quem fala através de um servidor local [Voicebox](https://github.com/jamiepine/voicebox) separado; se não estiver a correr, o vídeo usa o Edge-TTS

## Idiomas suportados

Árabe, Chinês, Tcheco, Dinamarquês, Holandês, Inglês, Finlandês, Francês, Alemão, Grego, Hindi, Húngaro, Indonésio, Italiano, Japonês, Coreano, Norueguês, Polonês, Português, Romeno, Russo, Espanhol, Sueco, Turco, Ucraniano, Vietnamita

## Catálogo de Voz

O catálogo de voz Edge-TTS é definido em `LANGUAGES` próximo ao topo de `video_translator_gui.py`. Esse dicionário é a fonte da verdade para nomes de idiomas de destino, botões de opção de voz da GUI e voz de fallback da CLI quando `--voice` é omitido.

As notas de Claude/manutenção do projeto refletem esse local em `CLAUDE.md` em **Voice Catalog Source Of Truth**, para que futuros agentes de código saibam onde atualizar as vozes e para onde o README aponta os usuários.

## Mecanismos de tradução

| Motor | Configuração | Limites | Qualidade |
|--------|-------|--------|---------|
| **Google Translate** *(padrão)* | Nenhum | Scraping não oficial - pode ser limitado em vídeos grandes | ★★★★ |
| **MarianMT** | Nenhum - baixa aproximadamente 298 MB por par de idiomas no primeiro uso | Nenhum - totalmente off-line após o download | ★★★★ |
| **DeepL Free** | Chave de API gratuita em [deepl.com](https://www.deepl.com/pro-api) | 500 mil caracteres/mês | ★★★★★ |
| **Ollama LLM** *(recomendado para dublagem de voz - novo na v2.0)* | Instalado automaticamente na primeira utilização (modelo Ollama de ~1 GB + 5 GB) | Nenhum - totalmente local | ★★★★★ |

> **MarianMT** usa modelos [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP), armazenados em cache localmente após o primeiro download. Requer idioma de origem explícito (detecção automática não suportada - selecione o idioma de origem manualmente). Os pacotes Python necessários (`sacremoses`, `sentencepiece`) são instalados automaticamente na primeira seleção, se estiverem ausentes.

> **Ollama LLM** *(novo na v2.0)* é o mecanismo recomendado para dublagem de voz porque produz traduções cientes do intervalo de tempo alvo. Onde MarianMT traduz literalmente e produz italiano/espanhol/francês cerca de 25% mais do que inglês (forçando compressão de áudio audível no TTS), o LLM é solicitado a manter cada segmento conciso e natural para entrega falada, alcançando uma proporção típica de 0,85-0,95 em relação à fonte. O modelo padrão é `qwen3:8b` (5,2 GB em disco, ~6 GB VRAM); `qwen3:4b` (~3 GB) é a opção leve, `qwen3:14b` a de qualidade superior. O pipeline detecta automaticamente o binário Ollama, instala-o automaticamente por meio do instalador oficial no primeiro uso (com pop-up de consentimento), inicia o daemon e extrai o modelo escolhido - sem necessidade de configuração manual. Muda automaticamente para Google Translate se alguma coisa estiver faltando.

## Clonagem de voz (XTTS v2)

Quando ativado, o aplicativo extrai a voz do locutor do vídeo original e a utiliza como referência para clonar a voz no idioma de destino.

- Idiomas suportados: AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Para os 9 idiomas restantes, o Edge-TTS é usado automaticamente como substituto
- Modelo (~1,8 GB) baixado automaticamente no primeiro uso para `~/.local/share/tts/`
- **Referência filtrada por VAD** (v1.4): 10-15 s de fala contínua selecionada do áudio original via [silero-vad](https://github.com/snakers4/silero-vad) para melhor qualidade de clonagem de voz
- **Velocidade de geração** configurável (`xtts_speed`, padrão `1.25`): valores mais altos reduzem artefatos de compactação de áudio pós-processamento quando o texto traduzido é maior que o slot de origem. Sintonize via `~/.config/videotranslatorai/config.json` ou CLI `--xtts-speed`
- Funciona em CUDA ou CPU

## identificação de pessoas falando (diarização) (pyannote-áudio)

Quando ativado, o aplicativo identifica quem está falando em cada segmento. Combinado com a clonagem de voz, a voz de cada locutor é clonada separadamente - ideal para entrevistas, podcasts e vídeos com várias pessoas.

- Requer um [token HuggingFace](https://huggingface.co/settings/tokens) gratuito (registro único)
- **Token armazenado com segurança** (v1.4) por meio do chaveiro do sistema operacional: Windows Credential Manager, macOS Keychain, Linux Secret Service. Migração automática do armazenamento JSON de texto simples anterior
- Após o primeiro download, funciona totalmente offline
- Modelo: `pyannote/speaker-diarization-3.1`

## Sincronização labial (Wav2Lip)

Quando ativado, o aplicativo aplica Wav2Lip GAN para sincronizar os movimentos da boca do sujeito com o áudio dublado - a pessoa parece falar o idioma traduzido.

- Modelo (~416 MB) e repositório clonados automaticamente no primeiro uso para `~/.local/share/wav2lip/`
- Funciona em CUDA (recomendado) ou CPU
- Aumenta significativamente o tempo de processamento
- Funciona melhor em vídeos com um rosto único e claramente visível

## Modelos para este PC

Definições avançadas > Modelo > **Modelos para este PC** abre uma janela que lê o hardware (CPU, RAM, GPU e VRAM utilizável, disco livre) sem alterar nada e recomenda um modelo para cada etapa: reconhecimento de voz para ficheiros e ao vivo, tradução e voz.

- Escolha **Velocidade**, **Equilibrado** ou **Qualidade**: cada recomendação apresenta os seus motivos.
- As restantes opções continuam selecionáveis e são avaliadas para este PC: cabe, no limite, grande demais, disco insuficiente ou serviço online.
- **Transferir** obtém um modelo Whisper em falta, com progresso e Cancelar, e verifica cada ficheiro com as somas de verificação do Hugging Face; nada é transferido antes de o premir.
- **Benchmark** mede o modelo escolhido no vídeo carregado (carregamento, primeira frase, velocidade); o áudio nunca sai do PC.
- **Aplicar** define os modelos; **Repor anteriores** recupera a escolha anterior. As GPU NVIDIA são usadas através de CUDA; as GPU AMD (ROCm) e Apple são mostradas, mas aí os modelos de voz correm na CPU.

## Voicebox (clonagem de voz por um servidor local)

[Voicebox](https://github.com/jamiepine/voicebox) (MIT) é um programa separado que clona vozes. Instale-o e inicie-o à parte; esta aplicação só chama a sua API local e nunca o instala.

- Definições avançadas > Clonagem de voz > **Voicebox**: defina o endereço (predefinido `http://127.0.0.1:17493`), o motor (`chatterbox` por predefinição) e prima **Verificar**.
- Para cada vídeo é clonada uma voz temporária a partir de uma amostra limpa de quem fala (uma por orador com a diarização), que depois é removida.
- Só é aceite um endereço neste PC, porque a API do Voicebox não tem autenticação.
- Se o Voicebox não responder ou não suportar a língua de destino, o vídeo é dobrado com o Edge-TTS.

## Requisitos

- Python 3.10+ (o instalador do Windows provisiona 3.11.9 automaticamente)
- Windows 10/11 (x64), Linux ou macOS
- **GPU NVIDIA fortemente recomendada** - veja a tabela de GPU abaixo
- 20 GB de espaço livre em disco para uma instalação completa (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg e todos os pacotes Python são instalados automaticamente** na primeira inicialização, se estiverem ausentes. Nenhuma configuração manual necessária.

**Dependência opcional do sistema** - `rubberband-cli` (Linux: `sudo apt install rubberband-cli`, macOS: `brew install rubberband`). Quando instalado, ele é usado para alongamento de tempo de preservação de pitch na banda de qualidade controlada por perfil (padrão 1,15-1,50, até 1,65 para conteúdo rígido), removendo o efeito "esquilo" residual em vozes XTTS clonadas. O pipeline funciona inalterado sem ele (fallback automático para ffmpeg `atempo`). Perfis de qualidade agora preferem tentativas extras de tradução curtas em vez de aceleração extrema de áudio.

### Suporte para GPU

O pipeline usa cinco componentes acelerados por GPU (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). A cobertura da GPU não é uniforme entre os fornecedores:

| GPU | Windows | Linux | Notas |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx ou mais recente, driver CUDA 12.4) | ✅ aceleração total | ✅ aceleração total | **Recomendado.** Todos os cinco componentes são executados em GPU. |
| **AMD** (Radeon) | ⚠️ incompleto (DirectML não suporta XTTS e faster-whisper) | ⚠️ parcial (ROCm funciona para Demucs/XTTS/pyannote mas faster-whisper suporta apenas CUDA) | Funciona, mas a transcrição Whisper permanece na CPU e domina o tempo total. |
| **Intel Arc** | ⚠️ suporte imaturo para PyTorch XPU | ⚠️ mesmo | Não testado. |
| **Nenhum (somente CPU)** | ✅ funciona | ✅ funciona | Espere **10-20× mais lento** do que em tempo real. Um clipe de 5 minutos pode levar mais de 50 minutos apenas para ser transcrito com Whisper large-v3. |

**VRAM NVIDIA recomendada:**

| VRAM | Placas gráficas comuns | Experiência |
|------|---------------|-----------|
| 6GB | GTX 1660, RTX 2060 | Utilizável, não é possível executar XTTS + Wav2Lip simultaneamente |
| 8GB | RTX 3060 Ti, 4060 | Pipeline completo, sem margem |
| **12GB+** | **RTX 3060 12GB, 4070, 4080** | **Recomendado - confortável** |
| 24GB | RTX 3090, 4090 | Capacidade extra para grandes lotes |

## Instalação

### Windows

Passo a passo, sem necessidade de linha de comando. Testado em um PC limpo com Windows 11.

1. **Baixe** o projeto: o botão verde **Código** → **Baixar ZIP**, ou o zip mais recente em [Versões do GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases). Extraia-o para qualquer pasta, por exemplo a área de trabalho.
2. **Instale**: clique com o botão direito em `setup_windows.bat` → **Executar como administrador** → pressione `1` (Install). Se o SmartScreen disser "O Windows protegeu o seu PC", clique em **Mais informações** → **Executar mesmo assim**: o script é texto simples, você pode abri-lo com o Bloco de Notas.
3. **Aguarde**: em um PC limpo com conexão rápida leva cerca de 15 minutos e 8 GB de disco. O instalador baixa e configura, nesta ordem:
   - Python 3.11 (em todo o sistema) e o tempo de execução do Microsoft Visual C++, quando ausente
   - os pacotes Python: PyTorch (CUDA 12.4 com uma GPU NVIDIA; caso contrário, a versão para CPU), faster-whisper, Demucs, coqui-tts, pyannote e a pilha do Wav2Lip
   - Git for Windows (para o Wav2Lip), ffmpeg e o reprodutor de vídeo integrado (libmpv em `mpv-runtime`; opcional, todo o resto funciona sem ele)
   - um **atalho na área de trabalho** para cada conta do Windows no PC e uma pasta no **Menu Iniciar** com o aplicativo e **Atualizar Video Translator AI**
4. **Inicie** a partir do atalho na área de trabalho ou do Menu Iniciar. Sem uma GPU NVIDIA, o aplicativo funciona na CPU, só que mais devagar: escolha um modelo Whisper pequeno.

> Tudo é instalado em todo o sistema em `%ProgramFiles%\VideoTranslatorAI`, para que qualquer usuário do Windows na máquina encontre o atalho pronto. Cada execução de `setup_windows.bat` grava um log em `%USERPROFILE%\VideoTranslatorAI-setup.log`: anexe-o ao relatar um problema. Se o instalador terminar com **INSTALAÇÃO INCOMPLETA**, execute-o novamente e escolha `[2] Repair / Update`. As ferramentas VS C++ Build Tools não são necessárias: o fork `coqui-tts` mantido fornece rodas pré-compiladas.

### Linux/macOS

```bash
# Clonar o repositório
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Opcional: instale a pilha NVIDIA CUDA 12.4 PyTorch testada antecipadamente
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Opcional: pré-instale todos os pacotes de tempo de execução do Python em vez de deixar a GUI
# instale pacotes ausentes na primeira execução
pip install --break-system-packages -r requirements.txt

# Opcional: o reprodutor de vídeo integrado (libmpv da distribuição, python-mpv do PyPI)
sudo apt install libmpv2        # Fedora: mpv-libs, Arch: mpv, openSUSE: libmpv2
pip install --break-system-packages -r requirements-player.txt

# Opcional: instale o projeto como um pacote Python editável
pip install --break-system-packages --no-deps -e .

# Iniciar da fonte
python video_translator_gui.py

# Ou, após a instalação do pacote/editável
videotranslatorai
videotranslatorai --preflight
```

> Na primeira inicialização, a GUI detecta quaisquer pacotes ausentes (faster-whisper, Demucs, Edge-TTS, etc.) e os instala automaticamente, transmitindo a saída para a janela de log. ffmpeg também é instalado automaticamente via `apt-get` / `dnf` / `pacman` (Linux) ou baixado do GitHub (Windows).

> O cabeçalho mostra um emblema de **Jogador**. Quando libmpv ou python-mpv está faltando, o painel esquerdo diz o que está faltando e oferece **Instalar player**: no Linux ele usa o gerenciador de pacotes através do pkexec (então `sudo -n`) e mostra o comando manual quando nenhum deles funciona; no Windows ele pergunta antes de baixar o libmpv para o usuário atual (cerca de 32 MB).

### Perfis de requisitos

| Arquivo | Objetivo |
|------|---------|
| `requirements.txt` | Instalação de tempo de execução completa e compatível com versões anteriores. |
| `requirements-core.txt` | Pacotes de pipeline padrão usados pela GUI/CLI. |
| `requirements-optional.txt` | XTTS, tokenizadores MarianMT, diarização, VAD, chaveiro. |
| `requirements-wav2lip.txt` | Tempo de execução Wav2Lip e pilha de detecção de rosto (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Pilha PyTorch testada com rodas NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Reprodutor de vídeo integrado: python-mpv (precisa de libmpv do sistema ou do instalador do Windows). |
| `requirements-dev.txt` | Dependências leves usadas por testes de CI/unidade. |

## Atualizar

### Windows

Menu Iniciar → **Video Translator AI** → **Atualizar Video Translator AI** (pede privilégios de administrador), ou execute `setup_windows.bat` como administrador e escolha `[2] Repair / Update`. O instalador verifica as [Versões do GitHub](https://github.com/HeartB1t/VideoTranslatorAI/releases): quando existe uma versão mais recente, baixa a versão, verifica sua soma de verificação SHA256 e a instala; caso contrário, repara os arquivos atuais. Suas configurações, chaves salvas, modelos baixados e vídeos traduzidos são mantidos. Sem conexão com a internet, a atualização é ignorada e o reparo continua.

### Linux/macOS

```bash
cd VideoTranslatorAI
git pull
pip install --break-system-packages -r requirements.txt
```

## Desinstalar

### Windows

Execute `setup_windows.bat` (clique com o botão direito → **Executar como administrador**) e escolha `[3] Uninstall` no menu. São oferecidos três submodos de desinstalação:

| Modo | Administrador necessário | Escopo |
|------|----------------|-------|
| **[1] Desinstalação completa - um clique** | ✅ | Remove a pasta do aplicativo, o atalho da área de trabalho e as entradas do Menu Iniciar, ffmpeg do PATH da máquina, o cache do modelo HF de cada usuário (Whisper/XTTS) e configuração (`HF token`) e todos os pacotes Python AI instalados pelo instalador. No final, ele também pergunta (aceita) se deseja desinstalar silenciosamente **Python 3.11** e **Git for Windows** por meio de suas strings de desinstalação silenciosa do registro. Ao desinstalar o Python 3.11, também são removidos os pacotes que o pip instalou para ele na pasta do usuário atual (`%APPDATA%\Python\Python311`), a menos que outro Python 3.11 continue instalado. |
| **[2] Somente usuário atual** | ❌ | Remove apenas a configuração VTAI do usuário em execução, o cache HF/XTTS e a instalação legada por usuário. **Deixa intacta a instalação de todo o sistema** para que outras contas do Windows no PC possam continuar usando o aplicativo. |
| **[3] Personalizado - granular** | ✅ para itens do sistema, ❌ para itens do usuário | Solicitação Y/N para cada categoria: pasta do aplicativo, atalho, PATH da máquina, instalações legadas por usuário, configurações/caches por usuário e, em seguida, pacotes Python agrupados (TTS, pilha PyTorch, Whisper+ctranslate2, Demucs, Wav2Lip deps, pyannote, utilitários de pipeline) e, finalmente, Python 3.11 e Git opcionais. |

Cada modo remove também o que o programa guarda para o utilizador: configuração e registos diários (`%APPDATA%\VideoTranslatorAI`), dados do programa com os runtimes do leitor, de JavaScript e do Wav2Lip (`%LOCALAPPDATA%\VideoTranslatorAI`), ficheiros temporários do tempo real (`%TEMP%\VideoTranslatorAI`), os modelos MarianMT e as chaves guardadas (token HF, ElevenLabs) do Gestor de Credenciais do Windows. As chaves são guardadas por conta Windows: cada conta remove as suas com `[2]`.

**Nunca removido automaticamente:** Ferramentas de compilação do Visual Studio C++ (se presentes em execuções mais antigas) e o tempo de execução do Microsoft Visual C++, compartilhado por outros programas. Use *Aplicativos e recursos* nas Configurações do Windows para removê-los manualmente, se desejar. O log de instalação `%USERPROFILE%\VideoTranslatorAI-setup.log` é mantido de propósito.

### Linux/macOS

Nenhum desinstalador dedicado - remova manualmente:

```bash
# Pacotes Python instalados pelo instalador automático da GUI
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Dados do usuário e caches de modelo
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip ~/.cache/wav2lip
rm -rf ~/.config/videotranslatorai          # config (temas, ordem do painel, configurações)
rm -rf ~/.local/share/fonts/VideoTranslatorAI   # tipos de letra dos temas divertidos
rm -rf ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt*   # modelos de tradução MarianMT
rm -rf ~/.local/share/VideoTranslatorAI                          # dados do programa (runtime JavaScript para o yt-dlp)
rm -rf "${TMPDIR:-/tmp}/VideoTranslatorAI"                       # ficheiros temporários do tempo real
# chaves guardadas (token HF, ElevenLabs)
python3 -c "import keyring; [keyring.delete_password('VideoTranslatorAI', u) for u in ('hf_token', 'elevenlabs_api_key') if keyring.get_password('VideoTranslatorAI', u)]"
rm -f  ~/.videotranslatorai_config.json     # configuração legada de versões <= 1.9, se presente
```

## Uso

### Diagnóstico

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Executa diagnósticos do ambiente local sem iniciar a tradução ou instalar nada. `--preflight-lipsync` trata os pacotes faciais Wav2Lip conforme necessário, o que é útil antes de ativar o **Lip Sync**. A GUI expõe a mesma verificação básica do botão **Diagnóstico** do painel de log. `--preflight-player` trata o player de vídeo integrado (python-mpv e um libmpv carregável) conforme necessário. `python -m videotranslator.libmpv_runtime check` investiga apenas libmpv (saída 0 pronta, 2 indisponível).

**Ficheiro de registo:** tudo o que o painel de registo mostra (cada clique e escolha, resultados, passos do processamento, erros com os detalhes) é também guardado em `logs/videotranslator.log` junto da configuração: `~/.config/videotranslatorai/logs/` no Linux, `%APPDATA%\VideoTranslatorAI\logs\` no Windows. Um ficheiro por dia, guardam-se os últimos 7 dias; o botão **Diagnóstico** mostra o caminho. Anexe-o quando comunicar um problema. As chaves de API e o texto escrito nos campos nunca são registados. Cada linha mostra a hora, o nível (informação, aviso, erro, no idioma da interface, com avisos e erros coloridos no painel) e a área, por exemplo [ui] para cliques, [job] para traduções, [live] para tempo real; cada arranque escreve um cabeçalho com versão, sistema, GPU e definições.

### GUI

```bash
python video_translator_gui.py
```

**Layout:** as configurações de tradução em lote ficam na coluna à direita, como uma pilha de painéis de configurações: **Entrada**, **Tradução**, **Perfil de fluxo de trabalho**, **Iniciar** e as seções avançadas recolhíveis (modelo, mecanismo de tradução, áudio, clonagem de voz, sincronização labial, diarização, opções, hotwords). A grande área à esquerda é o **player de vídeo integrado** (transporte, lista de reprodução, áudio A/B original versus áudio dublado, legendas, instantâneo, tela cheia), com a barra de **tradução em tempo real** abaixo dela. Arraste um cartão pelo título ou pela alça **≡** para movê-lo para cima ou para baixo na coluna; o pedido é salvo (`ui_panel_order`) e restaurado na próxima inicialização. O painel de registro na parte inferior pode ser ocultado com **Ocultar registro**. Ao iniciar, a janela abre centralizada no monitor atual (aquele sob o ponteiro) e maximizada, para que se comporte bem em uma configuração de vários monitores.

**Controles do player de vídeo:** os ícones usam cores funcionais consistentes em cada tema, independentemente da cor de destaque selecionada:

| Controle | Cor |
|---------|--------|
| Reproduzir vídeo | Verde |
| Pausa (substitui Play durante o jogo) | Âmbar |
| Parar a reprodução | Vermelho coral |
| Anterior/voltar 10 s/avançar 10 s/próximo | Azul |
| Instantâneo | Violeta |
| Abrir pasta | Ouro |

Passar o mouse adiciona um fundo colorido sutil. Os controles indisponíveis são neutros; a navegação da lista de reprodução permanece utilizável após Parar. As dicas de ferramentas e os indicadores de foco do teclado permanecem disponíveis, portanto a cor não é a única maneira de identificar ações.

**De arquivos locais:**
1. Clique em **Adicionar** para selecionar um ou mais arquivos de vídeo
2. Escolha o idioma de origem e de destino
3. Abra a seção **Modelo** e selecione um modelo Whisper (`small` é um bom equilíbrio entre velocidade/precisão)
4. Escolha uma voz e ajuste a velocidade do TTS, se necessário
5. *(Opcional)* Em **Mecanismo de tradução** selecione **Google** (padrão), **MarianMT** (local/off-line), **DeepL Free** ou **Ollama LLM** (local, recomendado para dublagem de voz)
6. *(Opcional)* Ativar **Clonagem de voz** (XTTS v2) e/ou **identificação de pessoas falando (diarização)**
7. *(Opcional)* Ativar **Sincronização labial** (Wav2Lip)
8. Clique em **Iniciar tradução**

**Do YouTube (ou qualquer site compatível):**
1. Cole um ou mais URLs no campo **URL** (um por linha)
2. Configure idioma, modelo e voz normalmente
3. Clique em **⬇ Baixar e Traduzir**

> yt-dlp suporta YouTube, Vimeo, Twitter/X, TikTok e [mais de 1000 outros sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Aviso de uso justo:** baixar vídeos via yt-dlp é considerado acesso automatizado por plataformas como o YouTube e pode violar seus Termos de Serviço. O uso intenso ou repetido do mesmo endereço IP pode resultar em bloqueios temporários (HTTP 429/erros de login obrigatório). Use uma VPN ou alterne seu IP se encontrar falhas de download. Esta ferramenta destina-se apenas ao uso pessoal e não comercial. A redistribuição de conteúdo traduzido pode infringir direitos autorais - respeite sempre os direitos do criador original.

### Tradução em tempo real (legendas e dublagem experimental de voz)

Assista a um arquivo local ou a um link de vídeo sob demanda resolvido com legendas traduzidas e tradução falada opcional. Use a barra abaixo do player:

**De um link:**

1. Cole um link no campo **URL**
2. Defina o idioma de origem e de destino, escolha uma voz e ajuste o controle deslizante **Atraso**
3. Selecione **Voz dublada** e/ou **Legendas**
4. Para ouvir apenas a voz traduzida, selecione **Silenciar áudio original** antes de começar (em italiano: **Silenzia originale**, ao lado da caixa de seleção da legenda)
5. Clique em **Traduzir em tempo real** - o link é resolvido e a tradução começa

**De um arquivo carregado:** carregue um vídeo no player (Entrada -> Adicionar e selecione-o), deixe o campo URL vazio, escolha as mesmas configurações ao vivo e clique em **Traduzir em tempo real**. Um URL tem prioridade quando o campo não está vazio.

- **Mecanismo:** MarianMT (off-line, padrão), Google, DeepL ou Ollama. O reconhecimento de fala (Whisper) é executado localmente. Os modelos offline precisam de um download inicial.
- **Atraso:** num ficheiro em modo diferido, quantos segundos de tradução ficam em reserva antes de a imagem retomar após uma pausa (pelo menos 8 s com voz, 4 s só com legendas). Se a imagem continuar a parar, a reserva cresce 4 s até 30 s e a barra indica-o.
- **Dublagem de voz:** reprodução experimental de fala Edge-TTS por meio de uma segunda instância mpv. Requer acesso à Internet e é independente da clonagem de voz em lote.
- **Voz ElevenLabs:** opcional, em Definições avançadas > Clonagem de voz > **Voz ao vivo ElevenLabs**. Introduza a sua chave API, verifique-a, escolha um modelo que fale a língua de destino e uma voz. O texto traduzido é enviado para o ElevenLabs (pago por carácter); a chave fica no porta-chaves do sistema. Se a chave ou a quota falharem, o Edge-TTS continua. Também abre a partir do botão **ElevenLabs…** da barra em tempo real, cuja linha indica que voz a dobragem vai usar.
  - Plano gratuito do ElevenLabs (verificado a 27 de setembro de 2026): pela API só funcionam as vozes predefinidas (Roger, Sarah, George, River...), com 10.000 caracteres por mês e no máximo 4 pedidos em simultâneo. A janela assinala as vozes que exigem um plano pago.
  - As vozes da biblioteca do ElevenLabs, as vozes clonadas e mais caracteres exigem uma subscrição paga do ElevenLabs, comprada ao ElevenLabs segundo os seus próprios preços e condições ([ElevenLabs pricing](https://elevenlabs.io/pricing)). O VideoTranslatorAI continua gratuito, não é afiliado ao ElevenLabs e não precisa dele: o Edge-TTS é a voz gratuita predefinida.
  - Modelos para tempo real, primeiro áudio após cerca de: Flash v2.5 0,2 s, Turbo v2.5 0,2 s, v3 Conversational 0,4 s. Multilingual v2 (0,9 s) e v3 (1-2 s) soam mais ricos mas ficam atrás do vídeo; Turbo v2 e Flash v2 só falam inglês.
  - Quando o ElevenLabs recusa uma fala (chave, plano, voz ou modelo inexistente, idioma, caracteres esgotados, pedidos a mais), a barra em tempo real diz porquê e o registo guarda a mensagem original do ElevenLabs.
- **Silenciar áudio original:** disponível antes do início e durante a tradução. Silencia toda a trilha sonora original, incluindo música e efeitos, mas deixa a voz traduzida audível. Não isola a pessoa que fala no áudio original. Desative-o para restaurar a trilha sonora; ele é redefinido quando a sessão ao vivo termina. O botão do alto-falante do player é o mudo geral, não esse controle independente.
- **Pausar e buscar:** os controles do player de vídeo estão conectados à sessão ao vivo; a sincronização de áudio ponta a ponta ainda precisa de testes de aceitação específicos da plataforma.
- **Limites atuais:** a calibração do tempo do áudio e a validação no Windows continuam por concluir. As transmissões em direto ainda em curso não são suportadas; a etiqueta do modo em direto não implica a receção progressiva de uma transmissão em curso.

Para um vídeo dublado salvo, use **Baixar e traduzir** / **Iniciar tradução** em vez da visualização em tempo real.

### Blocos de mecanismo de tradução e VPN

Podem acontecer dois bloqueios diferentes, com soluções diferentes:

| Bloquear | Sintoma | Correção |
|-------|---------|-----|
| **Baixar** (yt-dlp) | "Faça login para confirmar que você não é um bot", HTTP 429 | **VPN** / gire o IP ou faça login no YouTube em seu navegador (os cookies são lidos automaticamente) |
| **Tradução** (endpoint gratuito do Google) | "Google Translate não pôde traduzir... taxa de solicitação limitada/bloqueada" | Use **MarianMT** (offline) ou **Ollama** (local) - sem limite de taxa de solicitação. Uma VPN também ajuda. O fluxo em lote agora **volta para MarianMT automaticamente** quando o Google é bloqueado. |

### Temas e aparência

Clique no ícone de engrenagem no cabeçalho para abrir **Configurações**:

- **Tema**: Automático (segue o modo claro/escuro do sistema operacional), Graphite (padrão), Slate, Light, Neon.
- **Temas divertidos**: Dex e Handheld (consola portátil, letra pixelizada, molduras grossas), CRT e CRT Amber (monitor de fósforo dos anos 80; o vídeo também ganha curvatura e linhas de varrimento através de um shader do mpv). O Graphite continua a ser o predefinido.
- **Cor de destaque**: padrão por tema ou azul, verde-azulado, violeta, verde, âmbar, rosa.
- **Tamanho do texto**: pequeno, normal, grande, extra grande.
- **Idioma da interface**: 26 idiomas.

As alterações são aplicadas imediatamente, sem reinicialização, e são salvas no arquivo de configuração (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Restaurar padrões** traz de volta o tema Graphite, o acento padrão, o tamanho normal do texto e a ordem padrão dos painéis de configurações.

### Linha de comando

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Todas as opções:**

| Opção CLI | Descrição | Padrão |
|------|-------------|---------|
| `--lang-source` | Idioma de origem (`auto` para detecção automática) | `auto` |
| `--lang-target` | Código do idioma de destino (por exemplo, `it`, `fr`, `de`) | `it` |
| `--voice` | Nome de voz Edge-TTS | auto |
| `--model` | Modelo Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Ajuste de velocidade TTS (por exemplo, `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` ou `deepl` | `google` |
| `--deepl-key` | Chave de API DeepL Free | - |
| `--diarize` | Habilitar identificação de pessoas falando (diarização) (pyannote) | - |
| `--hf-token` | Token HuggingFace para diarização | - |
| `--lipsync` | Aplicar sincronização labial Wav2Lip após dublagem de voz | - |
| `--subs-only` | Gere apenas `.srt`, pule a dublagem de voz | - |
| `--no-subs` | Pular geração `.srt` | - |
| `--no-demucs` | Pular separação voz/música | - |
| `--output` / `-o` | Caminho do arquivo de saída | auto |
| `--output-dir` | Pasta para arquivos traduzidos (um só lugar, Windows e Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Processar vários arquivos | - |
| `--voicebox` | Clona a voz através de um servidor Voicebox em execução | - |
| `--voicebox-url` | Endereço do Voicebox | `http://127.0.0.1:17493` |
| `--voicebox-engine` | Motor do Voicebox (`chatterbox`, `qwen`, ...) | `chatterbox` |

### testes de integração com modelos reais

O conjunto de testes padrão evita downloads de modelos reais e longos trabalhos de GPU. Para executar verificações empíricas de aceitação para a pilha local instalada:

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Essas verificações validam importações reais de Wav2Lip, disponibilidade de Torch CUDA, disponibilidade de daemon Ollama e faster-Whisper em fala sintética. Eles falham ou ignoram intencionalmente quando o estado do driver/daemon/modelo local não está pronto.

**Exemplos:**

```bash
# Traduza vídeo italiano para inglês com MarianMT local
# (baixa o modelo de aproximadamente 298 MB no primeiro uso e depois totalmente off-line)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Traduzir com clonagem de voz + identificação de quem fala (diarização)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Traduzir com sincronização labial
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Apenas legendas (sem dublagem de voz)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Modelos Whisper

| Modelo | Tamanho | Velocidade | Precisão |
|-------|------|-------|----------|
| tiny | 75MB | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145MB | ⚡⚡⚡ | ★★☆☆ |
| small | 465MB | ⚡⚡ | ★★★☆ |
| medium | 1,5GB | ⚡ | ★★★★ |
| large-v2/v3 | 3GB | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6GB | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` é uma versão destilada de `large-v3` (4 camadas decodificadoras vs 32) - qualidade quase grande com velocidade aproximada de nível `medium`. Padrão recomendado em uma GPU moderna quando a velocidade de transcrição é importante; a queda na qualidade do material multilíngue é pequena.

> Os modelos são baixados automaticamente na primeira utilização.

> Não sabe que modelo serve para o seu PC? Abra **Modelos para este PC** nas definições do modelo: recomenda um com base no hardware e pode medi-lo.

## CLIs de módulos independentes

O pacote modular expõe quatro ferramentas voltadas para o usuário que podem ser invocadas diretamente sem iniciar o pipeline completo:

```bash
# Faça um pré-voo de um vídeo para presença facial (o Wav2Lip pularia se estivesse ausente).
python3 -m videotranslator.face_detector path/to/video.mp4
# saída 0 = rosto presente, saída 1 = sem rosto

# Analise um *_metrics.csv produzido por build_dubbed_track.
# Relatórios P50/P75/P90/P95 de pre_stretch_ratio, quebra de banda de audibilidade,
# esticar o uso do mecanismo e os N piores valores discrepantes com seu texto de destino.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Limpe o texto para TTS (reescreve dois pontos, ponto e vírgula, reticências, travessões).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Estime a dificuldade de dublagem de voz de um arquivo de segmentos .srt ou .json ANTES de executar o TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Cada ferramenta possui `-h`/`--help` para opções completas. Eles são independentes e reutilizam os mesmos módulos dos quais o pipeline de dublagem de voz depende, para que sua saída permaneça consistente com o tempo de execução.

## Licença

MIT

### Componentes de terceiros

O código do repositório é MIT. Os instaladores baixam os componentes abaixo de suas próprias fontes no momento da instalação; o projeto não os redistribui.

- **libmpv** (https://github.com/mpv-player/mpv), o mecanismo do reprodutor de vídeo integrado. Windows: a compilação LGPL de zhongfly (https://github.com/zhongfly/mpv-winbuild) é testada primeiro; uma compilação GPL fixada por shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) é a alternativa. `mpv-runtime\BUILD.txt` registra a fonte, o tipo de licença e o commit mpv, e o texto da licença fica próximo à DLL. Linux: o pacote de distribuição (`libmpv2`, `libmpv1`, `mpv-libs` ou `mpv`).
- **FFmpeg** dentro do libmpv (LGPL ou GPL, seguindo a compilação do libmpv).
- **python-mpv** (`mpv` em PyPI), GPLv2+ ou LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), usado pelo instalador do Windows para extrair libmpv e excluído posteriormente.
- **Carregador Vulkan** (Khronos, MIT e Apache-2.0), baixado no Windows somente quando `vulkan-1.dll` está faltando.
- **edge-tts** (LGPLv3), usado pelo pipeline de dublagem de voz.
- **Modelos MarianMT** (Helsinki-NLP), baixados do Hugging Face Hub no primeiro uso sob suas próprias licenças (Apache-2.0 para os modelos `opus-mt`, CC-BY-4.0 para `opus-mt-tc-big`).
- **Voicebox** (MIT, https://github.com/jamiepine/voicebox), opcional, instalado à parte pelo utilizador; os seus motores têm licenças próprias (Chatterbox MIT com marca de água de áudio, pesos TADA sob a Llama 3.2 Community License).
- **ElevenLabs** (https://elevenlabs.io), serviço online opcional usado com a conta e a chave API do utilizador, nos seus próprios termos.
- Tipos de letra **Pixelify Sans** e **VT323** (SIL Open Font License 1.1), usados pelos temas divertidos: os únicos ficheiros de terceiros incluídos no repositório, em `assets/fonts` junto dos textos das licenças.
