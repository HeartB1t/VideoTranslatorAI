# Temi UI personalizzabili - Design

**Data:** 2026-09-24
**Stato:** implementato (vedi docs/superpowers/plans/2026-09-24-ui-themes.md)
**Demo di riferimento:** `_dev/demo_pro_themes.py` (graphite / slate / light)

## Obiettivo

Sostituire il tema unico "Neon Dark" con un sistema di temi professionali
selezionabili dall'utente, applicati **live** senza riavvio, tramite una
finestra "Impostazioni" aperta da un'icona ⚙ nell'header.

## Fuori scope (fase 2, spec separata)

- Modifiche di layout viste nelle demo: area "Aggiungi video" al posto della
  listbox vuota, riepilogo a destra delle righe accordion, log come status bar.
- Drag & drop (richiede `tkinterdnd2`, non presente).
- Colori/font personalizzati liberi (color picker), import/export temi.

## Opzioni utente

| Impostazione | Valori | Default | Chiave config |
|---|---|---|---|
| Tema | `auto`, `graphite`, `slate`, `light`, `neon` | `graphite` | `ui_theme` |
| Colore d'accento | `default`, `blue`, `teal`, `violet`, `green`, `amber`, `rose` | `default` | `ui_accent` |
| Dimensione testo | `small` (0.9), `normal` (1.0), `large` (1.15), `xlarge` (1.3) | `normal` | `ui_scale` |
| Lingua UI | (esistente, spostata nel pannello) | invariato | invariato |

- `auto`: tema scuro del sistema → `graphite`, chiaro → `light`. Rilevato
  all'avvio e alla pressione di "Applica"; nessun polling.
- `default` accento = accento proprio del tema (blu Graphite, teal Slate, blu
  Light, verde Neon).
- Valori sconosciuti/corrotti in config → default, senza errori.

## Architettura

### 1. `videotranslator/ui_theme.py` - logica pura (nessun import Tk)

```python
@dataclass(frozen=True)
class Palette:
    BG: str; SURFACE: str; FIELD: str; BORDER: str
    FG: str; FG2: str; SEL: str; BTN: str
    ACC: str; ACC_HOVER: str; ACC_SOFT: str; ACC_FG: str
    OK: str; WARN: str; ERR: str
    font_family: str      # "sans" | "mono" (risolto in famiglia reale lato GUI)

THEMES: dict[str, Palette]        # graphite, slate, light, neon
ACCENTS: dict[str, str]           # nome -> hex base
SCALES: dict[str, float]

def resolve_palette(theme: str, accent: str, system_dark: bool | None) -> Palette
def derive_accent(base_hex, surface_hex, dark: bool) -> (acc, hover, soft, fg)
def contrast_ratio(a_hex, b_hex) -> float        # WCAG 2.x
def detect_system_dark() -> bool | None           # None = sconosciuto
def normalize_ui_settings(cfg: dict) -> dict      # valida/ripulisce le 3 chiavi
```

- `derive_accent`: hover = accento schiarito (tema scuro) o scurito (chiaro)
  ~10%; soft = mix 20% accento su SURFACE; `ACC_FG` = bianco o nero, quello
  con contrasto maggiore sull'accento.
- **Invariante**: dentro ogni palette risolta (tema × accento) tutti i valori
  colore sono esadecimali distinti. Se una derivazione produce un duplicato,
  il valore viene spostato di 1 unità su un canale (impercettibile) finché è
  unico. Serve alla ricolorazione a mappa (sotto).
- `detect_system_dark`:
  - Windows: `winreg` `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`
  - macOS: `defaults read -g AppleInterfaceStyle` (== "Dark")
  - Linux: `gsettings get org.gnome.desktop.interface color-scheme`
    (`prefer-dark`), poi `gtk-theme` contenente "dark", poi
    `xfconf-query -c xsettings -p /Net/ThemeName` contenente "dark".
  - Subprocess con `timeout=2`, `stdin=DEVNULL`, ogni errore → `None`.
  - `None` → trattato come scuro.

### 2. Palette

Le palette di Graphite/Slate/Light sono quelle di `_dev/demo_pro_themes.py`.
Neon "ripulito": colori attuali (`#060612`, `#00ff88`, …), font monospace,
ma pulsanti piatti come gli altri temi (niente glow/rilievo) e magenta
(`ACC2`) usato solo per `WARN`.

