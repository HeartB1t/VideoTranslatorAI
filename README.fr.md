# Video Translator AI

[Toutes les langues](README_LANGUAGES.md) | [English](README.md)

Outil open source pour transcrire, traduire et doubler des vidéos dans 26 langues.
La reconnaissance vocale Whisper s'exécute localement ; traduction et synthèse
dépendent du moteur choisi.

## Démarrage rapide

Windows : lancez `setup_windows.bat` en tant qu'administrateur et choisissez
`[1] Install`. Linux/macOS :

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Ajoutez un fichier ou un lien, choisissez les langues, la voix et le moteur, puis
lancez la traduction. **Silenzia originale** coupe toute la bande-son originale,
y compris la musique et les effets. Le doublage en direct est expérimental ; les
diffusions en cours ne sont pas encore prises en charge. Consultez le [README
anglais](README.md) pour les détails complets.
