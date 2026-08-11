#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Compatibile con Python 2.6+ e Python 3.
from __future__ import print_function
"""
merge_skel_gui.py — interfaccia grafica per merge_skel.py / merge_anim_into_skel.py

Due modalità separate, selezionabili in alto:

  1) "Unisci Genitore + Figlia"
     — comportamento originale: unisce due .skel (stessa gerarchia di ossa)
     producendo uno .skel standalone.

  2) "Incorpora .anim in uno .skel"
     — prende UNO .skel e uno o più file .anim (formato chunked AFM2/AFSB,
     quello usato quando il modello ha uno .skel) e incorpora i dati delle
     animazioni direttamente nello SKB1/SKS1 dello .skel, impostando il bit
     0x20 (embedded) nei flag di ogni animazione incorporata e rimuovendo la
     relativa voce da AFID. Utile quando il modello ha UN SOLO .skel e non
     serve alcun merge genitore/figlia.

Richiede che merge_skel.py e merge_anim_into_skel.py siano nella stessa
cartella (li importa direttamente).

Uso: python merge_skel_gui.py   (o "python3 merge_skel_gui.py")

Su Windows/macOS tkinter è già incluso in Python.
Su Linux, se manca, installalo con: sudo apt install python3-tk  (o python-tk per Python 2)
"""

import os
import sys
import traceback


def _pause_and_exit(msg):
    """Evita che la finestra del prompt si chiuda subito su errore in avvio,
    così l'errore resta leggibile invece di sparire in un lampo."""
    print(msg)
    try:
        raw_input("\nPremi INVIO per uscire...")  # Python 2
    except NameError:
        input("\nPremi INVIO per uscire...")      # Python 3
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
            "ERRORE: il modulo tkinter non e' disponibile.\n"
            "Su Linux installa con: sudo apt install python3-tk\n"
            "Dettaglio: %s" % e
        )

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_missing = [f for f in ("merge_skel.py", "merge_anim_into_skel.py", "merge_skel_into_m2.py")
            if not os.path.isfile(os.path.join(HERE, f))]
if _missing:
    _pause_and_exit(
        "ERRORE: questi file devono stare nella STESSA cartella di merge_skel_gui.py:\n  "
        + "\n  ".join(_missing)
        + "\n\nCartella attuale: %s" % HERE
    )

try:
    import merge_skel as ms
    import merge_anim_into_skel as mais
    import merge_skel_into_m2 as msm
except Exception as e:
    _pause_and_exit("ERRORE durante l'importazione di merge_skel.py / merge_anim_into_skel.py / "
                     "merge_skel_into_m2.py:\n%s" % traceback.format_exc())


