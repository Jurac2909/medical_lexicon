from __future__ import annotations

import asyncio
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .exporters import EXPORTERS
from .fetcher import TermInfoFetcher
from .logger import LOG_FILE, get_logger, log_exceptions
from .models import MedicalTerm
from .ner import MedicalNERAnalyzer

EXAMPLE_TEXT = (
    "The patient presented with severe chest pain, persistent cough and high "
    "fever. He was diagnosed with pneumonia and type 2 diabetes. Treatment "
    "included antibiotics, insulin therapy and regular blood pressure "
    "monitoring. The doctor also recommended an MRI scan to rule out a stroke."
)

ACCENT = "#2c6e91"
ACCENT_DARK = "#1f5170"
BG = "#f4f6f8"

CATEGORY_COLORS = {
    "disease": "#fde2e2",
    "symptom": "#fff1d6",
    "therapy": "#e3f6e8",
    "diagnostics": "#ece4f6",
    "anatomy": "#e2eefb",
}


class MedicalNERApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.log = get_logger()
        self.analyzer = MedicalNERAnalyzer()
        self.fetcher = TermInfoFetcher()

        self.terms: list[MedicalTerm] = []
        self._result_queue: "queue.Queue" = queue.Queue()
        self._busy = False

        self._build_ui()
        self.root.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        self.root.title("Medical Term Analysis")
        self.root.geometry("840x660")
        self.root.minsize(720, 560)
        self.root.configure(bg=BG)

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG)
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

        header = tk.Frame(self.root, bg=ACCENT)
        header.pack(fill="x")
        tk.Label(
            header,
            text="🩺  Medical Term Analysis",
            bg=ACCENT,
            fg="white",
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 0))
        tk.Label(
            header,
            text="Detects diseases, symptoms, therapies, diagnostics and anatomy "
            "using a neural network (NER).",
            bg=ACCENT,
            fg="#d6e6f0",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Input text", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        text_wrap = tk.Frame(main, bg="#cfd8df", bd=0)
        text_wrap.pack(fill="x", pady=(4, 12))
        self.text_input = tk.Text(
            text_wrap,
            height=6,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            padx=8,
            pady=6,
            bg="white",
        )
        self.text_input.pack(fill="x", padx=1, pady=1)
        self.text_input.insert("1.0", EXAMPLE_TEXT)

        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=(0, 12))
        self.btn_analyze = ttk.Button(
            btns, text="Analyze", style="Accent.TButton", command=self.on_analyze
        )
        self.btn_analyze.pack(side="left", ipadx=6)
        self.btn_clear = ttk.Button(btns, text="Clear", command=self.on_clear)
        self.btn_clear.pack(side="left", padx=(8, 0))

        ttk.Label(btns, text="Export to").pack(side="left", padx=(24, 6))
        self.btn_csv = ttk.Button(btns, text="CSV", command=lambda: self.on_export("CSV"))
        self.btn_csv.pack(side="left")
        self.btn_pdf = ttk.Button(btns, text="PDF", command=lambda: self.on_export("PDF"))
        self.btn_pdf.pack(side="left", padx=(8, 0))

        ttk.Label(
            main,
            text="ℹ  Term definitions are not shown here — they are included in the "
            "CSV and PDF exports.",
            foreground="#6b7a86",
            font=("Segoe UI", 9, "italic"),
        ).pack(anchor="w", pady=(0, 10))

        self.results_header = tk.StringVar(value="Found terms")
        ttk.Label(
            main, textvariable=self.results_header, font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        table_frame = ttk.Frame(main)
        table_frame.pack(fill="both", expand=True, pady=(4, 12))

        columns = ("term", "category", "confidence")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        self.tree.heading("term", text="Term")
        self.tree.heading("category", text="Category")
        self.tree.heading("confidence", text="Confidence")
        self.tree.column("term", width=420, anchor="w")
        self.tree.column("category", width=160, anchor="center", stretch=False)
        self.tree.column("confidence", width=130, anchor="center", stretch=False)
        for category, color in CATEGORY_COLORS.items():
            self.tree.tag_configure(category, background=color)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        status_frame = ttk.Frame(main)
        status_frame.pack(fill="x")
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(
            status_frame, textvariable=self.status, foreground=ACCENT_DARK
        ).pack(side="left")
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=160)
        self.progress.pack(side="right")

    @log_exceptions(reraise=False)
    def on_analyze(self) -> None:
        if self._busy:
            return
        text = self.text_input.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter text to analyze.")
            return

        self._set_busy(True, "Loading model and analyzing text...")
        worker = threading.Thread(target=self._analyze_worker, args=(text,), daemon=True)
        worker.start()

    def _analyze_worker(self, text: str) -> None:
        try:
            terms = self.analyzer.analyze(text)
            if terms:
                terms = asyncio.run(self.fetcher.fetch_all(terms))
            self._result_queue.put(("ok", terms))
        except Exception as exc:
            self._result_queue.put(("error", exc))

    def _poll_queue(self) -> None:
        try:
            kind, payload = self._result_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            if kind == "ok":
                self._show_results(payload)
            else:
                self._set_busy(False, "Error during analysis.")
                messagebox.showerror(
                    "Error",
                    f"An error occurred:\n{payload}\n\n"
                    f"Details have been written to:\n{LOG_FILE}",
                )
        finally:
            self.root.after(100, self._poll_queue)

    def _show_results(self, terms: list[MedicalTerm]) -> None:
        self.terms = terms
        for item in self.tree.get_children():
            self.tree.delete(item)
        for t in terms:
            self.tree.insert(
                "",
                "end",
                values=(t.text, t.category, f"{t.score * 100:.1f}%"),
                tags=(t.category,),
            )
        self.results_header.set(f"Found terms ({len(terms)})")
        self._set_busy(False, f"Done. Found {len(terms)} terms. Export to save definitions.")
        if not terms:
            messagebox.showinfo("Result", "No medical terms were found in the text.")

    @log_exceptions(reraise=False)
    def on_export(self, fmt: str) -> None:
        if not self.terms:
            messagebox.showinfo("Export", "No results to export. Analyze some text first.")
            return
        exporter = EXPORTERS[fmt]
        path = filedialog.asksaveasfilename(
            title=f"Save as {exporter.description}",
            defaultextension=exporter.extension,
            filetypes=[(exporter.description, f"*{exporter.extension}")],
            initialfile=f"medical_terms{exporter.extension}",
        )
        if not path:
            return
        try:
            saved = exporter.export(self.terms, path)
        except ImportError:
            messagebox.showerror(
                "Missing library",
                "PDF export requires the 'reportlab' library.\n"
                "Install it with:  pip install reportlab",
            )
            return
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))
            return
        self.status.set(f"Exported: {saved}")
        messagebox.showinfo("Export successful", f"File saved (with definitions):\n{saved}")

    @log_exceptions(reraise=False)
    def on_clear(self) -> None:
        self.text_input.delete("1.0", "end")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.terms = []
        self.results_header.set("Found terms")
        self.status.set("Ready.")

    def _set_busy(self, busy: bool, message: str) -> None:
        self._busy = busy
        self.status.set(message)
        state = "disabled" if busy else "normal"
        for btn in (self.btn_analyze, self.btn_csv, self.btn_pdf, self.btn_clear):
            btn.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()


def run() -> None:
    root = tk.Tk()
    MedicalNERApp(root)
    root.mainloop()
