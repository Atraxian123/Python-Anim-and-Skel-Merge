#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Compatibile con Python 2.6+ e Python 3. / Compatible with Python 2.6+ and Python 3.
from __future__ import print_function
"""
merge_skel_gui.py — interfaccia grafica bilingue (IT/EN) per merge_skel.py,
                     merge_anim_into_skel.py e merge_skel_into_m2.py
merge_skel_gui.py — bilingual (IT/EN) GUI for merge_skel.py,
                     merge_anim_into_skel.py and merge_skel_into_m2.py

Tre modalità / Three modes:
  1) Unisci Genitore + Figlia / Merge Parent + Daughter
  2) Incorpora .anim in uno .skel / Bake .anim into a .skel
  3) Incorpora uno .skel in un .m2 / Bake a .skel into a .m2

Un pulsante in alto a destra cambia lingua in qualsiasi momento.
A button in the top-right corner switches language at any time.

Richiede / Requires: merge_skel.py, merge_anim_into_skel.py e
merge_skel_into_m2.py nella stessa cartella (li importa direttamente) /
in the same folder (imported directly).

Uso / Usage: python merge_skel_gui.py   (o/or "python3 merge_skel_gui.py")

Su Windows/macOS tkinter è già incluso in Python.
Su Linux, se manca: sudo apt install python3-tk  (o python-tk per Python 2)

tkinter ships with Python on Windows/macOS.
On Linux, if missing: sudo apt install python3-tk  (or python-tk for Python 2)
"""

import os
import sys
import traceback


def _pause_and_exit(msg):
    """Evita che la finestra del prompt si chiuda subito su errore in avvio /
    Keeps the console window open on a startup error instead of vanishing."""
    print(msg)
    try:
        raw_input("\nPremi INVIO per uscire... / Press ENTER to exit...")  # Python 2
    except NameError:
        input("\nPremi INVIO per uscire... / Press ENTER to exit...")      # Python 3
    sys.exit(1)


try:
    # Python 2
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    from ScrolledText import ScrolledText
except ImportError:
    try:
        # Python 3
        import tkinter as tk
        from tkinter import filedialog, messagebox
        from tkinter.scrolledtext import ScrolledText
    except ImportError as e:
        _pause_and_exit(
            "ERRORE / ERROR: il modulo tkinter non e' disponibile / tkinter module not available.\n"
            "Su Linux / on Linux: sudo apt install python3-tk\n"
            "Dettaglio / Detail: %s" % e
        )

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_missing = [f for f in ("merge_skel.py", "merge_anim_into_skel.py", "merge_skel_into_m2.py")
            if not os.path.isfile(os.path.join(HERE, f))]
if _missing:
    _pause_and_exit(
        "ERRORE / ERROR: questi file devono stare nella STESSA cartella di merge_skel_gui.py "
        "/ these files must be in the SAME folder as merge_skel_gui.py:\n  "
        + "\n  ".join(_missing)
        + "\n\nCartella attuale / Current folder: %s" % HERE
    )

try:
    import merge_skel as ms
    import merge_anim_into_skel as mais
    import merge_skel_into_m2 as msm
except Exception as e:
    _pause_and_exit("ERRORE / ERROR durante l'importazione / during import of merge_skel.py / "
                     "merge_anim_into_skel.py / merge_skel_into_m2.py:\n%s" % traceback.format_exc())


# =============================================================================
# Stringhe / Strings
# =============================================================================

