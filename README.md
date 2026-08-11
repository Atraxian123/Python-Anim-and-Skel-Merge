# WoW `.skel` / `.anim` / `.m2` Merge Toolchain — Instructions
# Strumenti di merge `.skel` / `.anim` / `.m2` per WoW — Istruzioni

*(English below / Italiano più sotto — jump to [Italiano](#italiano))*

Inspired by the now removed from the internet Callumchauchy's multiconverter that merged .skel files into their .m2 models.

Mainly made with Claude.ai

---

## REQUIREMENTS
**`Python 2.6.6`**
**`To be used on models that have either .skel, .skel + .anim files and/or parent .skel and daughter .skel + .anim files`**

## INTENDED USE
**`Used to merge the .skel files into >WotLK .m2 files for easier retroporting. It is meant to be used on non-converted .skel files, .anim files for models that have a .skel (models with only .anim files but not a .skel filed do not require this) and models that have both a parent and daughter .skel files`**

## KNOWN BUGS
**`The scripts are still not flagging all ofthe animations as inside of the .m2 model, so some manual reflagging with Alastor's m2 template and 010 editor is required for animations that use the external .anim files as aliases`**


## English

### What these scripts do

Modern World of Warcraft models (Legion+) split animation data across several
files:

- **`.m2`** — the model itself (mesh, textures...). If it depends on an
  external skeleton, it contains no bone or sequence data of its own.
- **`.skel`** — the model's skeleton (bones, sequences/animations,
  attachments). Large models may split this further into a **parent**
  `.skel` (shared skeleton) and a **daughter** `.skel` (variant-specific
  animations, e.g. `centaur2_female.skel` sharing `centaur2_male.skel`'s
  bone hierarchy).
- **`.anim`** — individual animations too large to keep embedded, loaded
  on demand and referenced by an `AFID` table in the `.skel`.

These four scripts let you **collapse that whole chain back into a single,
self-contained `.m2`** that needs no external `.skel`/`.anim` files at all —
useful for lightweight distribution, older tools that don't understand the
chunked `.skel` system, or just simplifying a modding pipeline.

### The four scripts

| Script | Purpose |
|---|---|
| `merge_skel.py` | Merges a **parent** `.skel` + a **daughter** `.skel` (same bone hierarchy, different animation sets) into one `.skel`. Command-line only. |
| `merge_anim_into_skel.py` | Bakes one or more external **`.anim`** files directly into a `.skel`'s embedded animation data, and flips the "embedded" flag so the `.skel` no longer needs those `.anim` files. Command-line only. |
| `merge_skel_gui.py` | A graphical interface (bilingual, IT/EN toggle) for the two scripts above. **Does not** handle the final `.m2` step — see below. |
| `merge_skel_into_m2.py` | The final step: folds a fully-baked `.skel` (bones, sequences, global sequences, attachments) directly into a `.m2`, producing a standalone model with no external skeleton dependency. Command-line only. |

### Recommended pipeline order

1. **Bake `.anim` files into the `.skel`** (`merge_anim_into_skel.py`, or
   the GUI's "Bake .anim into a .skel" mode). Do this for every animation
   you want in the final model — anything left un-baked will need an
   old-style `.anim` file named after the final `.m2` once step 3 removes
   the `.skel`/`AFID` fallback.
2. **Merge parent + daughter `.skel`**, if applicable (`merge_skel.py`, or
   the GUI's "Merge Parent + Daughter" mode). Order relative to step 1
   doesn't matter — both scripts key off `(animID, subID)`, so you can bake
   `.anim` files in before or after the parent/daughter merge.
3. **Fold the finished `.skel` into the `.m2`** (`merge_skel_into_m2.py`).
   This is the only step not available in the GUI — run it from a terminal.

If your model only ever had a single `.skel` (no parent/daughter split),
skip step 2 entirely — that's exactly what step 3 was designed to support
on its own.

### Requirements

- Python 3 (2.6+ also supported for the command-line scripts).
- `merge_skel.py`, `merge_anim_into_skel.py`, `merge_skel_gui.py`, and
  `merge_skel_into_m2.py` must all sit **in the same folder** — they import
  each other directly.
- The GUI needs `tkinter`. It ships with Python on Windows/macOS. On Linux,
  if missing: `sudo apt install python3-tk` (or `python-tk` for Python 2).

### Usage

**GUI** (steps 1–2):
```
python3 merge_skel_gui.py
```
Pick a mode at the top, fill in the file fields, click the run button. A
button in the top-right corner switches the interface language at any time.

**Command line — bake `.anim` into a `.skel`:**
```
python3 merge_anim_into_skel.py <parent.skel> <out.skel> <anim1.anim> [anim2.anim ...]
```

**Command line — merge parent + daughter `.skel`:**
```
python3 merge_skel.py <parent.skel> <daughter.skel> <out.skel>
```
*(check `merge_skel.py`'s own `--help`/usage text if this differs — it was
provided by the user, not written by this toolchain's author.)*

**Command line — fold a `.skel` into a `.m2` (final step):**
```
python3 merge_skel_into_m2.py <model.m2> <skeleton.skel> <out.m2>
```

### Important notes and caveats

- **`.anim` filenames matter.** `merge_anim_into_skel.py` determines each
  file's animation ID / sub-ID from its filename (the `NNNN-SS.anim`
  suffix, e.g. `centaur2_male0060-00.anim` → animID 60, subID 0). Keep
  original filenames intact.
- **`merge_skel_into_m2.py` refuses to run if the target `.m2` already has
  non-empty bones/sequences/global_loops arrays**, to avoid corrupting an
  `.m2` that isn't actually skeleton-dependent. It's meant for models that
  currently rely on an external `SKID`/`.skel`.
- **Un-baked animations get flagged, not silently dropped.**
  `merge_skel_into_m2.py` will warn you by animID/subID if any sequence in
  the `.skel` still isn't marked "embedded" before folding — those
  animations won't work correctly once the `.skel`/`AFID` fallback is gone.
- **This only removes the `.skel` dependency, not `.anim` dependency for
  un-baked sequences** — if you skip step 1 for some animations, the client
  will look for old-style raw `.anim` files named after the *model*, not the
  chunked `AFM2`/`AFSB` files you started with.
- **Back up your source files.** These tools were built and verified against
  a specific set of sample files (a centaur model); while the underlying
  struct layouts were independently verified byte-for-byte against real game
  data, always keep your originals before overwriting anything.

---

## Italiano

### Cosa fanno questi script

I modelli moderni di World of Warcraft (Legion+) suddividono i dati di
animazione su più file:

- **`.m2`** — il modello vero e proprio (mesh, texture...). Se dipende da
  uno skeleton esterno, non contiene dati di ossa o animazioni proprie.
- **`.skel`** — lo skeleton del modello (ossa, sequenze/animazioni,
  attacchi). I modelli grandi possono suddividerlo ulteriormente in uno
  `.skel` **genitore** (skeleton condiviso) e uno `.skel` **figlia**
  (animazioni specifiche di una variante, es. `centaur2_female.skel` che
  condivide la gerarchia di ossa di `centaur2_male.skel`).
- **`.anim`** — animazioni singole troppo grandi per restare incorporate,
  caricate su richiesta e referenziate da una tabella `AFID` nello `.skel`.

Questi quattro script permettono di **ricompattare tutta questa catena in un
unico `.m2` autonomo** che non richiede più file `.skel`/`.anim` esterni —
utile per distribuzioni leggere, strumenti più vecchi che non capiscono il
sistema `.skel` a chunk, o semplicemente per semplificare una pipeline di
modding.

### I quattro script

| Script | Scopo |
|---|---|
| `merge_skel.py` | Unisce uno `.skel` **genitore** + uno `.skel` **figlia** (stessa gerarchia di ossa, set di animazioni diversi) in un unico `.skel`. Solo riga di comando. |
| `merge_anim_into_skel.py` | Incorpora uno o più file **`.anim`** esterni direttamente nei dati di animazione incorporati di uno `.skel`, e imposta il flag "embedded" così lo `.skel` non ha più bisogno di quei file `.anim`. Solo riga di comando. |
| `merge_skel_gui.py` | Un'interfaccia grafica (bilingue, con cambio IT/EN) per i due script sopra. **Non** gestisce il passaggio finale verso `.m2` — vedi sotto. |
| `merge_skel_into_m2.py` | Il passaggio finale: incorpora uno `.skel` completamente "baked" (ossa, sequenze, sequenze globali, attacchi) direttamente in un `.m2`, producendo un modello autonomo senza dipendenza da uno skeleton esterno. Solo riga di comando. |

### Ordine consigliato della pipeline

1. **Incorpora i file `.anim` nello `.skel`** (`merge_anim_into_skel.py`,
   oppure la modalità "Incorpora .anim in uno .skel" della GUI). Fallo per
   ogni animazione che vuoi nel modello finale — qualsiasi animazione non
   incorporata richiederà un file `.anim` in formato vecchio stile con il
   nome basato sul `.m2` finale, una volta che il passaggio 3 rimuove il
   fallback `.skel`/`AFID`.
2. **Unisci genitore + figlia `.skel`**, se applicabile (`merge_skel.py`,
   oppure la modalità "Unisci Genitore + Figlia" della GUI). L'ordine
   rispetto al passaggio 1 non è rilevante — entrambi gli script si basano
   su `(animID, subID)`, quindi puoi incorporare i file `.anim` prima o dopo
   l'unione genitore/figlia.
3. **Incorpora lo `.skel` finito nel `.m2`** (`merge_skel_into_m2.py`).
   È l'unico passaggio non disponibile nella GUI — eseguilo da terminale.

Se il tuo modello ha sempre avuto un solo `.skel` (nessuna suddivisione
genitore/figlia), salta del tutto il passaggio 2 — è esattamente il caso
d'uso per cui il passaggio 3 è stato pensato in autonomia.

### Requisiti

- Python 3 (supportato anche 2.6+ per gli script a riga di comando).
- `merge_skel.py`, `merge_anim_into_skel.py`, `merge_skel_gui.py` e
  `merge_skel_into_m2.py` devono trovarsi **tutti nella stessa cartella** —
  si importano a vicenda direttamente.
- La GUI richiede `tkinter`. È già incluso in Python su Windows/macOS. Su
  Linux, se manca: `sudo apt install python3-tk` (o `python-tk` per
  Python 2).

### Uso

**GUI** (passaggi 1–2):
```
python3 merge_skel_gui.py
```
Scegli una modalità in alto, compila i campi dei file, premi il pulsante di
esecuzione. Un pulsante in alto a destra cambia la lingua dell'interfaccia
in qualsiasi momento.

**Riga di comando — incorpora `.anim` in uno `.skel`:**
```
python3 merge_anim_into_skel.py <genitore.skel> <output.skel> <anim1.anim> [anim2.anim ...]
```

**Riga di comando — unisci genitore + figlia `.skel`:**
```
python3 merge_skel.py <genitore.skel> <figlia.skel> <output.skel>
```
*(verifica il testo di `--help`/uso di `merge_skel.py` stesso se questo
differisce — è stato fornito dall'utente, non scritto dall'autore di questa
pipeline.)*

**Riga di comando — incorpora uno `.skel` in un `.m2` (passaggio finale):**
```
python3 merge_skel_into_m2.py <modello.m2> <skeleton.skel> <output.m2>
```

### Note importanti e avvertenze

- **I nomi dei file `.anim` sono importanti.** `merge_anim_into_skel.py`
  determina l'ID animazione / sub-ID di ogni file dal suo nome (il suffisso
  `NNNN-SS.anim`, es. `centaur2_male0060-00.anim` → animID 60, subID 0).
  Mantieni intatti i nomi originali dei file.
- **`merge_skel_into_m2.py` rifiuta di procedere se il `.m2` di destinazione
  ha già array di ossa/sequenze/sequenze globali non vuoti**, per evitare di
  corrompere un `.m2` che in realtà non dipende da uno skeleton esterno. È
  pensato per modelli che attualmente si affidano a un `SKID`/`.skel`
  esterno.
- **Le animazioni non incorporate vengono segnalate, non eliminate in
  silenzio.** `merge_skel_into_m2.py` avviserà, per animID/subID, se una
  sequenza dello `.skel` non è ancora contrassegnata come "embedded" prima
  dell'incorporazione — quelle animazioni non funzioneranno correttamente
  una volta rimosso il fallback `.skel`/`AFID`.
- **Questo rimuove solo la dipendenza da `.skel`, non la dipendenza da
  `.anim` per le sequenze non incorporate** — se salti il passaggio 1 per
  alcune animazioni, il client cercherà file `.anim` in formato grezzo
  vecchio stile con nome basato sul *modello*, non i file chunked
  `AFM2`/`AFSB` da cui sei partito.
- **Fai un backup dei file originali.** Questi strumenti sono stati
  costruiti e verificati su un set specifico di file di esempio (un modello
  di centauro); sebbene i layout delle struct siano stati verificati in modo
  indipendente byte per byte contro dati di gioco reali, conserva sempre gli
  originali prima di sovrascrivere qualsiasi cosa.