class MergeSkelApp(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("Merge .skel / Incorpora .anim / Incorpora .m2")
        self.resizable(False, False)

        self.mode = tk.StringVar(value="parent_daughter")

        pad = {'padx': 10, 'pady': 6}

        # ---- selettore modalità -------------------------------------------------
        mode_frame = tk.LabelFrame(self, text="Modalità")
        mode_frame.grid(row=0, column=0, columnspan=2, sticky="we", **pad)
        tk.Radiobutton(mode_frame, text="Unisci Genitore + Figlia (.skel + .skel)",
                        variable=self.mode, value="parent_daughter",
                        command=self.refresh_mode).pack(anchor="w", padx=8, pady=2)
        tk.Radiobutton(mode_frame, text="Incorpora .anim in uno .skel (.skel + uno o più .anim)",
                        variable=self.mode, value="bake_anim",
                        command=self.refresh_mode).pack(anchor="w", padx=8, pady=2)
        tk.Radiobutton(mode_frame, text="Incorpora uno .skel in un .m2 (.m2 + .skel)",
                        variable=self.mode, value="skel_into_m2",
                        command=self.refresh_mode).pack(anchor="w", padx=8, pady=2)

        # ---- pannello: unisci genitore + figlia ---------------------------------
        self.pd_frame = tk.LabelFrame(self, text="Genitore + Figlia")
        self.parent_path = tk.StringVar()
        self.daughter_path = tk.StringVar()

        tk.Label(self.pd_frame, text="Skeleton GENITORE (.skel):").grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self.pd_frame, textvariable=self.parent_path, width=55).grid(row=1, column=0, **pad)
        tk.Button(self.pd_frame, text="Sfoglia...", command=self.pick_parent).grid(row=1, column=1, **pad)

        tk.Label(self.pd_frame, text="Skeleton FIGLIA (.skel):").grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(self.pd_frame, textvariable=self.daughter_path, width=55).grid(row=3, column=0, **pad)
        tk.Button(self.pd_frame, text="Sfoglia...", command=self.pick_daughter).grid(row=3, column=1, **pad)

        # ---- pannello: incorpora .anim ------------------------------------------
        self.anim_frame = tk.LabelFrame(self, text="Incorpora .anim")
        self.skel_path = tk.StringVar()
        self.anim_paths = []  # lista di path selezionati

        tk.Label(self.anim_frame, text="Skeleton (.skel):").grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self.anim_frame, textvariable=self.skel_path, width=55).grid(row=1, column=0, **pad)
        tk.Button(self.anim_frame, text="Sfoglia...", command=self.pick_skel_for_anim).grid(row=1, column=1, **pad)

        tk.Label(self.anim_frame, text="File .anim (uno o più):").grid(row=2, column=0, sticky="w", **pad)
        self.anim_listbox = tk.Listbox(self.anim_frame, width=55, height=6, selectmode="extended")
        self.anim_listbox.grid(row=3, column=0, **pad)
        anim_btns = tk.Frame(self.anim_frame)
        anim_btns.grid(row=3, column=1, sticky="n", **pad)
        tk.Button(anim_btns, text="Aggiungi...", command=self.pick_anims).pack(fill="x", pady=2)
        tk.Button(anim_btns, text="Rimuovi selezionati", command=self.remove_selected_anims).pack(fill="x", pady=2)
        tk.Button(anim_btns, text="Svuota lista", command=self.clear_anims).pack(fill="x", pady=2)

        # ---- pannello: incorpora .skel in un .m2 --------------------------------
        self.m2_frame = tk.LabelFrame(self, text="Incorpora .skel in .m2")
        self.m2_path = tk.StringVar()
        self.m2_skel_path = tk.StringVar()

        tk.Label(self.m2_frame, text="Modello (.m2):").grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self.m2_frame, textvariable=self.m2_path, width=55).grid(row=1, column=0, **pad)
        tk.Button(self.m2_frame, text="Sfoglia...", command=self.pick_m2).grid(row=1, column=1, **pad)

        tk.Label(self.m2_frame, text="Skeleton (.skel):").grid(row=2, column=0, sticky="w", **pad)
        tk.Entry(self.m2_frame, textvariable=self.m2_skel_path, width=55).grid(row=3, column=0, **pad)
        tk.Button(self.m2_frame, text="Sfoglia...", command=self.pick_m2_skel).grid(row=3, column=1, **pad)

        tk.Label(self.m2_frame, text="Incorpora ossa, sequenze, sequenze globali e attacchi\n"
                                      "direttamente nel .m2; rimuove la dipendenza SKID/.skel.",
                 justify="left", fg="#555555").grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))

        # ---- pulsante esegui + log -----------------------------------------------
        self.merge_btn = tk.Button(self, text="Esegui e salva...",
                                    command=self.run_action, bg="#2e7d32", fg="white",
                                    height=2)
        self.merge_btn.grid(row=2, column=0, columnspan=2, sticky="we", **pad)

        tk.Label(self, text="Log:").grid(row=3, column=0, sticky="w", padx=10)
        self.log = ScrolledText(self, width=70, height=16, state="disabled")
        self.log.grid(row=4, column=0, columnspan=2, padx=10, pady=(0, 10))

        self.refresh_mode()

    # ------------------------------------------------------------------ modalità

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

    def pick_parent(self):
        path = filedialog.askopenfilename(
            title="Seleziona lo skeleton GENITORE",
            filetypes=[("WoW skeleton", "*.skel"), ("Tutti i file", "*.*")]
        )
        if path:
            self.parent_path.set(path)

    def pick_daughter(self):
        path = filedialog.askopenfilename(
            title="Seleziona lo skeleton FIGLIA",
            filetypes=[("WoW skeleton", "*.skel"), ("Tutti i file", "*.*")]
        )
        if path:
            self.daughter_path.set(path)

    def pick_skel_for_anim(self):
        path = filedialog.askopenfilename(
            title="Seleziona lo skeleton (.skel) in cui incorporare gli .anim",
            filetypes=[("WoW skeleton", "*.skel"), ("Tutti i file", "*.*")]
        )
        if path:
            self.skel_path.set(path)

    def pick_m2(self):
        path = filedialog.askopenfilename(
            title="Seleziona il modello (.m2)",
            filetypes=[("WoW model", "*.m2"), ("Tutti i file", "*.*")]
        )
        if path:
            self.m2_path.set(path)

    def pick_m2_skel(self):
        path = filedialog.askopenfilename(
            title="Seleziona lo skeleton (.skel) da incorporare nel .m2",
            filetypes=[("WoW skeleton", "*.skel"), ("Tutti i file", "*.*")]
        )
        if path:
            self.m2_skel_path.set(path)

    def pick_anims(self):
        paths = filedialog.askopenfilenames(
            title="Seleziona uno o più file .anim",
            filetypes=[("WoW anim", "*.anim"), ("Tutti i file", "*.*")]
        )
        # askopenfilenames() ha diverse forme di ritorno "rotte" a seconda di
        # piattaforma/versione di Tk:
        #  (a) una stringa Tcl grezza: "{C:/percorso 1/f.anim} {C:/f2.anim}"
        #  (b) una tupla con UN solo elemento che è ancora quella stringa grezza
        #  (c) una tupla vera di percorsi già separati (il caso "giusto")
        # In tutti e tre i casi, ripassarla per self.tk.splitlist() produce
        # sempre l'elenco corretto di percorsi (senza graffe), quindi la
        # applichiamo sempre, incondizionatamente.
        # Python 2 restituisce le stringhe di Tk come `unicode`, non `str` --
        # sono due tipi DIVERSI in Python 2 (a differenza di Python 3, dove
        # `str` copre già tutto). Un controllo `isinstance(paths, str)`
        # fallisce silenziosamente su un valore `unicode`, lasciando passare
        # la stringa grezza non separata -- causa reale del problema.
        try:
            string_types = basestring  # Python 2: str e unicode insieme
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

    # ------------------------------------------------------------------ azione principale

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
            messagebox.showerror("Errore", "Seleziona un file GENITORE valido.")
            return
        if not daughter or not os.path.isfile(daughter):
            messagebox.showerror("Errore", "Seleziona un file FIGLIA valido.")
            return

        self.clear_log()

        real_print = print
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        builtins.print = self.print_log
        try:
            self.print_log("Lettura file...")
            parent_chunks = ms.load(parent)
            daughter_chunks = ms.load(daughter)

            if 'SKPD' not in daughter_chunks:
                self.print_log("[avviso] il file 'figlia' non ha un chunk SKPD: "
                                "sei sicuro sia lo skeleton figlia e non il genitore?")

            parent_skb1 = ms.parse_skb1(parent_chunks['SKB1'])
            parent_sks1 = ms.parse_sks1(parent_chunks['SKS1'])
            daughter_skb1 = ms.parse_skb1(daughter_chunks['SKB1'])
            daughter_sks1 = ms.parse_sks1(daughter_chunks['SKS1'])

            self.print_log("Genitore: %d ossa, %d animazioni"
                            % (len(parent_skb1['bones']), len(parent_sks1['anims'])))
            self.print_log("Figlia:   %d ossa, %d animazioni"
                            % (len(daughter_skb1['bones']), len(daughter_sks1['anims'])))
            self.print_log("Merge in corso...")

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
            self.print_log("ERRORE:", e)
            self.print_log(traceback.format_exc())
            messagebox.showerror("Errore durante il merge", str(e))
            return
        finally:
            builtins.print = real_print

        default_name = os.path.splitext(os.path.basename(parent))[0] + "_merged.skel"
        save_path = filedialog.asksaveasfilename(
            title="Salva il file .skel unito",
            defaultextension=".skel",
            initialfile=default_name,
            filetypes=[("WoW skeleton", "*.skel"), ("Tutti i file", "*.*")]
        )
        if not save_path:
            self.print_log("Salvataggio annullato dall'utente.")
            return

        with open(save_path, 'wb') as f:
            f.write(result_bytes)

        self.print_log("Fatto! Salvato in: %s" % save_path)
        messagebox.showinfo("Completato", "File salvato in:\n%s" % save_path)

    def run_bake_anim(self):
        skel = self.skel_path.get().strip()
        anims = list(self.anim_paths)

        if not skel or not os.path.isfile(skel):
            messagebox.showerror("Errore", "Seleziona un file .skel valido.")
            return
        if not anims:
            messagebox.showerror("Errore", "Aggiungi almeno un file .anim.")
            return

        self.clear_log()

        real_print = print
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        builtins.print = self.print_log
        try:
            self.print_log("Lettura .skel e .anim, incorporazione in corso...")
            self.print_log("(imposta il flag 0x20 'embedded' su ogni animazione incorporata "
                            "e rimuove la relativa voce da AFID)")

            default_name = os.path.splitext(os.path.basename(skel))[0] + "_baked.skel"
            save_path = filedialog.asksaveasfilename(
                title="Salva lo .skel con gli .anim incorporati",
                defaultextension=".skel",
                initialfile=default_name,
                filetypes=[("WoW skeleton", "*.skel"), ("Tutti i file", "*.*")]
            )
            if not save_path:
                self.print_log("Salvataggio annullato dall'utente.")
                return

            mais.merge_skel_anim(skel, save_path, anims)

        except Exception as e:
            self.print_log("ERRORE:", e)
            self.print_log(traceback.format_exc())
            messagebox.showerror("Errore durante l'incorporazione", str(e))
            return
        finally:
            builtins.print = real_print

        self.print_log("Fatto! Salvato in: %s" % save_path)
        messagebox.showinfo("Completato", "File salvato in:\n%s" % save_path)

    def run_skel_into_m2(self):
        m2 = self.m2_path.get().strip()
        skel = self.m2_skel_path.get().strip()

        if not m2 or not os.path.isfile(m2):
            messagebox.showerror("Errore", "Seleziona un file .m2 valido.")
            return
        if not skel or not os.path.isfile(skel):
            messagebox.showerror("Errore", "Seleziona un file .skel valido.")
            return

        self.clear_log()

        real_print = print
        try:
            import builtins
        except ImportError:
            import __builtin__ as builtins
        builtins.print = self.print_log
        try:
            self.print_log("Lettura .m2 e .skel, incorporazione in corso...")
            self.print_log("(incorpora ossa, sequenze, sequenze globali e attacchi nel .m2; "
                            "rimuove il chunk SKID)")

            default_name = os.path.splitext(os.path.basename(m2))[0] + "_standalone.m2"
            save_path = filedialog.asksaveasfilename(
                title="Salva il .m2 con lo .skel incorporato",
                defaultextension=".m2",
                initialfile=default_name,
                filetypes=[("WoW model", "*.m2"), ("Tutti i file", "*.*")]
            )
            if not save_path:
                self.print_log("Salvataggio annullato dall'utente.")
                return

            msm.merge_skel_into_m2(m2, skel, save_path)

        except Exception as e:
            self.print_log("ERRORE:", e)
            self.print_log(traceback.format_exc())
            messagebox.showerror("Errore durante l'incorporazione", str(e))
            return
        finally:
            builtins.print = real_print

        self.print_log("Fatto! Salvato in: %s" % save_path)
        messagebox.showinfo("Completato", "File salvato in:\n%s" % save_path)


if __name__ == '__main__':
    try:
        app = MergeSkelApp()
        app.mainloop()
    except Exception:
        _pause_and_exit("ERRORE durante l'avvio della finestra:\n" + traceback.format_exc())
