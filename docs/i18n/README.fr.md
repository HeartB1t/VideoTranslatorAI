# 🎬 Video Translator AI

[Français](../../README.md) | [Toutes les traductions](README.md)

**Lire cette page dans :** [العربية](README.ar.md) · [中文](README.zh.md) · [Čeština](README.cs.md) · [Dansk](README.da.md) · [Nederlands](README.nl.md) · [Suomi](README.fi.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Ελληνικά](README.el.md) · [हिन्दी](README.hi.md) · [Magyar](README.hu.md) · [Bahasa Indonesia](README.id.md) · [Italiano](README.it.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Norsk](README.no.md) · [Polski](README.pl.md) · [Português](README.pt.md) · [Română](README.ro.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Svenska](README.sv.md) · [Türkçe](README.tr.md) · [Українська](README.uk.md) · [Tiếng Việt](README.vi.md)

[![tests](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml/badge.svg)](https://github.com/HeartB1t/VideoTranslatorAI/actions/workflows/tests.yml)

Outil de doublage vocal vidéo alimenté par l'IA qui transcrit, traduit et redouble automatiquement les vidéos dans 26 langues, avec des options de traitement local et aucune clé API requise par défaut. La reconnaissance vocale Whisper s'exécute localement ; Edge-TTS, Google Translate et DeepL nécessitent une connexion Internet. Les fonctionnalités optionnelles (DeepL, identification des personnes parlant (diarisation)) peuvent nécessiter une clé API ou un jeton d'accès.

> **v2.0** - package modulaire, traduction Ollama locale, orchestration de profil de qualité, métadonnées Python installables et tests d'intégration opt-in avec des modèles réels. Voir [GitHub Releases](https://github.com/HeartB1t/VideoTranslatorAI/releases) et l'historique des validations pour la liste complète des modifications.

## Comment ça marche

1. **Transcription** - [faster-Whisper](https://github.com/SYSTRAN/faster-whisper) transcrit l'audio (accélération GPU)
2. **Séparation voix/musique** - [Demucs](https://github.com/facebookresearch/demucs) isole les voix de la musique de fond
3. **Traduction** - MarianMT (local, hors ligne), Google Translate, DeepL Free ou **Ollama LLM** (Qwen3, traductions concises compatibles avec les emplacements)
4. **identification des personnes qui parlent (diarisation)** *(facultatif)* - [pyannote-audio](https://github.com/pyannote/pyannote-audio) identifie qui parle dans chaque segment
5. **doublage vocal** - [Edge-TTS](https://github.com/rany2/edge-tts) (plus de 400 voix) ou [Coqui XTTS v2](https://github.com/coqui-ai/TTS) (clonage vocal, pour chaque intervenant de la conversation)
6. **Mixage** - voix doublée mixée avec une musique de fond originale
7. **Normalisation** - audio final normalisé à -23 LUFS (norme de diffusion EBU R128)
8. **Lip Sync** *(facultatif)* - [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) synchronise les mouvements de la bouche avec l'audio doublé

## Caractéristiques

- 🖥️ Interface graphique thématique (Tkinter) - aucune ligne de commande nécessaire ; Thèmes Graphite, Slate, Light et Neon, couleurs d'accentuation, taille du texte et panneaux de paramètres que vous pouvez réorganiser en faisant glisser
- 🌍 **26 langues cibles** avec plusieurs voix par langue
- 🌐 **UI en 26 langues** - l'interface elle-même s'adapte à votre langue
- 🎬 **Support YouTube et URL** - collez n'importe quel lien YouTube et traduisez directement (propulsé par yt-dlp)
- ▶️ **Lecteur vidéo intégré** (libmpv/mpv) - commandes de transport à code couleur, liste de lecture, audio A/B original ou doublé, basculement des sous-titres, instantané, plein écran, dossier ouvert
- ⏱️ **Traduction en temps réel** - regardez un fichier local ou un lien vidéo résolu à la demande avec des sous-titres traduits et un curseur de délai de style YouTube ; moteurs MarianMT / Google / DeepL / Ollama. Le doublage vocal expérimental utilise Edge-TTS et une deuxième instance mpv. La gestion du chevauchement vocal et l’acceptation réelle de l’audio/Windows restent en cours ; les diffusions en direct croissantes ne sont pas encore prises en charge. Consultez le [état de mise en œuvre en direct](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).
- 🎵 Séparation voix/musique via Demucs (conserve la musique de fond)
- 🔇 **Muet l'audio original**, disponible avant et pendant la traduction en direct, coupe la bande sonore de la vidéo tout en gardant la voix traduite audible. Désactivez-le pour restaurer l'audio d'origine ; il se réinitialise à la fin de la session en direct.
- 🧠 **MarianMT** - traduction neuronale entièrement locale et hors ligne (Helsinki-NLP, pas de limite de débit de requête, pas de clé API)
- 🤖 **Traduction Ollama LLM** *(nouveau dans la v2.0)* - LLM local (Qwen3, Llama, Mistral) produisant des traductions concises compatibles avec les slots pour le doublage vocal naturel, détecte/installe/démarre/extrait automatiquement le modèle lors de la première utilisation
- 🎙️ **Clonage vocal** - Coqui XTTS v2 clone la personne qui parle avec la voix de l'audio d'origine dans la langue cible (modèle de ~ 1,8 Go), avec une vitesse adaptative par segment et une nouvelle tentative multi-graines sur les hallucinations
- 👥 **identification des personnes parlant (diarisation)** - pyannote-audio 3.1 identifie plusieurs personnes parlant ; XTTS clone chaque voix séparément
- 💋 **Lip Sync** - Wav2Lip GAN synchronise les mouvements de la bouche avec l'audio doublé (modèle ~ 416 Mo)
- 🔊 **Normalisation audio** - normalisation automatique du volume sonore -23 LUFS (EBU R128)
- ✏️ Éditeur de sous-titres - vérifiez et corrigez les sous-titres avant le doublage vocal
- 📦 Traitement par lots : traduisez plusieurs vidéos ou URL à la fois
- ⚡ Accélération GPU via CUDA (revient automatiquement au CPU)
- 📄 Exportation facultative des sous-titres `.srt`
- 🔁 **DeepL Free** Moteur de traduction (facultatif - 500 000 caractères/mois, nécessite une clé API gratuite)
- 🔧 **Installation automatique** - les packages Python manquants et ffmpeg sont installés automatiquement au premier lancement

## Langues prises en charge

arabe, chinois, tchèque, danois, néerlandais, anglais, finnois, français, allemand, grec, hindi, hongrois, indonésien, italien, japonais, coréen, norvégien, polonais, portugais, roumain, russe, espagnol, suédois, turc, ukrainien, vietnamien

## Catalogue vocal

Le catalogue vocal Edge-TTS est défini dans `LANGUAGES` en haut de `video_translator_gui.py`. Ce dictionnaire est la source de vérité pour les noms de langue cible, les boutons radio vocaux de l'interface graphique et la voix de secours CLI lorsque `--voice` est omis.

Les notes de maintenance de Claude/projet reflètent cet emplacement dans `CLAUDE.md` sous **Voice Catalog Source Of Truth**, afin que les futurs agents de code sachent où mettre à jour les voix et où le README pointe les utilisateurs.

## Moteurs de traduction

| Moteur | Configuration | Limites | Qualité |
|--------|-------|--------|---------|
| **Google Translate** *(par défaut)* | Aucun | Scraping non officiel - peut être limité sur les grandes vidéos | ★★★★ |
| **MarianMT** | Aucun - téléchargements ~ 298 Mo par paire de langues lors de la première utilisation | Aucun - entièrement hors ligne après le téléchargement | ★★★★ |
| **DeepL Free** | Clé API gratuite sur [deepl.com](https://www.deepl.com/pro-api) | 500 000 caractères/mois | ★★★★★ |
| **Ollama LLM** *(recommandé pour le doublage vocal - nouveau dans la v2.0)* | Auto-installé lors de la première utilisation (~ 1 Go Ollama + modèle 5 Go) | Aucun - entièrement local | ★★★★★ |

> **MarianMT** utilise des modèles [Helsinki-NLP/opus-mt](https://huggingface.co/Helsinki-NLP), mis en cache localement après le premier téléchargement. Nécessite une langue source explicite (détection automatique non prise en charge - sélectionnez la langue source manuellement). Les packages Python requis (`sacremoses`, `sentencepiece`) sont installés automatiquement lors de la première sélection s'ils sont manquants.

> **Ollama LLM** *(nouveau dans la v2.0)* est le moteur recommandé pour le doublage vocal car il produit des traductions tenant compte du créneau horaire cible. Là où MarianMT traduit littéralement et produit l'italien/espagnol/français environ 25 % plus longtemps que l'anglais (forçant une compression audio audible sur le TTS), le LLM est invité à garder chaque segment concis et naturel pour la diffusion orale, atteignant un rapport de caractères typique de 0,85 à 0,95 par rapport à la source. Le modèle par défaut est `qwen3:8b` (5,2 Go sur disque, ~6 Go de VRAM) ; `qwen3:4b` (~ 3 Go) est l'option légère, `qwen3:14b` celle de qualité supérieure. Le pipeline détecte automatiquement le binaire Ollama, l'installe automatiquement via le programme d'installation officiel lors de la première utilisation (avec une fenêtre contextuelle de consentement), démarre le démon et extrait le modèle choisi - aucune configuration manuelle n'est requise. Passe automatiquement à Google Translate si quelque chose manque.

## Clonage vocal (XTTS v2)

Lorsqu'elle est activée, l'application extrait la voix de l'orateur de la vidéo originale et l'utilise comme référence pour cloner la voix dans la langue cible.

- Langues prises en charge : AR, ZH, CS, DE, EN, ES, FR, HI, HU, IT, JA, KO, NL, PL, PT, RU, TR (17/26)
- Pour les 9 langues restantes, Edge-TTS est utilisé automatiquement comme solution de secours
- Modèle (~ 1,8 Go) téléchargé automatiquement lors de la première utilisation sur `~/.local/share/tts/`
- **Référence filtrée VAD** (v1.4) : 10 à 15 s de parole continue sélectionnée à partir de l'audio d'origine via [silero-vad](https://github.com/snakers4/silero-vad) pour une meilleure qualité de clonage vocal
- **Vitesse de génération** configurable (`xtts_speed`, `1.25` par défaut) : des valeurs plus élevées réduisent les artefacts de compression audio après traitement lorsque le texte traduit est plus long que l'emplacement source. Régler via `~/.config/videotranslatorai/config.json` ou CLI `--xtts-speed`
- Fonctionne sur CUDA ou CPU

## identification des personnes parlant (diarisation) (pyannote-audio)

Lorsqu'elle est activée, l'application identifie qui parle dans chaque segment. Combiné avec le clonage vocal, la voix de chaque locuteur est clonée séparément - ​​idéal pour les interviews, les podcasts et les vidéos à plusieurs.

- Nécessite un [jeton HuggingFace](https://huggingface.co/settings/tokens) gratuit (inscription unique)
- **Jeton stocké de manière sécurisée** (v1.4) via le trousseau du système d'exploitation : Windows Credential Manager, macOS Keychain, Linux Secret Service. Migration automatique à partir du stockage JSON en texte brut précédent
- Après le premier téléchargement, fonctionne entièrement hors ligne
- Modèle : `pyannote/speaker-diarization-3.1`

## Synchronisation labiale (Wav2Lip)

Lorsqu'elle est activée, l'application applique Wav2Lip GAN pour synchroniser les mouvements de la bouche du sujet avec l'audio doublé - la personne semble parler la langue traduite.

- Modèle (~ 416 Mo) et référentiel clonés automatiquement lors de la première utilisation sur `~/.local/share/wav2lip/`
- Fonctionne sur CUDA (recommandé) ou CPU
- Augmente considérablement le temps de traitement
- Fonctionne mieux sur les vidéos avec un seul visage clairement visible

## Exigences

- Python 3.10+ (le programme d'installation de Windows provisionne automatiquement la version 3.11.9)
- Windows 10/11 (x64), Linux ou macOS
- **GPU NVIDIA fortement recommandé** - voir le tableau GPU ci-dessous
- 20 Go d'espace disque libre pour une installation complète (PyTorch CUDA, Whisper large-v3, XTTS, Wav2Lip)

> **ffmpeg et tous les packages Python sont installés automatiquement** au premier lancement s'ils sont manquants. Aucune configuration manuelle requise.

**Dépendance système facultative** - `rubberband-cli` (Linux : `sudo apt install rubberband-cli`, macOS : `brew install rubberband`). Une fois installé, il est utilisé pour l'étirement temporel préservant la hauteur dans la bande de qualité contrôlée par le profil (par défaut 1,15-1,50, jusqu'à 1,65 pour le contenu dur), supprimant l'effet "tamia" résiduel sur les voix XTTS clonées. Le pipeline fonctionne inchangé sans cela (repli automatique vers ffmpeg `atempo`). Les profils de qualité préfèrent désormais les tentatives de traduction très courtes plutôt que les accélérations audio extrêmes.

### Prise en charge des GPU

Le pipeline utilise cinq composants accélérés par GPU (faster-whisper, Demucs, XTTS, Wav2Lip, pyannote). La couverture GPU n’est pas uniforme selon les fournisseurs :

| GPU | Windows | Linux | Remarques |
|-----|---------|-------|-------|
| **NVIDIA** (RTX 20xx ou version ultérieure, pilote CUDA 12.4) | ✅ pleine accélération | ✅ pleine accélération | **Recommandé.** Les 5 composants fonctionnent sur GPU. |
| **AMD** (Radeon) | ⚠️ incomplet (DirectML ne prend pas en charge XTTS et faster-whisper) | ⚠️ partiel (ROCm fonctionne pour Demucs/XTTS/pyannote mais faster-whisper ne prend en charge que CUDA) | Fonctionne mais la transcription Whisper reste sur CPU et domine le temps total. |
| **Intel Arc** | ⚠️ Prise en charge immature de PyTorch XPU | ⚠️ pareil | Pas testé. |
| **Aucun (CPU uniquement)** | ✅ fonctionne | ✅ fonctionne | Attendez-vous à **10-20× plus lent** qu'en temps réel. Un clip de 5 minutes peut prendre plus de 50 minutes rien que pour être transcrit avec Whisper large-v3. |

**VRAM NVIDIA recommandée :**

| VRAM | Cartes graphiques courantes | Expérience |
|------|---------------|-----------|
| 6 Go | GTX 1660, RTX 2060 | Utilisable, ne peut pas exécuter XTTS + Wav2Lip simultanément |
| 8 Go | RTX 3060Ti, 4060 | Pipeline complet, pas de marge |
| **12 Go+** | **RTX 3060 12 Go, 4070, 4080** | **Recommandé - confortable** |
| 24 Go | RTX 3090, 4090 | Capacité disponible pour les gros lots |

## Mise en place

### Windows

1. Clonez ou téléchargez ce référentiel
2. Cliquez avec le bouton droit sur `setup_windows.bat` → **Exécuter en tant qu'administrateur** → le menu affiche `[1] Install`
3. L'installateur automatiquement :
   - Installe Python 3.11 s'il n'est pas présent (à l'échelle du système)
   - Installe Git for Windows s'il n'est pas présent
   - Installe toutes les dépendances Python (PyTorch CUDA 12.4, faster-whisper, Demucs, coqui-tts, Wav2Lip deps, etc.)
   - Télécharge et installe ffmpeg
   - Installe le lecteur vidéo intégré (python-mpv plus une version libmpv dans `mpv-runtime`). L'étape est facultative : si elle échoue, tout le reste fonctionne et le volet du lecteur explique ce qui manque.
   - Crée un **raccourci sur le bureau public** (visible par tous les comptes Windows sur le PC)

> Le programme d'installation est **multi-utilisateur** : tout est installé à l'échelle du système sous `%ProgramFiles%\VideoTranslatorAI` et tout utilisateur Windows sur la machine trouve le raccourci prêt à l'emploi. Les outils de construction VS C++ ne sont **plus nécessaires** - le fork `coqui-tts` maintenu fournit des packages de roues Python précompilés.

### Linux/MacOS

```bash
# Cloner le dépôt
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI

# Facultatif : installez la pile NVIDIA CUDA 12.4 PyTorch testée à l'avance
pip install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 -r requirements-gpu-cu124.txt

# Facultatif : préinstallez tous les packages d'exécution Python au lieu de laisser l'interface graphique
# installer les packages manquants lors de la première exécution
pip install --break-system-packages -r requirements.txt

# En option : le lecteur vidéo intégré (libmpv de la distribution, python-mpv de PyPI)
sudo apt install libmpv2        # Fedora : mpv-libs, Arch : mpv, openSUSE : libmpv2
pip install --break-system-packages -r requirements-player.txt

# Facultatif : installez le projet en tant que package Python modifiable
pip install --break-system-packages --no-deps -e .

# Lancer depuis la source
python video_translator_gui.py

# Ou, après l'installation des modifications/du package
videotranslatorai
videotranslatorai --preflight
```

> Au premier lancement, l'interface graphique détecte tous les packages manquants (faster-whisper, Demucs, Edge-TTS, etc.) et les installe automatiquement, en diffusant la sortie dans la fenêtre de journal. ffmpeg est également installé automatiquement via `apt-get` / `dnf` / `pacman` (Linux) ou téléchargé depuis GitHub (Windows).

> L'en-tête affiche un badge **Joueur**. Lorsque libmpv ou python-mpv est manquant, le volet de gauche indique ce qui manque et propose **Installer le lecteur** : sous Linux, il utilise le gestionnaire de paquets via pkexec (puis `sudo -n`) et affiche la commande manuelle lorsque ni l'un ni l'autre ne fonctionne ; sous Windows, il demande avant de télécharger libmpv pour l'utilisateur actuel (environ 32 Mo).

### Profils d'exigences

| Fichier | Objectif |
|------|---------|
| `requirements.txt` | Installation d'exécution complète et rétrocompatible. |
| `requirements-core.txt` | Packages de pipeline par défaut utilisés par GUI/CLI. |
| `requirements-optional.txt` | XTTS, tokenizers MarianMT, diarisation, VAD, porte-clés. |
| `requirements-wav2lip.txt` | Runtime Wav2Lip et pile de détection de visage (`new-basicsr`, `facexlib`, `dlib`). |
| `requirements-gpu-cu124.txt` | Pile PyTorch testée avec les roues NVIDIA CUDA 12.4. |
| `requirements-player.txt` | Lecteur vidéo intégré : python-mpv (nécessite libmpv du système ou du programme d'installation Windows). |
| `requirements-dev.txt` | Dépendances légères utilisées par les tests CI/unitaires. |

## Désinstaller

### Windows

Exécutez `setup_windows.bat` (clic droit → **Exécuter en tant qu'administrateur**) et choisissez `[3] Uninstall` dans le menu. Trois sous-modes de désinstallation sont proposés :

| Mode | Administrateur requis | Portée |
|------|----------------|-------|
| **[1] Désinstallation complète - un clic** | ✅ | Supprime le dossier de l'application, le raccourci Public Desktop, ffmpeg du PATH de la machine, le cache de modèle HF de chaque utilisateur (Whisper/XTTS) et la configuration (`HF token`), ainsi que tous les packages Python AI installés par le programme d'installation. À la fin, il demande également (opt-in) s'il faut désinstaller silencieusement **Python 3.11** et **Git for Windows** via leurs chaînes de désinstallation silencieuse de registre. |
| **[2] Utilisateur actuel uniquement** | ❌ | Supprime uniquement la configuration VTAI de l'utilisateur en cours d'exécution, le cache HF/XTTS et l'installation héritée par utilisateur. **Laisse l'installation à l'échelle du système intacte** afin que les autres comptes Windows sur le PC puissent continuer à utiliser l'application. |
| **[3] Personnalisé - granulaire** | ✅ pour les éléments système, ❌ pour les éléments utilisateur | Invite O/N pour chaque catégorie : dossier d'application, raccourci, CHEMIN de la machine, installations héritées par utilisateur, configurations/caches par utilisateur, puis packages Python regroupés (TTS, pile PyTorch, Whisper+ctranslate2, Demucs, dépôts Wav2Lip, pyannote, utilitaires de pipeline), et enfin Python 3.11 et Git en option. |

**Jamais supprimé automatiquement :** Outils de construction Visual Studio C++ (s'ils sont présents dans des exécutions plus anciennes). Utilisez *Applications et fonctionnalités* dans les paramètres Windows pour les supprimer manuellement si vous le souhaitez.

### Linux/MacOS

Pas de programme de désinstallation dédié - supprimez manuellement :

```bash
# Packages Python installés par l'installateur automatique de l'interface graphique
pip uninstall -y faster-whisper demucs soundfile edge-tts deep-translator pydub \
    yt-dlp pyloudnorm sentencepiece sacremoses pyannote.audio torchcodec \
    coqui-tts transformers torch torchaudio torchvision new-basicsr basicsr facexlib dlib ctranslate2 mpv

# Données utilisateur et caches de modèles
rm -rf ~/.cache/huggingface/hub/models--*whisper*
rm -rf ~/.cache/huggingface/hub/models--*XTTS* ~/.cache/huggingface/hub/models--*coqui*
rm -rf ~/.cache/huggingface/hub/models--*pyannote*
rm -rf ~/.local/share/tts ~/.local/share/wav2lip
rm -rf ~/.config/videotranslatorai          # config (thèmes, ordre des panneaux, paramètres)
rm -f  ~/.videotranslatorai_config.json     # configuration héritée des versions <= 1.9, si présente
```

## Utilisation

### Diagnostic

```bash
python video_translator_gui.py --preflight
python video_translator_gui.py --preflight --preflight-lipsync
python video_translator_gui.py --preflight --preflight-player
python -m videotranslator --preflight
```

Exécute les diagnostics de l'environnement local sans démarrer la traduction ni installer quoi que ce soit. `--preflight-lipsync` traite les packages de visage Wav2Lip comme requis, ce qui est utile avant d'activer **Lip Sync**. L'interface graphique expose la même vérification de base à partir du bouton **Diagnostics** du panneau de journal. `--preflight-player` traite le lecteur vidéo intégré (python-mpv et une libmpv chargeable) selon les besoins. `python -m videotranslator.libmpv_runtime check` sonde libmpv seul (sortie 0 prête, 2 indisponible).

### GUI

```bash
python video_translator_gui.py
```

**Mise en page :** les paramètres de traduction par lots se trouvent dans la colonne de droite, sous la forme d'une pile de panneaux de paramètres : **Saisie**, **Traduction**, **Profil de flux de travail**, **Démarrer** et les sections avancées réductibles (modèle, moteur de traduction, audio, clonage vocal, synchronisation labiale, diarisation, options, mots clés). La grande zone sur la gauche est le **lecteur vidéo intégré** (transport, playlist, audio A/B original ou doublé, sous-titres, instantané, plein écran), avec la barre de **traduction en temps réel** en dessous. Faites glisser une carte par son titre ou par la poignée **≡** pour la déplacer vers le haut ou le bas de la colonne ; la commande est enregistrée (`ui_panel_order`) et restaurée au prochain démarrage. Le panneau de journal en bas peut être masqué avec **Masquer le journal**. Au démarrage, la fenêtre s'ouvre centrée sur le moniteur actuel (celui sous le pointeur) et agrandie, elle se comporte donc bien sur une configuration multi-moniteurs.

**Commandes du lecteur vidéo :** les icônes utilisent des couleurs fonctionnelles cohérentes dans chaque thème, indépendamment de la couleur d'accentuation sélectionnée :

| Contrôle | Couleur |
|---------|--------|
| Lire la vidéo | Vert |
| Pause (remplace Play pendant la lecture) | Ambre |
| Arrêter la lecture | Rouge corail |
| Précédent / retour 10 s / avant 10 s / suivant | Bleu |
| Instantané | Violette |
| Ouvrir le dossier | Or |

Le survol ajoute un arrière-plan légèrement teinté. Les commandes indisponibles sont neutres ; la navigation dans la playlist reste utilisable après l'arrêt. Les info-bulles et les indicateurs de focus du clavier restent disponibles, la couleur n'est donc pas le seul moyen d'identifier les actions.

**À partir de fichiers locaux :**
1. Cliquez sur **Ajouter** pour sélectionner un ou plusieurs fichiers vidéo
2. Choisissez la langue source et la langue cible
3. Ouvrez la section **Modèle** et sélectionnez un modèle Whisper (`small` est un bon équilibre entre vitesse/précision)
4. Choisissez une voix et ajustez la vitesse TTS si nécessaire
5. *(Facultatif)* Dans **Moteur de traduction**, sélectionnez **Google** (par défaut), **MarianMT** (local/hors ligne), **DeepL Free** ou **Ollama LLM** (local, recommandé pour le doublage vocal).
6. *(Facultatif)* Activer le **Clonage vocal** (XTTS v2) et/ou **l'identification des personnes qui parlent (diarisation)**
7. *(Facultatif)* Activer **La synchronisation labiale** (Wav2Lip)
8. Cliquez sur **Démarrer la traduction**

**Depuis YouTube (ou tout site pris en charge) :**
1. Collez une ou plusieurs URL dans le champ **URL** (une par ligne).
2. Configurez la langue, le modèle et la voix comme d'habitude
3. Cliquez sur **⬇ Télécharger et traduire**

> yt-dlp prend en charge YouTube, Vimeo, Twitter/X, TikTok et [plus de 1 000 autres sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

> ⚠️ **Avis d'utilisation équitable :** Le téléchargement de vidéos via yt-dlp est considéré comme un accès automatisé par des plateformes comme YouTube et peut enfreindre leurs conditions d'utilisation. Une utilisation intensive ou répétée de la même adresse IP peut entraîner des blocages temporaires (erreurs HTTP 429 / connexion requise). Utilisez un VPN ou faites pivoter votre IP si vous rencontrez des échecs de téléchargement. Cet outil est destiné uniquement à un usage personnel et non commercial. La redistribution du contenu traduit peut enfreindre les droits d'auteur - respectez toujours les droits du créateur original.

### Traduction en temps réel (sous-titres et doublage vocal expérimental)

Regardez un fichier local ou un lien vidéo résolu à la demande avec des sous-titres traduits et une traduction vocale facultative. Utilisez la barre sous le lecteur :

**À partir d'un lien :**

1. Collez un lien dans le champ **URL**
2. Définissez la langue source et cible, choisissez une voix et ajustez le curseur **Délai**
3. Sélectionnez **Voix doublée** et/ou **Sous-titres**.
4. Pour entendre uniquement la voix traduite, sélectionnez **Muet l'audio original** avant de commencer (en italien : **Silenzia originale**, à côté de la case à cocher des sous-titres).
5. Cliquez sur **Traduire en temps réel** : le lien est résolu et la traduction démarre.

**À partir d'un fichier chargé :** chargez une vidéo dans le lecteur (Saisie -> Ajouter, puis sélectionnez-la), laissez le champ URL vide, choisissez les mêmes paramètres en direct et cliquez sur **Traduire en temps réel**. Une URL est prioritaire lorsque le champ n'est pas vide.

- **Moteur :** MarianMT (hors ligne, par défaut), Google, DeepL ou Ollama. La reconnaissance vocale (Whisper) s'exécute localement. Les modèles hors ligne nécessitent un téléchargement initial.
- **Doublage vocal :** lecture vocale expérimentale Edge-TTS via une deuxième instance mpv. Il nécessite un accès Internet et est distinct du clonage vocal par lots.
- **Muet l'audio original :** disponible avant le démarrage et pendant la traduction. Il coupe toute la bande originale, y compris la musique et les effets, mais laisse la voix traduite audible. Cela n’isole pas la personne qui parle dans l’audio original. Désactivez-le pour restaurer la bande sonore ; il se réinitialise à la fin de la session en direct. Le bouton du haut-parleur du lecteur est la fonction de sourdine générale, et non cette commande indépendante.
- **Pause et recherche :** les commandes du lecteur vidéo sont connectées à la session en direct ; La synchronisation audio de bout en bout nécessite encore des tests d'acceptation spécifiques à la plate-forme.
- **Limites actuelles :** la gestion du chevauchement/fondu des clips, l'étalonnage du timing audio et l'acceptation de Windows restent ouverts. Les diffusions en direct croissantes ne sont pas encore prises en charge ; l'étiquette du mode live n'implique pas la prise en charge de l'ingestion d'une diffusion à mesure qu'elle se développe. Voir le [état de mise en œuvre et travail restant](../../docs/ACTION_PLAN.md#live-p5-handoff-to-claude-code-2026-09-26).

Pour une vidéo doublée enregistrée, utilisez **Télécharger et traduire** / **Démarrer la traduction** au lieu de l'aperçu en temps réel.

### Blocs moteurs de traduction et VPN

Deux blocages différents peuvent survenir, avec des correctifs différents :

| Bloquer | Symptôme | Corriger |
|-------|---------|-----|
| **Télécharger** (yt-dlp) | "Connectez-vous pour confirmer que vous n'êtes pas un robot", HTTP 429 | **VPN** / alterner IP, ou être connecté à YouTube dans votre navigateur (les cookies sont lus automatiquement) |
| **Traduction** (point de terminaison Google gratuit) | "Google Translate n'a pas pu traduire... taux de requêtes limité/bloqué" | Utilisez **MarianMT** (hors ligne) ou **Ollama** (local) - aucune limite de débit de requête. Un VPN aide également. Le flux de lots **revient désormais automatiquement** à MarianMT lorsque Google est bloqué. |

### Thèmes et apparence

Cliquez sur l'icône en forme d'engrenage dans l'en-tête pour ouvrir les **Paramètres** :

- **Thème** : Automatique (suit le mode sombre/clair du système d'exploitation), Graphite (par défaut), Slate, Light, Neon.
- **Couleur d'accent** : par défaut par thème, ou bleu, sarcelle, violet, vert, ambre, rose.
- **Taille du texte** : petit, normal, grand, très grand.
- **Langue de l'interface** : 26 langues.

Les modifications s'appliquent immédiatement, sans redémarrage, et sont enregistrées dans le fichier de configuration (`ui_theme`, `ui_accent`, `ui_scale`, `ui_lang`). **Restaurer les paramètres par défaut** ramène le thème Graphite, l'accent par défaut, la taille normale du texte et l'ordre par défaut des panneaux de paramètres.

### Ligne de commande

```bash
python video_translator_gui.py video.mp4 --lang-target en
python -m videotranslator video.mp4 --lang-target en
videotranslatorai video.mp4 --lang-target en
```

**Toutes les options :**

| Option CLI | Descriptif | Par défaut |
|------|-------------|---------|
| `--lang-source` | Langue source (`auto` pour la détection automatique) | `auto` |
| `--lang-target` | Code de langue cible (par exemple `it`, `fr`, `de`) | `it` |
| `--voice` | Nom vocal Edge-TTS | auto |
| `--model` | Modèle Whisper (`tiny` → `large-v3-turbo`) | `small` |
| `--tts-rate` | Réglage de la vitesse TTS (par exemple `+10%`, `-20%`) | `+0%` |
| `--translation-engine` | `google`, `marian` ou `deepl` | `google` |
| `--deepl-key` | Clé API DeepL Free | - |
| `--diarize` | Permettre l'identification des personnes parlant (diarisation) (pyannote) | - |
| `--hf-token` | Jeton HuggingFace pour la diarisation | - |
| `--lipsync` | Appliquer la synchronisation labiale Wav2Lip après le doublage vocal | - |
| `--subs-only` | Générez uniquement `.srt`, ignorez le doublage vocal | - |
| `--no-subs` | Ignorer la génération `.srt` | - |
| `--no-demucs` | Passer la séparation voix/musique | - |
| `--output` / `-o` | Chemin du fichier de sortie | auto |
| `--output-dir` | Dossier pour les fichiers traduits (un seul endroit, Windows et Linux) | `<videos>/VideoTranslatorAI` |
| `--batch` | Traiter plusieurs fichiers | - |

### tests d'intégration avec des modèles réels

La suite de tests par défaut évite les téléchargements de modèles réels et les longs travaux sur le GPU. Pour exécuter des vérifications empiriques d'adhésion pour la pile locale installée :

```bash
VTAI_RUN_HEAVY_SMOKE=1 python -m unittest discover -s tests -p "test_heavy_smoke.py" -v
```

Ces vérifications valident les importations Wav2Lip réelles, la disponibilité de Torch CUDA, la disponibilité du démon Ollama et faster-Whisper sur la parole synthétique. Ils échouent ou sautent intentionnellement lorsque l’état du pilote/démon/modèle local n’est pas prêt.

**Exemples :**

```bash
# Traduire une vidéo italien en anglais avec MarianMT local
# (télécharge le modèle d'environ 298 Mo lors de la première utilisation, puis entièrement hors ligne)
python video_translator_gui.py video.mp4 --lang-source it --lang-target en --translation-engine marian

# Traduire avec clonage vocal + identification des interlocuteurs (diarisation)
python video_translator_gui.py interview.mp4 --lang-target en --diarize --hf-token hf_xxx

# Traduire avec la synchronisation labiale
python video_translator_gui.py video.mp4 --lang-target en --lipsync

# Sous-titres uniquement (pas de doublage vocal)
python video_translator_gui.py video.mp4 --lang-target fr --subs-only
```

## Modèles Whisper

| Modèle | Taille | Vitesse | Précision |
|-------|------|-------|----------|
| tiny | 75 Mo | ⚡⚡⚡⚡ | ★☆☆☆ |
| base | 145 Mo | ⚡⚡⚡ | ★★☆☆ |
| small | 465 Mo | ⚡⚡ | ★★★☆ |
| medium | 1,5 Go | ⚡ | ★★★★ |
| large-v2/v3 | 3 Go | 🐢 | ★★★★★ |
| large-v3-turbo | 1,6 Go | ⚡⚡ | ★★★★½ |

> `large-v3-turbo` est une version distillée de `large-v3` (4 couches de décodeur contre 32) - qualité quasi-grande à une vitesse d'environ `medium`. Valeur par défaut recommandée sur un GPU moderne lorsque la vitesse de transcription est importante ; la baisse de qualité sur le matériel multilingue est mineure.

> Les modèles sont téléchargés automatiquement lors de la première utilisation.

## CLI de module autonome

Le package modulaire expose quatre outils destinés à l'utilisateur qui peuvent être invoqués directement sans lancer le pipeline complet :

```bash
# Pré-volez une vidéo pour la présence du visage (Wav2Lip sauterait en cas d'absence).
python3 -m videotranslator.face_detector path/to/video.mp4
# sortie 0 = visage présent, sortie 1 = pas de visage

# Analysez un *_metrics.csv produit par build_dubbed_track.
# Rapports P50/P75/P90/P95 de pre_stretch_ratio, répartition de la bande d'audibilité,
# étendre l'utilisation du moteur et les N pires valeurs aberrantes avec leur texte cible.
python3 -m videotranslator.metrics_csv path/to/video_metrics.csv

# Désinfecte le texte pour TTS (réécrit les deux-points, les points-virgules, les points de suspension, les tirets).
echo "alle 10:30 ho detto: andiamo!" | python3 -m videotranslator.tts_text_sanitizer

# Estimez la difficulté de doublage vocal à partir d’un fichier de segments .srt ou .json AVANT d’exécuter TTS.
python3 -m videotranslator.difficulty_detector path/to/video_it.srt --target-lang it --expansion 1.25
```

Chaque outil dispose de `-h`/`--help` pour des options complètes. Ils sont autonomes et réutilisent les mêmes modules sur lesquels repose le pipeline de doublage vocal, de sorte que leur sortie reste cohérente avec le runtime.

## Licence

MIT

### Composants tiers

Le code du référentiel est MIT. Les installateurs téléchargent les composants ci-dessous à partir de leurs propres sources au moment de l'installation ; le projet ne les redistribue pas.

- **libmpv** (https://github.com/mpv-player/mpv), le moteur du lecteur vidéo intégré. Windows : la version LGPL de zhongfly (https://github.com/zhongfly/mpv-winbuild) est essayée en premier ; une version GPL épinglée par shinchiro (https://sourceforge.net/projects/mpv-player-windows/files/libmpv/) est la solution de secours. `mpv-runtime\BUILD.txt` enregistre la source, la version de licence et la validation mpv, et le texte de la licence se trouve à côté de la DLL. Linux : le package de distribution (`libmpv2`, `libmpv1`, `mpv-libs` ou `mpv`).
- **FFmpeg** dans libmpv (LGPL ou GPL, suivant la version libmpv).
- **python-mpv** (`mpv` sur PyPI), GPLv2+ ou LGPLv2.1+.
- **7-Zip `7zr.exe`** 26.03 (LGPL), utilisé par le programme d'installation de Windows pour extraire libmpv et supprimé par la suite.
- **Chargeur Vulkan** (Khronos, MIT et Apache-2.0), téléchargé sous Windows uniquement lorsque `vulkan-1.dll` est manquant.
- **edge-tts** (LGPLv3), utilisé par le pipeline de doublage vocal.
- **Modèles MarianMT** (Helsinki-NLP), téléchargés à partir du Hugging Face Hub lors de la première utilisation sous leurs propres licences (Apache-2.0 pour les modèles `opus-mt`, CC-BY-4.0 pour `opus-mt-tc-big`).