Mappatura delle costanti globali attuali → ruoli:

| Costante oggi | Ruolo nuovo |
|---|---|
| `BG` | `BG` |
| `CARD` | `SURFACE` |
| `FG`, `FG2`, `SEL`, `BORDER` | stessi nomi |
| `PILL`, bg pulsanti `#1a1a3a` | `BTN` |
| `ACC`, `GRN` | `ACC` (`GRN` diventa alias) |
| `ACC2` | `WARN` |
| `RED` | `ERR` |
| `#11111b` (log), `#bac2de` (label) | `FIELD`, `FG2` |

I nomi globali esistenti (`BG`, `FG`, `ACC`, …) restano come variabili di
modulo per non riscrivere ~300 righe, ma vengono **riassegnati** dal
ThemeManager a ogni cambio tema. Nuovi nomi aggiunti: `SURFACE`, `FIELD`,
`BTN`, `ACC_HOVER`, `ACC_SOFT`, `ACC_FG`, `OK`, `WARN`, `ERR`.
`CARD` resta alias di `SURFACE`.

### 3. `ThemeManager` (in `videotranslator/ui_theme_tk.py`)

`ThemeManager(root, module_globals)` vive in un modulo dedicato, separato
dalla logica pura di `ui_theme.py`; la GUI lo crea prima di qualsiasi widget
passando i propri `globals()`, così `apply()` riscrive le variabili colore del
modulo GUI (`GLOBAL_ALIASES`).

Responsabilità:

1. **Font con nome** - crea una volta `tkfont.Font(name=...)` per
   esattamente i ruoli di `FONT_ROLES`: `VT.Small`, `VT.SmallBold`,
   `VT.Base`, `VT.Bold`, `VT.Italic`, `VT.Large`, `VT.Title`, `VT.Mono`
   (non esiste `VT.MonoBold`). Tutte le 38 tuple fisse e le costanti `_MONO*` vengono
   sostituite con questi nomi. `apply()` fa `font.configure(family=, size=)`
   → Tk aggiorna automaticamente ogni widget.
   - Famiglia sans: prima disponibile tra `Segoe UI`, `Inter`, `Noto Sans`,
     `Cantarell`, `DejaVu Sans`, `TkDefaultFont`.
   - Famiglia mono: `Cascadia Mono`, `JetBrains Mono`, `DejaVu Sans Mono`,
     `TkFixedFont`.
   - Taglie base (scala 1.0): Small 8, SmallBold 8, Base 9, Bold 9,
     Italic 8, Large 11, Title 15, Mono 9; moltiplicate per la scala e
     arrotondate (minimo 6 pt).
2. **Stili ttk** - tutto il blocco `ttk.Style` oggi in `App.__init__`
   (Combobox, Scrollbar) si sposta in `ThemeManager._apply_ttk()`, esteso a
   Treeview (editor sottotitoli), Progressbar, Scale e Checkbutton se usati.
   Richiamato a ogni `apply()`.
