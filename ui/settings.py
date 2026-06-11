"""
Settings view for StrangeCat Monitor.
Configuration panel with dark themed comboboxes.
"""
import tkinter as tk
from tkinter import ttk
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "base"))

from config import C, T, set_startup, is_startup


def apply_dark_theme(root):
    """Apply dark theme to ttk scrollbars."""
    style = ttk.Style(root)
    style.theme_use("default")


class SettingsView:
    """Settings panel with properly dark comboboxes."""

    def __init__(self, parent: tk.Frame, app):
        self._app = app
        self._frame = tk.Frame(parent, bg=C["bg"])
        self._frame.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        """Build the settings UI."""
        app = self._app
        cfg = app.cfg
        lang = app.lang
        
        # Apply dark theme to root
        apply_dark_theme(app.root)

        # Canvas + scrollbar
        outer = tk.Frame(self._frame, bg=C["bg"])
        outer.pack(fill="both", expand=True)
        cv = tk.Canvas(outer, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical",
                           command=cv.yview, style="Vertical.TScrollbar")
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        content = tk.Frame(cv, bg=C["bg"])
        win_id = cv.create_window((0, 0), window=content, anchor="nw")

        def _resize(e):
            cv.itemconfig(win_id, width=e.width)
            cv.configure(scrollregion=cv.bbox("all"))
        cv.bind("<Configure>", _resize)
        content.bind("<Configure>",
            lambda e: cv.configure(scrollregion=cv.bbox("all")))

        # Register scroll target
        app.register_scroll_target(cv)

        P = dict(padx=24)

        def section(txt):
            fr = tk.Frame(content, bg=C["bg"])
            fr.pack(fill="x", pady=(20, 4), **P)
            tk.Label(fr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg=C["bg"], fg=C["fg_dark"]).pack(side="left")
            tk.Frame(content, bg=C["border"], height=1).pack(fill="x", **P)

        def row(label, fn):
            r = tk.Frame(content, bg=C["surface2"],
                         highlightbackground=C["border"], highlightthickness=1)
            r.pack(fill="x", pady=1, **P)
            tk.Label(r, text=label, font=("Segoe UI", 9),
                     bg=C["surface2"], fg=C["fg"],
                     width=34, anchor="w").pack(side="left", padx=14, pady=9)
            fn(r)
            return r

        def mk_check(r, var):
            def toggle():
                var.set(not var.get())
                apply()
            b = tk.Label(r, text="", font=("Segoe UI Emoji", 12),
                         bg=C["surface2"], fg=C["acc"],
                         cursor="hand2", padx=8)
            b.pack(side="left")

            def upd(*a):
                b.config(text="☑" if var.get() else "☐",
                         fg=C["acc"] if var.get() else C["fg_dim"])
            upd()
            var.trace_add("write", upd)
            b.bind("<Button-1>", lambda e: toggle())

        def mk_combo(r, var, values, w=12):
            # tk.OptionMenu (uses tk.Menu internally) works in overrideredirect
            # windows on Windows; ttk.Combobox (Toplevel popup) does not.
            om = tk.OptionMenu(r, var, *values, command=lambda _: apply())
            om.configure(
                bg=C["surface"], fg=C["fg"],
                activebackground=C["surface2"], activeforeground=C["fg_hi"],
                highlightthickness=1, highlightbackground=C["border"],
                highlightcolor=C["acc"],
                relief="flat", bd=0,
                font=("Segoe UI", 9),
                width=w, cursor="hand2",
                direction="below",
            )
            om["menu"].configure(
                bg=C["surface"], fg=C["fg"],
                activebackground=C["acc"], activeforeground="#ffffff",
                relief="flat", bd=1,
                activeborderwidth=0,
                font=("Segoe UI", 9),
            )
            om.pack(side="left", padx=8, pady=4)

        def mk_scale(r, var, lo, hi, res):
            tk.Scale(r, from_=lo, to=hi, resolution=res,
                     orient="horizontal", variable=var,
                     bg=C["surface2"], fg=C["fg"],
                     troughcolor=C["fg_dark"],
                     highlightthickness=0,
                     activebackground=C["acc"],
                     length=160, sliderlength=14,
                     command=lambda v: apply()
                     ).pack(side="left", padx=8)

        def mk_entry(r, var, w=7):
            e = tk.Entry(r, textvariable=var, width=w,
                         bg=C["surface"], fg=C["fg"],
                         insertbackground=C["fg"],
                         relief="flat", bd=6,
                         highlightbackground=C["border"],
                         highlightthickness=1)
            e.pack(side="left", padx=8, pady=4)
            e.bind("<Return>", lambda e: apply())
            e.bind("<FocusOut>", lambda e: apply())

        # Tk variables
        v_boot = tk.BooleanVar(value=is_startup())
        v_mini = tk.BooleanVar(value=bool(cfg.get("start_minimized")))
        v_top = tk.BooleanVar(value=bool(cfg.get("always_on_top", True)))
        v_opac = tk.DoubleVar(value=float(cfg.get("opacity", 0.97)))
        v_unit = tk.StringVar(value=str(cfg.get("temp_unit", "C")))
        v_lang = tk.StringVar(value=str(cfg.get("language", "fr")))
        v_http = tk.BooleanVar(value=bool(cfg.get("http_enabled", True)))
        v_port = tk.IntVar(value=int(cfg.get("http_port", 5100)))
        v_mode = tk.StringVar(value=str(cfg.get("refresh_mode", "normal")))
        v_disk = tk.DoubleVar(value=float(cfg.get("disk_interval", 60.0)))
        v_cpu = tk.BooleanVar(value=bool(cfg.get("show_cpu", True)))
        v_ram = tk.BooleanVar(value=bool(cfg.get("show_ram", True)))
        v_gpu = tk.BooleanVar(value=bool(cfg.get("show_gpu", True)))
        v_gpu_t = tk.BooleanVar(value=bool(cfg.get("show_gpu_temp", True)))
        v_vram = tk.BooleanVar(value=bool(cfg.get("show_vram", True)))
        v_net = tk.BooleanVar(value=bool(cfg.get("show_net", True)))
        v_cfan = tk.BooleanVar(value=bool(cfg.get("show_cpu_fan", True)))
        v_cfans = tk.BooleanVar(value=bool(cfg.get("show_case_fans", True)))
        v_disks = tk.BooleanVar(value=bool(cfg.get("show_disks", True)))

        def apply(*_):
            try:
                port = int(v_port.get())
            except Exception:
                port = cfg.get("http_port", 5100)
            old_http = cfg.get("http_enabled")
            old_port = cfg.get("http_port")
            old_lang = cfg.get("language")
            cfg.update(dict(
                start_on_boot=bool(v_boot.get()),
                start_minimized=bool(v_mini.get()),
                always_on_top=bool(v_top.get()),
                opacity=round(float(v_opac.get()), 2),
                temp_unit=str(v_unit.get()),
                language=str(v_lang.get()),
                http_enabled=bool(v_http.get()),
                http_port=port,
                refresh_mode=str(v_mode.get()),
                disk_interval=float(v_disk.get()),
                show_cpu=bool(v_cpu.get()),
                show_ram=bool(v_ram.get()),
                show_gpu=bool(v_gpu.get()),
                show_gpu_temp=bool(v_gpu_t.get()),
                show_vram=bool(v_vram.get()),
                show_net=bool(v_net.get()),
                show_cpu_fan=bool(v_cfan.get()),
                show_case_fans=bool(v_cfans.get()),
                show_disks=bool(v_disks.get()),
            ))
            set_startup(cfg["start_on_boot"])
            app.root.attributes("-topmost", cfg["always_on_top"])
            app.root.attributes("-alpha", cfg["opacity"])
            app.lang = cfg["language"]
            if cfg["language"] != old_lang:
                app._rebuild_tabbar()
            if cfg["http_enabled"] != old_http or cfg["http_port"] != old_port:
                if cfg["http_enabled"]:
                    from http_server import start_http
                    start_http(cfg["http_port"], app.collector)
                else:
                    from http_server import stop_http
                    stop_http()
            from config import save_cfg
            save_cfg(cfg)

        section(T("sec_gen", lang))
        row(T("boot", lang), lambda r: mk_check(r, v_boot))
        row(T("minimized", lang), lambda r: mk_check(r, v_mini))
        row(T("ontop", lang), lambda r: mk_check(r, v_top))

        section(T("sec_disp", lang))
        row(T("opacity", lang), lambda r: mk_scale(r, v_opac, 0.3, 1.0, 0.05))
        row(T("unit", lang), lambda r: mk_combo(r, v_unit, ["C", "F"], 4))
        row(T("lang", lang), lambda r: mk_combo(r, v_lang, ["fr", "en"], 5))

        def close_widget(r):
            def reset():
                cfg["close_action"] = "ask"
                from config import save_cfg
                save_cfg(cfg)
            tk.Button(r, text=T("close_reset", lang),
                      font=("Segoe UI", 8), bg=C["acc"], fg="#fff",
                      cursor="hand2", relief="flat",
                      padx=12, pady=4, command=reset).pack(side="left", padx=8)
        row(T("close_lbl", lang), close_widget)

        section(T("sec_net", lang))
        row(T("http_on", lang), lambda r: mk_check(r, v_http))

        def port_row(r):
            mk_entry(r, v_port, 6)
            tk.Label(r, text="→ 127.0.0.1:<port>/performance",
                     font=("Segoe UI", 8), bg=C["surface2"],
                     fg=C["fg_dark"]).pack(side="left", padx=4)
        row(T("http_port", lang), port_row)

        section(T("sec_met", lang))
        row(T("show_cpu", lang), lambda r: mk_check(r, v_cpu))
        row(T("show_ram", lang), lambda r: mk_check(r, v_ram))
        row(T("show_gpu", lang), lambda r: mk_check(r, v_gpu))
        row(T("show_gpu_temp", lang), lambda r: mk_check(r, v_gpu_t))
        row(T("show_vram", lang), lambda r: mk_check(r, v_vram))
        row(T("show_net", lang), lambda r: mk_check(r, v_net))
        row(T("show_cpu_fan", lang), lambda r: mk_check(r, v_cfan))
        row(T("show_case_fans", lang), lambda r: mk_check(r, v_cfans))
        row(T("show_disks", lang), lambda r: mk_check(r, v_disks))

        section(T("sec_perf", lang))
        row(T("refresh", lang), lambda r: mk_combo(r, v_mode, ["realtime", "normal", "low"], 10))
        row("Disk interval (s)", lambda r: mk_entry(r, v_disk, 6))

        # CPU Temp source info
        section("CPU TEMP SOURCE")
        try:
            snap = app.collector.snapshot()
            val = snap.get("cpu_temp")
            method = snap.get("cpu_temp_method", "—")
        except Exception:
            val, method = None, "—"
        info = tk.Frame(content, bg=C["surface"],
                        highlightbackground=C["border2"], highlightthickness=1)
        info.pack(fill="x", pady=4, **P)
        icon = "✓" if val else "✗"
        fg = C["ok"] if val else C["hot"]
        txt = f"{icon}  {val:.1f}°  via {method}" if val else f"{icon}  {method}"
        tk.Label(info, text=txt, font=("Consolas", 9, "bold"),
                 bg=C["surface"], fg=fg, anchor="w").pack(
                     anchor="w", padx=14, pady=(8, 4))
        tk.Label(info,
                 text="Priorité : psutil → LibreHardwareMonitor → OpenHardwareMonitor → CoreTemp",
                 font=("Consolas", 7), bg=C["surface"],
                 fg=C["fg_dark"], anchor="w").pack(anchor="w", padx=14, pady=(0, 4))
        if not val:
            tk.Label(info,
                     text="→ Lancez LibreHardwareMonitor en Administrateur.",
                     font=("Consolas", 7), bg=C["surface"],
                     fg=C["warn"], anchor="w").pack(anchor="w", padx=14, pady=(0, 8))
        else:
            tk.Frame(info, height=4, bg=C["surface"]).pack()

        # ── OC / Undervolt ────────────────────────────────────────────
        section("OC / UNDERVOLT  (⚠ Admin requis)")

        import subprocess as _sp
        import shutil as _sh

        def _run(*args, check=False):
            try:
                _sp.run(args, check=check,
                        creationflags=_sp.CREATE_NO_WINDOW,
                        stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
                return True
            except Exception:
                return False

        # CPU max processor state (%)
        def _get_cpu_max():
            try:
                out = _sp.check_output(
                    ["powercfg", "/query", "SCHEME_CURRENT",
                     "SUB_PROCESSOR", "PROCTHROTTLEMAX"],
                    creationflags=_sp.CREATE_NO_WINDOW, text=True)
                for line in out.splitlines():
                    if "Valeur d'alimentation secteur actuelle" in line \
                            or "Current AC Power Setting Index" in line:
                        return int(line.strip().split()[-1], 16)
            except Exception:
                pass
            return 100

        v_cpu_max = tk.IntVar(value=_get_cpu_max())

        def _apply_cpu_max(*_):
            val = int(v_cpu_max.get())
            _run("powercfg", "/setacvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(val))
            _run("powercfg", "/setdcvalueindex", "SCHEME_CURRENT",
                 "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(val))
            _run("powercfg", "/setactive", "SCHEME_CURRENT")

        def cpu_max_row(r):
            mk_scale(r, v_cpu_max, 20, 100, 5)
            v_cpu_max.trace_add("write", _apply_cpu_max)
            tk.Label(r, text="%", font=("Segoe UI", 9),
                     bg=C["surface2"], fg=C["fg_dark"]).pack(side="left")

        row("Perf. max CPU (plan énergie)", cpu_max_row)

        # GPU tools info
        oc_info = tk.Frame(content, bg=C["surface"],
                           highlightbackground=C["border2"], highlightthickness=1)
        oc_info.pack(fill="x", pady=4, **P)

        def _launch_msi(*_):
            paths = [
                r"C:\Program Files (x86)\MSI Afterburner\MSIAfterburner.exe",
                r"C:\Program Files\MSI Afterburner\MSIAfterburner.exe",
            ]
            for p in paths:
                if _sh.which(p) or __import__("os").path.exists(p):
                    _sp.Popen([p])
                    return
            import tkinter.messagebox as mb
            mb.showinfo("MSI Afterburner",
                        "MSI Afterburner non trouvé.\nInstallation : msi.com/afterburner")

        tk.Label(oc_info, text="GPU OC / Undervolt",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["surface"], fg=C["fg"]).pack(anchor="w", padx=14, pady=(8, 2))
        tk.Label(oc_info,
                 text="Utilise MSI Afterburner pour OC/undervolt GPU\n"
                      "(Core Voltage, Core Clock, Memory Clock).",
                 font=("Segoe UI", 8), bg=C["surface"],
                 fg=C["fg_dark"], justify="left").pack(anchor="w", padx=14)
        btn_msi = tk.Button(oc_info, text="Ouvrir MSI Afterburner",
                            font=("Segoe UI", 8), bg=C["acc"], fg="#fff",
                            cursor="hand2", relief="flat", padx=10, pady=4,
                            command=_launch_msi)
        btn_msi.pack(anchor="w", padx=14, pady=(4, 10))

        tk.Frame(content, bg=C["bg"], height=20).pack()

        content.update_idletasks()
        cv.configure(scrollregion=cv.bbox("all"))
