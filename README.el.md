# Video Translator AI

[Όλες οι γλώσσες](README_LANGUAGES.md) | [English](README.md)

Εργαλείο ανοικτού κώδικα για απομαγνητοφώνηση, μετάφραση και μεταγλώττιση βίντεο
σε 26 γλώσσες. Η αναγνώριση Whisper εκτελείται τοπικά· η μετάφραση και η σύνθεση
φωνής εξαρτώνται από την επιλεγμένη μηχανή.

## Γρήγορη εκκίνηση

Windows: εκτελέστε το `setup_windows.bat` ως διαχειριστής και επιλέξτε
`[1] Install`. Linux/macOS:

```bash
git clone https://github.com/HeartB1t/VideoTranslatorAI.git
cd VideoTranslatorAI
pip install --break-system-packages -r requirements.txt
python video_translator_gui.py
```

Προσθέστε αρχείο ή σύνδεσμο, επιλέξτε γλώσσες, φωνή και μηχανή και ξεκινήστε.
Το **Silenzia originale** κάνει σίγαση σε όλο τον αρχικό ήχο, μαζί με μουσική και
εφέ. Η ζωντανή μεταγλώττιση είναι πειραματική· οι ζωντανές μεταδόσεις δεν
υποστηρίζονται ακόμη. Δείτε το [README στα Αγγλικά](README.md) για λεπτομέρειες.