STRINGS = {
    'it': {
        'title': "Merge .skel / Incorpora .anim / Incorpora .m2",
        'lang_btn': "English",
        'mode_frame': "Modalità",
        'mode_pd': "Unisci Genitore + Figlia (.skel + .skel)",
        'mode_anim': "Incorpora .anim in uno .skel (.skel + uno o più .anim)",
        'mode_m2': "Incorpora uno .skel in un .m2 (.m2 + .skel)",
        'pd_frame': "Genitore + Figlia",
        'parent_label': "Skeleton GENITORE (.skel):",
        'daughter_label': "Skeleton FIGLIA (.skel):",
        'browse': "Sfoglia...",
        'anim_frame': "Incorpora .anim",
        'skel_label': "Skeleton (.skel):",
        'anim_list_label': "File .anim (uno o più):",
        'add': "Aggiungi...",
        'remove_sel': "Rimuovi selezionati",
        'clear_list': "Svuota lista",
        'force_flag_label': "Forza il flag 0x20 (embedded) su TUTTE le animazioni dello .skel",
        'force_flag_warn': "Attenzione: opzione da usare solo se, dopo l'incorporazione normale,\n"
                            "alcune animazioni continuano a non funzionare in gioco (es. alias non\n"
                            "risolti). Forza il flag anche su animazioni senza dati incorporati o\n"
                            "una catena alias valida -- può peggiorare le cose se usata a sproposito.",
        'm2_frame': "Incorpora .skel in .m2",
        'm2_label': "Modello (.m2):",
        'm2_skel_label': "Skeleton (.skel):",
        'm2_note': "Incorpora ossa, sequenze, sequenze globali e attacchi\n"
                   "direttamente nel .m2; rimuove la dipendenza SKID/.skel.",
        'run_btn': "Esegui e salva...",
        'log_label': "Log:",
        'err_title': "Errore",
        'err_parent': "Seleziona un file GENITORE valido.",
        'err_daughter': "Seleziona un file FIGLIA valido.",
        'err_skel': "Seleziona un file .skel valido.",
        'err_anim': "Aggiungi almeno un file .anim.",
        'err_m2': "Seleziona un file .m2 valido.",
        'sel_parent_title': "Seleziona lo skeleton GENITORE",
        'sel_daughter_title': "Seleziona lo skeleton FIGLIA",
        'sel_skel_title': "Seleziona lo skeleton (.skel) in cui incorporare gli .anim",
        'sel_anim_title': "Seleziona uno o più file .anim",
        'sel_m2_title': "Seleziona il modello (.m2)",
        'sel_m2_skel_title': "Seleziona lo skeleton (.skel) da incorporare nel .m2",
        'filetype_skel': "WoW skeleton",
        'filetype_anim': "WoW anim",
        'filetype_m2': "WoW model",
        'filetype_all': "Tutti i file",
        'reading': "Lettura file...",
        'warn_no_skpd': "[avviso] il file 'figlia' non ha un chunk SKPD: "
                         "sei sicuro sia lo skeleton figlia e non il genitore?",
        'parent_stats': "Genitore: %d ossa, %d animazioni",
        'daughter_stats': "Figlia:   %d ossa, %d animazioni",
        'merging': "Merge in corso...",
        'save_title': "Salva il file .skel unito",
        'save_cancelled': "Salvataggio annullato dall'utente.",
        'done': "Fatto! Salvato in: %s",
        'done_title': "Completato",
        'done_msg': "File salvato in:\n%s",
        'error_title_merge': "Errore durante il merge",
        'error_title_bake': "Errore durante l'incorporazione",
        'error_prefix': "ERRORE:",
        'baking_start': "Lettura .skel e .anim, incorporazione in corso...",
        'baking_flag_note': "(imposta il flag 0x20 'embedded' su ogni animazione incorporata "
                             "e rimuove la relativa voce da AFID)",
        'save_baked_title': "Salva lo .skel con gli .anim incorporati",
        'm2_baking_start': "Lettura .m2 e .skel, incorporazione in corso...",
        'm2_baking_note': "(incorpora ossa, sequenze, sequenze globali e attacchi nel .m2; "
                           "rimuove il chunk SKID)",
        'save_m2_title': "Salva il .m2 con lo .skel incorporato",
    },
    'en': {
        'title': "Merge .skel / Bake .anim / Bake .m2",
        'lang_btn': "Italiano",
        'mode_frame': "Mode",
        'mode_pd': "Merge Parent + Daughter (.skel + .skel)",
        'mode_anim': "Bake .anim into a .skel (.skel + one or more .anim)",
        'mode_m2': "Bake a .skel into a .m2 (.m2 + .skel)",
        'pd_frame': "Parent + Daughter",
        'parent_label': "PARENT skeleton (.skel):",
        'daughter_label': "DAUGHTER skeleton (.skel):",
        'browse': "Browse...",
        'anim_frame': "Bake .anim",
        'skel_label': "Skeleton (.skel):",
        'anim_list_label': ".anim file(s):",
        'add': "Add...",
        'remove_sel': "Remove selected",
        'clear_list': "Clear list",
        'force_flag_label': "Force the 0x20 (embedded) flag on ALL animations in the .skel",
        'force_flag_warn': "Warning: only use this if, after the normal baking step, some\n"
                            "animations still don't play correctly in-game (e.g. unresolved\n"
                            "aliases). It forces the flag even on animations with no baked-in\n"
                            "data or valid alias chain -- can make things worse if misused.",
        'm2_frame': "Bake .skel into .m2",
        'm2_label': "Model (.m2):",
        'm2_skel_label': "Skeleton (.skel):",
        'm2_note': "Bakes bones, sequences, global sequences and attachments\n"
                   "directly into the .m2; removes the SKID/.skel dependency.",
        'run_btn': "Run and save...",
        'log_label': "Log:",
        'err_title': "Error",
        'err_parent': "Select a valid PARENT file.",
        'err_daughter': "Select a valid DAUGHTER file.",
        'err_skel': "Select a valid .skel file.",
        'err_anim': "Add at least one .anim file.",
        'err_m2': "Select a valid .m2 file.",
        'sel_parent_title': "Select the PARENT skeleton",
        'sel_daughter_title': "Select the DAUGHTER skeleton",
        'sel_skel_title': "Select the .skel to bake the .anim files into",
        'sel_anim_title': "Select one or more .anim files",
        'sel_m2_title': "Select the model (.m2)",
        'sel_m2_skel_title': "Select the .skel to bake into the .m2",
        'filetype_skel': "WoW skeleton",
        'filetype_anim': "WoW anim",
        'filetype_m2': "WoW model",
        'filetype_all': "All files",
        'reading': "Reading files...",
        'warn_no_skpd': "[warning] the 'daughter' file has no SKPD chunk: "
                         "are you sure it's the daughter skeleton and not the parent?",
        'parent_stats': "Parent: %d bones, %d animations",
        'daughter_stats': "Daughter: %d bones, %d animations",
        'merging': "Merging...",
        'save_title': "Save the merged .skel file",
        'save_cancelled': "Save cancelled by user.",
        'done': "Done! Saved to: %s",
        'done_title': "Complete",
        'done_msg': "File saved to:\n%s",
        'error_title_merge': "Error during merge",
        'error_title_bake': "Error during baking",
        'error_prefix': "ERROR:",
        'baking_start': "Reading .skel and .anim files, baking in progress...",
        'baking_flag_note': "(sets the 0x20 'embedded' flag on every baked-in animation "
                             "and removes the matching entry from AFID)",
        'save_baked_title': "Save the .skel with the .anim files baked in",
        'm2_baking_start': "Reading .m2 and .skel, baking in progress...",
        'm2_baking_note': "(bakes bones, sequences, global sequences and attachments into "
                           "the .m2; removes the SKID chunk)",
        'save_m2_title': "Save the .m2 with the .skel baked in",
    },
}