3. **Ricolorazione a mappa** - `recolor(root, old: Palette, new: Palette)`:
   - costruisce `mapping = {old.<ruolo>: new.<ruolo>}` (confronto
     case-insensitive, normalizzando i nomi colore Tk con
     `winfo_rgb` → hex);
   - visita ricorsivamente `root` e tutti i figli (inclusi `Toplevel`);
   - per ogni opzione colore supportata dal widget (`bg`, `fg`,
     `activebackground`, `activeforeground`, `highlightbackground`,
     `highlightcolor`, `insertbackground`, `selectbackground`,
     `selectforeground`, `disabledforeground`, `troughcolor`,
     `selectcolor`, `readonlybackground`) sostituisce il valore se è nella
     mappa; ignora silenziosamente `TclError`;
   - `tk.Text`/`Listbox`: ricolora anche i tag del widget di testo (log).
   - Colori non presenti nella mappa restano invariati (es. colori dei flag
     di qualità nell'editor, che funzionano su entrambi i temi).
4. **Globali** - `apply()` riassegna le variabili di modulo, così hover e
   `configure(bg=ACC)` eseguiti dopo il cambio usano il tema nuovo.

Flusso `apply(settings)`:
`resolve_palette` → aggiorna globali → font → ttk → `recolor(old, new)` →
salva `self._palette = new`.

### 4. Pulsanti

`_glow_btn` viene riscritto come pulsante piatto (firma e valore di ritorno
`(wrap, btn)` invariati, così i 13 chiamanti non cambiano):
`relief="flat"`, `bd=0`, bordo 1px `BORDER` tramite il frame wrapper,
hover `BTN → BORDER`; variante `primary=True` per "Avvia traduzione" e
"Scarica e traduci" (`ACC`/`ACC_FG`, hover `ACC_HOVER`).
Il titolo header diventa "Video Translator AI" in `VT.Title`, colore `FG`,
senza `◈`/maiuscolo; le etichette sezione in `VT.Small` bold, colore `FG2`.

### 5. Finestra Impostazioni

- Icona `⚙` (label cliccabile) a destra nell'header; il selettore lingua UI
  esce dall'header.
- `Toplevel` modale leggera, non ridimensionabile, centrata sulla finestra
  principale.
- Contenuto:
  - **Aspetto**: tema (pulsanti segmentati: Automatico, Graphite, Slate,
    Chiaro, Neon), accento (pallini colorati cliccabili + "Predefinito"),
    dimensione testo (segmentati).
  - **Lingua**: combobox lingua UI (logica esistente
    `_on_ui_lang_change`).
- Ogni scelta si applica **subito** (anteprima live sulla finestra
  principale). Pulsanti in basso: `Chiudi` (salva) e `Ripristina
  predefiniti`. Chiudere con la X equivale a `Chiudi`.
- Salvataggio con la funzione di config esistente (merge delle 3 chiavi,
  permessi 0600 preservati).
- Durante una traduzione in corso il cambio tema è consentito.

### 6. i18n

Nuove chiavi in `UI_STRINGS` per **tutte le 26 lingue** (come nel commit
`f56fcac`): `settings_title`, `settings_appearance`, `settings_theme`,
`settings_accent`, `settings_text_size`, `settings_language`,
`theme_auto`, `theme_light`, `accent_default`, `size_small`,
`size_normal`, `size_large`, `size_xlarge`, `btn_close`, `btn_reset`.
Nomi propri dei temi (Graphite, Slate, Neon) non tradotti. La finestra
Impostazioni aggiorna i propri testi quando si cambia lingua al suo interno.

## Avvio

In `App.__init__`, prima di `_build_ui()`: legge config →
`normalize_ui_settings` → `ThemeManager.apply()` senza `recolor` (nessun
widget ancora creato). Nessun flash del tema vecchio.

## Compatibilità

- Windows: `winreg` in stdlib; Segoe UI e Cascadia Mono presenti su
  Win 10/11. ✓
- Linux: gsettings/xfconf opzionali, fallback scuro. ✓
- macOS: `defaults` presente. ✓
- Nessuna nuova dipendenza.

## Test

`tests/test_ui_theme.py` (pure, nessun display):
- ogni palette risolta (4 temi × 7 accenti) ha valori tutti distinti;
- contrasto `FG`/`BG` e `FG`/`SURFACE` ≥ 4.5, `FG2`/`SURFACE` ≥ 3.0,
  `ACC_FG`/`ACC` ≥ 3.0 per ogni combinazione;
- `normalize_ui_settings` con valori mancanti/sconosciuti/tipi errati →
  default;
- `resolve_palette("auto", ...)` con `system_dark` True/False/None;
- `detect_system_dark` con subprocess/winreg mockati (timeout, comando
  mancante, output inatteso → `None`).

`tests/test_ui_theme_tk.py` (salta se nessun display, `pytest.skip`):
- albero piccolo di widget (Frame/Label/Button/Entry/Text/Toplevel)
  colorato con palette A, `recolor(A→B)`: tutti i colori mappati diventano
  B, un colore estraneo resta invariato;
- font con nome: cambio scala aggiorna `font.actual("size")` di un Label.

Verifica manuale: avvio GUI, screenshot di ciascun tema × 2 accenti ×
scala large, finestra editor sottotitoli aperta durante il cambio.

## Rischi

- **Colori "orfani"** (hex scritti a mano non mappati) restano del tema
  precedente. Mitigazione: grep dei letterali `"#xxxxxx"` in
  `video_translator_gui.py` → devono restare solo in `ui_theme.py` e in
  `quality_flags.py`; aggiunto test statico che lo verifica.
- **Scala xlarge** su 1366×768 può far scattare lo scroll verticale: è
  accettabile, il form è già in un canvas scrollabile.