class MergeSkelApp(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.lang = 'en'
        self.resizable(False, False)

        self.mode = tk.StringVar(value="parent_daughter")

        pad = {'padx': 10, 'pady': 6}

        # ---- barra superiore: modalità + cambio lingua / top bar: mode + language switch
        top_frame = tk.Frame(self)
        top_frame.grid(row=0, column=0, columnspan=2, sticky="we", padx=10, pady=(10, 0))
        top_frame.grid_columnconfigure(0, weight=1)

        self.mode_frame_widget = tk.LabelFrame(top_frame)
        self.mode_frame_widget.grid(row=0, column=0, sticky="we")
        self.mode_pd_radio = tk.Radiobutton(self.mode_frame_widget, variable=self.mode,
                                             value="parent_daughter", command=self.refresh_mode)
        self.mode_pd_radio.pack(anchor="w", padx=8, pady=2)
        self.mode_anim_radio = tk.Radiobutton(self.mode_frame_widget, variable=self.mode,
                                               value="bake_anim", command=self.refresh_mode)
        self.mode_anim_radio.pack(anchor="w", padx=8, pady=2)
        self.mode_m2_radio = tk.Radiobutton(self.mode_frame_widget, variable=self.mode,
                                             value="skel_into_m2", command=self.refresh_mode)
        self.mode_m2_radio.pack(anchor="w", padx=8, pady=2)

        self.lang_btn = tk.Button(top_frame, command=self.toggle_lang, width=10)
        self.lang_btn.grid(row=0, column=1, sticky="ne", padx=(10, 0))

        # ---- pannello: unisci genitore + figlia / panel: merge parent + daughter
        self.pd_frame = tk.LabelFrame(self)
        self.parent_path = tk.StringVar()
        self.daughter_path = tk.StringVar()

        self.parent_label = tk.Label(self.pd_frame)
        self.parent_label.grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self.pd_frame, textvariable=self.parent_path, width=55).grid(row=1, column=0, **pad)
        self.parent_browse_btn = tk.Button(self.pd_frame, command=self.pick_parent)
        self.parent_browse_btn.grid(row=1, column=1, **pad)

        self.daughter_label = tk.Label(self.pd_frame)
        self.daughter_label.grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(self.pd_frame, textvariable=self.daughter_path, width=55).grid(row=3, column=0, **pad)
        self.daughter_browse_btn = tk.Button(self.pd_frame, command=self.pick_daughter)
        self.daughter_browse_btn.grid(row=3, column=1, **pad)

        # ---- pannello: incorpora .anim / panel: bake .anim
        self.anim_frame = tk.LabelFrame(self)
        self.skel_path = tk.StringVar()
        self.anim_paths = []  # lista di path selezionati / selected paths list

        self.skel_label = tk.Label(self.anim_frame)
        self.skel_label.grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self.anim_frame, textvariable=self.skel_path, width=55).grid(row=1, column=0, **pad)
        self.skel_browse_btn = tk.Button(self.anim_frame, command=self.pick_skel_for_anim)
        self.skel_browse_btn.grid(row=1, column=1, **pad)

        self.anim_list_label = tk.Label(self.anim_frame)
        self.anim_list_label.grid(row=2, column=0, sticky="w", **pad)
        self.anim_listbox = tk.Listbox(self.anim_frame, width=55, height=6, selectmode="extended")
        self.anim_listbox.grid(row=3, column=0, **pad)
        anim_btns = tk.Frame(self.anim_frame)
        anim_btns.grid(row=3, column=1, sticky="n", **pad)
        self.add_btn = tk.Button(anim_btns, command=self.pick_anims)
        self.add_btn.pack(fill="x", pady=2)
        self.remove_btn = tk.Button(anim_btns, command=self.remove_selected_anims)
        self.remove_btn.pack(fill="x", pady=2)
        self.clear_btn = tk.Button(anim_btns, command=self.clear_anims)
        self.clear_btn.pack(fill="x", pady=2)

        self.force_all_embedded = tk.BooleanVar(value=False)
        self.force_flag_check = tk.Checkbutton(self.anim_frame, variable=self.force_all_embedded)
        self.force_flag_check.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 0))
        self.force_flag_warn_label = tk.Label(self.anim_frame, justify="left", fg="#a05a00")
        self.force_flag_warn_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))

        # ---- pannello: incorpora .skel in un .m2 / panel: bake .skel into .m2
        self.m2_frame = tk.LabelFrame(self)
        self.m2_path = tk.StringVar()
        self.m2_skel_path = tk.StringVar()

        self.m2_label = tk.Label(self.m2_frame)
        self.m2_label.grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self.m2_frame, textvariable=self.m2_path, width=55).grid(row=1, column=0, **pad)
        self.m2_browse_btn = tk.Button(self.m2_frame, command=self.pick_m2)
        self.m2_browse_btn.grid(row=1, column=1, **pad)

        self.m2_skel_label = tk.Label(self.m2_frame)
        self.m2_skel_label.grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(self.m2_frame, textvariable=self.m2_skel_path, width=55).grid(row=3, column=0, **pad)
        self.m2_skel_browse_btn = tk.Button(self.m2_frame, command=self.pick_m2_skel)
        self.m2_skel_browse_btn.grid(row=3, column=1, **pad)

        self.m2_note_label = tk.Label(self.m2_frame, justify="left", fg="#555555")
        self.m2_note_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))

        # ---- pulsante esegui + log / run button + log
        self.merge_btn = tk.Button(self, command=self.run_action, bg="#2e7d32", fg="white", height=2)
        self.merge_btn.grid(row=2, column=0, columnspan=2, sticky="we", **pad)

        self.log_label = tk.Label(self)
        self.log_label.grid(row=3, column=0, sticky="w", padx=10)
        self.log = ScrolledText(self, width=70, height=16, state="disabled")
        self.log.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 10))

        self.apply_language()
        self.refresh_mode()

    # ------------------------------------------------------------------ lingua / language

    def t(self, key):
        return STRINGS[self.lang][key]

    def toggle_lang(self):
        self.lang = 'it' if self.lang == 'en' else 'en'
        self.apply_language()

    def apply_language(self):
        self.title(self.t('title'))
        self.lang_btn.config(text=self.t('lang_btn'))
        self.mode_frame_widget.config(text=self.t('mode_frame'))
        self.mode_pd_radio.config(text=self.t('mode_pd'))
        self.mode_anim_radio.config(text=self.t('mode_anim'))
        self.mode_m2_radio.config(text=self.t('mode_m2'))
        self.pd_frame.config(text=self.t('pd_frame'))
        self.parent_label.config(text=self.t('parent_label'))
        self.daughter_label.config(text=self.t('daughter_label'))
        self.parent_browse_btn.config(text=self.t('browse'))
        self.daughter_browse_btn.config(text=self.t('browse'))
        self.anim_frame.config(text=self.t('anim_frame'))
        self.skel_label.config(text=self.t('skel_label'))
        self.skel_browse_btn.config(text=self.t('browse'))
        self.anim_list_label.config(text=self.t('anim_list_label'))
        self.add_btn.config(text=self.t('add'))
        self.remove_btn.config(text=self.t('remove_sel'))
        self.clear_btn.config(text=self.t('clear_list'))
        self.force_flag_check.config(text=self.t('force_flag_label'))
        self.force_flag_warn_label.config(text=self.t('force_flag_warn'))
        self.m2_frame.config(text=self.t('m2_frame'))
        self.m2_label.config(text=self.t('m2_label'))
        self.m2_skel_label.config(text=self.t('m2_skel_label'))
        self.m2_browse_btn.config(text=self.t('browse'))
        self.m2_skel_browse_btn.config(text=self.t('browse'))
        self.m2_note_label.config(text=self.t('m2_note'))
        self.merge_btn.config(text=self.t('run_btn'))
        self.log_label.config(text=self.t('log_label'))

    # ------------------------------------------------------------------ modalità / mode

    def refresh_mode(self):
        self.pd_frame.grid_forget()
        self.anim_frame.grid_forget()
        self.m2_frame.grid_forget()
        if self.mode.get() == "parent_daughter":
            self.pd_frame.grid(row=1, column=0, columnspan=2, sticky="we", padx=10, pady=6)
        elif self.mode.get() == "bake_anim":
            self.anim_frame.grid(row=1, column=0, columnspan=2, sticky="we", padx=10, pady=6)
        else:
            self.m2_frame.grid(row=1, column=0, columnspan=2, sticky="we", padx=10, pady=6)

    # ------------------------------------------------------------------ file pickers

    def _filetypes(self, kind):
        if kind == 'skel':
            return [(self.t('filetype_skel'), "*.skel"), (self.t('filetype_all'), "*.*")]
        if kind == 'm2':
            return [(self.t('filetype_m2'), "*.m2"), (self.t('filetype_all'), "*.*")]
        return [(self.t('filetype_anim'), "*.anim"), (self.t('filetype_all'), "*.*")]

    def pick_parent(self):
        path = filedialog.askopenfilename(title=self.t('sel_parent_title'), filetypes=self._filetypes('skel'))
        if path:
            self.parent_path.set(path)

    def pick_daughter(self):
        path = filedialog.askopenfilename(title=self.t('sel_daughter_title'), filetypes=self._filetypes('skel'))
        if path:
            self.daughter_path.set(path)

    def pick_skel_for_anim(self):
        path = filedialog.askopenfilename(title=self.t('sel_skel_title'), filetypes=self._filetypes('skel'))
        if path:
            self.skel_path.set(path)

    def pick_m2(self):
        path = filedialog.askopenfilename(title=self.t('sel_m2_title'), filetypes=self._filetypes('m2'))
        if path:
            self.m2_path.set(path)

    def pick_m2_skel(self):
        path = filedialog.askopenfilename(title=self.t('sel_m2_skel_title'), filetypes=self._filetypes('skel'))
        if path:
            self.m2_skel_path.set(path)

    def pick_anims(self):
        paths = filedialog.askopenfilenames(title=self.t('sel_anim_title'), filetypes=self._filetypes('anim'))
        # askopenfilenames() ha diverse forme di ritorno "rotte" a seconda di
        # piattaforma/versione di Tk / has several "broken" return shapes
        # depending on platform/Tk version:
        #  (a) una stringa Tcl grezza / a raw Tcl string: "{C:/path 1/f.anim} {C:/f2.anim}"
        #  (b) una tupla con UN solo elemento che è ancora quella stringa grezza /
        #      a tuple with ONE element that is still that raw string
        #  (c) una tupla vera di percorsi già separati (il caso "giusto") /
        #      a real tuple of already-separated paths (the "good" case)
        # In tutti e tre i casi, self.tk.splitlist() produce sempre l'elenco
        # corretto / in all three cases, self.tk.splitlist() always produces
        # the correct list, so we always apply it unconditionally.
        #
        # Python 2 restituisce le stringhe di Tk come `unicode`, non `str` --
        # sono due tipi DIVERSI in Python 2 (a differenza di Python 3, dove
        # `str` copre già tutto) / Python 2 returns Tk strings as `unicode`,
        # not `str` -- two DIFFERENT types in Python 2 (unlike Python 3,
        # where `str` already covers both).
        try:
            string_types = basestring  # Python 2: str e unicode insieme / str and unicode together
        except NameError:
            string_types = str         # Python 3

        if isinstance(paths, string_types):
            raw = paths
        elif len(paths) == 1:
            raw = paths[0]
        else:
            raw = None

        if raw is not None and ('{' in raw or ' ' in raw):
            paths = self.tk.splitlist(raw)
        elif raw is not None:
            paths = (raw,)

        for p in paths:
            if p not in self.anim_paths:
                self.anim_paths.append(p)
                self.anim_listbox.insert("end", p)

    def remove_selected_anims(self):
        sel = list(self.anim_listbox.curselection())
        sel.reverse()
        for i in sel:
            del self.anim_paths[i]
            self.anim_listbox.delete(i)

    def clear_anims(self):
        self.anim_paths = []
        self.anim_listbox.delete(0, "end")

    # ------------------------------------------------------------------ logging

    def print_log(self, *args):
        text = " ".join(str(a) for a in args)
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ------------------------------------------------------------------ azione principale / main action

    def run_action(self):
        if self.mode.get() == "parent_daughter":
            self.run_merge_parent_daughter()
        elif self.mode.get() == "bake_anim":
            self.run_bake_anim()
        else:
            self.run_skel_into_m2()

    def run_merge_parent_daughter(self):
        parent = self.parent_path.get().strip()
        daughter = self.daughter_path.get().strip()

        if not parent or not os.path.isfile(parent):
            messagebox.showerror(self.t('err_title'), self.t('err_parent'))
            return
        if not daughter or not os.path.isfile(daughter):
            messagebox.showerror(self.t('err_title'), self.t('err_daughter'))
            return

        self.clear_log()

        real_print = print
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        builtins.print = self.print_log
        try:
            self.print_log(self.t('reading'))
            parent_chunks = ms.load(parent)
            daughter_chunks = ms.load(daughter)

            if 'SKPD' not in daughter_chunks:
                self.print_log(self.t('warn_no_skpd'))

            parent_skb1 = ms.parse_skb1(parent_chunks['SKB1'])
            parent_sks1 = ms.parse_sks1(parent_chunks['SKS1'])
            daughter_skb1 = ms.parse_skb1(daughter_chunks['SKB1'])
            daughter_sks1 = ms.parse_sks1(daughter_chunks['SKS1'])

            self.print_log(self.t('parent_stats') % (len(parent_skb1['bones']), len(parent_sks1['anims'])))
            self.print_log(self.t('daughter_stats') % (len(daughter_skb1['bones']), len(daughter_sks1['anims'])))
            self.print_log(self.t('merging'))

            merged_skb1, merged_sks1 = ms.merge(parent_skb1, parent_sks1,
                                                 daughter_skb1, daughter_sks1)

            out_chunks = [ms.make_chunk('SKL1', parent_chunks['SKL1'])]
            out_chunks.append(ms.make_chunk('SKS1', ms.write_sks1(merged_sks1)))
            out_chunks.append(ms.make_chunk('SKB1', ms.write_skb1(merged_skb1)))
            if 'SKA1' in parent_chunks:
                out_chunks.append(ms.make_chunk('SKA1', parent_chunks['SKA1']))
            if 'AFID' in parent_chunks:
                out_chunks.append(ms.make_chunk('AFID', parent_chunks['AFID']))
            if 'BFID' in parent_chunks:
                out_chunks.append(ms.make_chunk('BFID', parent_chunks['BFID']))
            result_bytes = b''.join(out_chunks)

        except Exception as e:
            self.print_log(self.t('error_prefix'), e)
            self.print_log(traceback.format_exc())
            messagebox.showerror(self.t('error_title_merge'), str(e))
            return
        finally:
            builtins.print = real_print

        default_name = os.path.splitext(os.path.basename(parent))[0] + "_merged.skel"
        save_path = filedialog.asksaveasfilename(
            title=self.t('save_title'),
            defaultextension=".skel",
            initialfile=default_name,
            filetypes=self._filetypes('skel')
        )
        if not save_path:
            self.print_log(self.t('save_cancelled'))
            return

        with open(save_path, 'wb') as f:
            f.write(result_bytes)

        self.print_log(self.t('done') % save_path)
        messagebox.showinfo(self.t('done_title'), self.t('done_msg') % save_path)

    def run_bake_anim(self):
        skel = self.skel_path.get().strip()
        anims = list(self.anim_paths)

        if not skel or not os.path.isfile(skel):
            messagebox.showerror(self.t('err_title'), self.t('err_skel'))
            return
        if not anims:
            messagebox.showerror(self.t('err_title'), self.t('err_anim'))
            return

        self.clear_log()

        real_print = print
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        builtins.print = self.print_log
        try:
            self.print_log(self.t('baking_start'))
            self.print_log(self.t('baking_flag_note'))

            default_name = os.path.splitext(os.path.basename(skel))[0] + "_baked.skel"
            save_path = filedialog.asksaveasfilename(
                title=self.t('save_baked_title'),
                defaultextension=".skel",
                initialfile=default_name,
                filetypes=self._filetypes('skel')
            )
            if not save_path:
                self.print_log(self.t('save_cancelled'))
                return

            mais.merge_skel_anim(skel, save_path, anims,
                                  force_all_embedded=self.force_all_embedded.get())

        except Exception as e:
            self.print_log(self.t('error_prefix'), e)
            self.print_log(traceback.format_exc())
            messagebox.showerror(self.t('error_title_bake'), str(e))
            return
        finally:
            builtins.print = real_print

        self.print_log(self.t('done') % save_path)
        messagebox.showinfo(self.t('done_title'), self.t('done_msg') % save_path)

    def run_skel_into_m2(self):
        m2 = self.m2_path.get().strip()
        skel = self.m2_skel_path.get().strip()

        if not m2 or not os.path.isfile(m2):
            messagebox.showerror(self.t('err_title'), self.t('err_m2'))
            return
        if not skel or not os.path.isfile(skel):
            messagebox.showerror(self.t('err_title'), self.t('err_skel'))
            return

        self.clear_log()

        real_print = print
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        builtins.print = self.print_log
        try:
            self.print_log(self.t('m2_baking_start'))
            self.print_log(self.t('m2_baking_note'))

            default_name = os.path.splitext(os.path.basename(m2))[0] + "_standalone.m2"
            save_path = filedialog.asksaveasfilename(
                title=self.t('save_m2_title'),
                defaultextension=".m2",
                initialfile=default_name,
                filetypes=self._filetypes('m2')
            )
            if not save_path:
                self.print_log(self.t('save_cancelled'))
                return

            msm.merge_skel_into_m2(m2, skel, save_path)

        except Exception as e:
            self.print_log(self.t('error_prefix'), e)
            self.print_log(traceback.format_exc())
            messagebox.showerror(self.t('error_title_bake'), str(e))
            return
        finally:
            builtins.print = real_print

        self.print_log(self.t('done') % save_path)
        messagebox.showinfo(self.t('done_title'), self.t('done_msg') % save_path)


if __name__ == '__main__':
    try:
        app = MergeSkelApp()
        app.mainloop()
    except Exception:
        _pause_and_exit("ERRORE durante l'avvio della finestra / Error starting the window:\n"
                         + traceback.format_exc())
