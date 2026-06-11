"""
Main application class for StrangeCat Monitor.
Handles window management, UI layout, and global events.
"""
import tkinter as tk
from tkinter import ttk
import time
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "base"))

from config import C, APP_NAME, APP_VER, T, _fmt_dur, _state_color
from ui.sidebar import Sidebar
from ui.performance import create_performance_view
from ui.settings import SettingsView


class App:
    """Main application window with Windows 11 Task Manager style."""

    def __init__(self, root: tk.Tk, cfg: dict, collector):
        self.root = root
        self.cfg = cfg
        self.collector = collector
        self.lang = cfg.get("language", "fr")
        self._alive = True
        self._active_tab = cfg.get("active_tab", "perf")
        self._selected = cfg.get("selected_metric", "cpu")

        # Drag / resize
        self._drag = False
        self._rsz = False
        self._dx = self._dy = 0
        self._rx = self._ry = self._rw = self._rh = self._wx = self._wy = 0

        # Sub-components
        self._sidebar: Sidebar | None = None
        self._detail = None
        self._settings_view: SettingsView | None = None
        self._content_frame: tk.Frame | None = None
        self._scroll_targets = []

        # Apply dark theme
        self._apply_tk_theme()

        self._build_window()
        self._build_titlebar()
        self._build_tabbar()
        self._build_footer()
        self._build_content()

        # Global scroll wheel binding (targets already registered in _build_content)
        root.bind_all("<MouseWheel>", self._on_global_scroll, add="+")
        root.bind_all("<Button-4>", self._on_global_scroll4, add="+")
        root.bind_all("<Button-5>", self._on_global_scroll5, add="+")

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll()

    def _apply_tk_theme(self):
        """Configure dark theme for the application."""
        r = self.root
        r.option_add("*TCombobox*Listbox.background", C["surface"])
        r.option_add("*TCombobox*Listbox.foreground", C["fg"])
        r.option_add("*TCombobox*Listbox.selectBackground", C["acc"])
        r.option_add("*TCombobox*Listbox.selectForeground", C["fg_hi"])
        r.option_add("*TCombobox*Listbox.font", "Segoe\\ UI 9")
        st = ttk.Style(r)
        st.theme_use("default")
        st.configure("Dark.TCombobox",
            fieldbackground=C["surface"],
            background=C["surface2"],
            foreground=C["fg"],
            arrowcolor=C["fg"],
            bordercolor=C["border"],
            lightcolor=C["border"],
            darkcolor=C["border"],
            relief="flat",
        )
        st.map("Dark.TCombobox",
            fieldbackground=[("readonly", C["surface"]),
                             ("disabled", C["surface2"])],
            foreground=[("readonly", C["fg"]),
                        ("disabled", C["fg_dim"])],
            background=[("active", C["surface2"]),
                        ("readonly", C["surface2"])],
        )
        st.configure("Vertical.TScrollbar",
            background=C["surface2"], troughcolor=C["bg"],
            arrowcolor=C["fg_dim"], bordercolor=C["bg"],
            relief="flat",
        )

    def _build_window(self):
        """Build the main window."""
        r = self.root
        r.overrideredirect(True)
        r.configure(bg=C["bg"])
        r.attributes("-topmost", bool(self.cfg.get("always_on_top", True)))
        r.attributes("-alpha", float(self.cfg.get("opacity", 0.97)))
        w = int(self.cfg.get("win_w", 980))
        h = int(self.cfg.get("win_h", 640))
        x = int(self.cfg.get("pos_x", 140))
        y = int(self.cfg.get("pos_y", 80))
        r.geometry(f"{w}x{h}+{x}+{y}")
        r.minsize(720, 480)
        r.bind("<Motion>", self._on_motion)
        r.bind("<ButtonPress-1>", self._on_press)
        r.bind("<B1-Motion>", self._on_drag_ev)
        r.bind("<ButtonRelease-1>", self._on_release)

    def _build_titlebar(self):
        """Build the title bar."""
        tb = tk.Frame(self.root, bg=C["header_bg"], height=36)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)
        self._titlebar = tb

        for w in (tb,):
            w.bind("<ButtonPress-1>", self._on_press)
            w.bind("<B1-Motion>", self._on_drag_ev)
            w.bind("<ButtonRelease-1>", self._on_release)

        left = tk.Frame(tb, bg=C["header_bg"])
        left.pack(side="left", padx=(14, 0))
        tk.Label(left, text="🐱", font=("Segoe UI Emoji", 11),
                 bg=C["header_bg"], fg=C["acc"]).pack(side="left", padx=(0, 8))
        tk.Label(left, text=APP_NAME, font=("Segoe UI", 9, "bold"),
                 bg=C["header_bg"], fg=C["fg_hi"]).pack(side="left")
        tk.Label(left, text=f"v{APP_VER}", font=("Segoe UI", 7),
                 bg=C["header_bg"], fg=C["fg_dark"]).pack(side="left", padx=(6, 0))

        right = tk.Frame(tb, bg=C["header_bg"])
        right.pack(side="right")

        def wbtn(txt, cmd, hbg=C["surface2"], hfg=C["fg_hi"]):
            b = tk.Label(right, text=txt, font=("Segoe UI", 11),
                         bg=C["header_bg"], fg=C["fg_dim"],
                         cursor="hand2", padx=14, pady=5)
            b.pack(side="left")
            b.bind("<Button-1>", lambda e: cmd())
            b.bind("<Enter>", lambda e, b=b: b.config(fg=hfg, bg=hbg))
            b.bind("<Leave>", lambda e, b=b: b.config(fg=C["fg_dim"], bg=C["header_bg"]))

        wbtn("—", self.hide)
        wbtn("✕", self._on_close, hbg="#c42b1c", hfg="#fff")
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x", side="top")

    def _build_tabbar(self):
        """Build the tab bar."""
        if hasattr(self, "_tabbar"):
            self._tabbar.destroy()
        self._tabbar = tk.Frame(self.root, bg=C["header_bg"], height=34)
        self._tabbar.pack(fill="x", side="top")
        self._tabbar.pack_propagate(False)

        self._tabbar.bind("<ButtonPress-1>", self._on_press)
        self._tabbar.bind("<B1-Motion>", self._on_drag_ev)
        self._tabbar.bind("<ButtonRelease-1>", self._on_release)

        for key, lk in [("perf", "tab_perf"), ("settings", "tab_set")]:
            active = (self._active_tab == key)
            bg = C["bg"] if active else C["header_bg"]
            fg = C["fg_hi"] if active else C["fg_dim"]
            font = ("Segoe UI", 9, "bold") if active else ("Segoe UI", 9)
            lbl = tk.Label(self._tabbar, text=f"  {T(lk, self.lang)}  ",
                           font=font, bg=bg, fg=fg, cursor="hand2",
                           padx=4, pady=6)
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, k=key: self._switch_tab(k))
            if not active:
                lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=C["fg_hi"]))
                lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=C["fg_dim"]))

        # Indicator line
        if hasattr(self, "_tab_line"):
            self._tab_line.destroy()
        self._tab_line = tk.Frame(self.root, bg=C["acc"], height=2)
        self._tab_line.pack(fill="x", side="top")

    def _rebuild_tabbar(self):
        """Rebuild the tabbar (e.g., after language change)."""
        self._build_tabbar()

    def _switch_tab(self, tab):
        """Switch between tabs."""
        if tab == self._active_tab:
            return
        self._active_tab = tab
        self.cfg["active_tab"] = tab
        self._build_tabbar()
        if self._content_frame:
            self._content_frame.destroy()
        self._sidebar = None
        self._detail = None
        self._detail_views = {}
        self._settings_view = None
        self._scroll_targets.clear()
        self._build_content()

    def _build_footer(self):
        """Build the footer."""
        tk.Frame(self.root, bg=C["border"], height=1).pack(fill="x", side="bottom")
        foot = tk.Frame(self.root, bg=C["foot_bg"], height=22)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)

        self._lbl_temp = tk.Label(foot, text="", font=("Segoe UI", 7),
                                  bg=C["foot_bg"], fg=C["fg_dark"], anchor="w")
        self._lbl_temp.pack(side="left", padx=12)

        self._lbl_session = tk.Label(foot, text="", font=("Segoe UI", 7),
                                     bg=C["foot_bg"], fg=C["fg_dim"], anchor="center")
        self._lbl_session.pack(side="left", expand=True)

        self._lbl_http = tk.Label(foot, text="", font=("Segoe UI", 7),
                                  bg=C["foot_bg"], fg=C["fg_dark"], anchor="e")
        self._lbl_http.pack(side="right", padx=12)

        # Resize grip
        self._grip = tk.Label(self.root, text="◢", font=("Segoe UI", 9),
                              bg=C["foot_bg"], fg=C["border2"], cursor="size_nw_se")
        self._grip.place(relx=1.0, rely=1.0, anchor="se", y=-2)
        self._grip.bind("<ButtonPress-1>", self._on_press)
        self._grip.bind("<B1-Motion>", self._on_drag_ev)
        self._grip.bind("<ButtonRelease-1>", self._on_release)

    def _build_content(self):
        """Build the content area."""
        self._content_frame = tk.Frame(self.root, bg=C["bg"])
        self._content_frame.pack(fill="both", expand=True, side="top")
        if self._active_tab == "perf":
            self._build_perf_layout()
        else:
            self._settings_view = SettingsView(self._content_frame, self)

    def _build_perf_layout(self):
        """Build the performance tab layout."""
        pane = tk.Frame(self._content_frame, bg=C["bg"])
        pane.pack(fill="both", expand=True)

        # Sidebar
        sb_frame = tk.Frame(pane, bg=C["sidebar_bg"], width=200)
        sb_frame.pack(side="left", fill="y")
        sb_frame.pack_propagate(False)
        tk.Frame(pane, bg=C["border"], width=1).pack(side="left", fill="y")

        # Build metrics list (cached drives - no slow rescan on the UI thread)
        from metrics import build_metrics
        from collector import cached_disk_drives
        disk_drives = cached_disk_drives()
        metrics = build_metrics(self.cfg, disk_drives)
        self._metrics = metrics

        self._sidebar = Sidebar(
            sb_frame, metrics,
            on_select=self.select_metric,
            selected_key=self._selected,
            app=self
        )

        # Right panel
        right = tk.Frame(pane, bg=C["panel_bg"])
        right.pack(side="left", fill="both", expand=True)
        self._right_panel = right
        self._detail_views = {}

        # Find the metric meta for the selected key (fallback to first)
        metric_meta = None
        for m in metrics:
            if m["key"] == self._selected:
                metric_meta = m
                break
        if metric_meta is None and metrics:
            metric_meta = metrics[0]
            self._selected = metric_meta["key"]

        if metric_meta:
            self._detail = create_performance_view(right, metric_meta)
            self._detail_views[metric_meta["key"]] = self._detail

    # Global scroll handling
    def register_scroll_target(self, canvas):
        """Register a canvas as a scroll target."""
        if canvas not in self._scroll_targets:
            self._scroll_targets.append(canvas)

    def _on_global_scroll(self, event):
        """Handle global mouse wheel scroll."""
        # Scroll all registered canvases
        for canvas in self._scroll_targets:
            try:
                canvas.yview_scroll(-1 * (event.delta // 120), "units")
            except Exception:
                pass

    def _on_global_scroll4(self, event):
        """Handle global scroll button 4 (Linux)."""
        for canvas in self._scroll_targets:
            try:
                canvas.yview_scroll(-1, "units")
            except Exception:
                pass

    def _on_global_scroll5(self, event):
        """Handle global scroll button 5 (Linux)."""
        for canvas in self._scroll_targets:
            try:
                canvas.yview_scroll(1, "units")
            except Exception:
                pass

    # Drag / resize handling
    def _in_grip(self, rx, ry) -> bool:
        """Check if cursor is in resize grip area."""
        ww = self.root.winfo_width()
        wh = self.root.winfo_height()
        return rx >= ww - 22 and ry >= wh - 22

    def _on_motion(self, e):
        """Handle mouse motion."""
        try:
            rx = e.x_root - self.root.winfo_rootx()
            ry = e.y_root - self.root.winfo_rooty()
            self.root.config(cursor="size_nw_se" if self._in_grip(rx, ry) else "")
        except Exception:
            pass

    def _on_press(self, e):
        """Handle mouse button press."""
        rx = e.x_root - self.root.winfo_rootx()
        ry = e.y_root - self.root.winfo_rooty()
        if self._in_grip(rx, ry):
            self._rsz = True
            self._drag = False
            self._rx, self._ry = e.x_root, e.y_root
            self._rw = self.root.winfo_width()
            self._rh = self.root.winfo_height()
            self._wx = self.root.winfo_x()
            self._wy = self.root.winfo_y()
        else:
            self._rsz = False
            self._drag = True
            self._dx = e.x_root - self.root.winfo_x()
            self._dy = e.y_root - self.root.winfo_y()

    def _on_drag_ev(self, e):
        """Handle mouse drag."""
        if self._rsz:
            nw = max(720, self._rw + (e.x_root - self._rx))
            nh = max(480, self._rh + (e.y_root - self._ry))
            self.cfg["win_w"] = nw
            self.cfg["win_h"] = nh
            self.root.geometry(f"{nw}x{nh}+{self._wx}+{self._wy}")
        elif self._drag:
            nx = e.x_root - self._dx
            ny = e.y_root - self._dy
            self.root.geometry(f"+{nx}+{ny}")
            self.cfg["pos_x"] = nx
            self.cfg["pos_y"] = ny

    def _on_release(self, e):
        """Handle mouse button release."""
        self._rsz = False
        self._drag = False
        try:
            self.root.config(cursor="")
        except Exception:
            pass

    # Polling
    def _poll(self):
        """Main UI update loop."""
        try:
            snap = self.collector.snapshot()
            self._update_footer(snap)
            if self._active_tab == "perf":
                hist = snap.get("_hist", {})
                if self._sidebar:
                    self._sidebar.update_values(snap)
                    self._sidebar.update_graphs(hist)
                if self._detail:
                    self._detail.update(snap, hist)
        except Exception:
            pass
        from config import POLL_MS
        self.root.after(POLL_MS, self._poll)

    def _update_footer(self, snap):
        """Update footer information."""
        try:
            method = snap.get("cpu_temp_method") or "unavailable"
            self._lbl_temp.configure(text=f"{T('temp_src', self.lang)}: {method}")
            up = snap.get("uptime_app", 0)
            self._lbl_session.configure(text=f"Session : {_fmt_dur(up)}")
            port = self.cfg.get("http_port", 5100)
            if self.cfg.get("http_enabled", True):
                self._lbl_http.configure(text=f"● HTTP :{port}", fg=C["ok"])
            else:
                self._lbl_http.configure(text="○ HTTP off", fg=C["fg_dark"])
        except Exception:
            pass

    # Metric selection
    def select_metric(self, key: str):
        """Select a metric to display."""
        self._selected = key
        self.cfg["selected_metric"] = key
        if self._sidebar:
            self._sidebar.update_selection(key)
        if self._detail is not None:
            # Switch detail view using a per-metric cache: views are built once
            # then shown/hidden, so switching is instant (no graph rebuild).
            metric_meta = None
            for m in getattr(self, "_metrics", []):
                if m["key"] == key:
                    metric_meta = m
                    break
            if not metric_meta:
                return
            # Hide the currently visible view.
            try:
                self._detail.pack_forget()
            except Exception:
                pass
            view = self._detail_views.get(key)
            if view is None or not view.winfo_exists():
                view = create_performance_view(self._right_panel, metric_meta)
                self._detail_views[key] = view
            else:
                view.pack(fill="both", expand=True)
            self._detail = view
            # Push current data immediately so the view isn't blank.
            try:
                snap = self.collector.snapshot()
                self._detail.update(snap, snap.get("_hist", {}))
            except Exception:
                pass

    # Close handling
    def _on_close(self):
        """Handle window close."""
        action = self.cfg.get("close_action", "ask")
        if action == "quit":
            self._do_quit()
        elif action == "hide":
            self.hide()
        else:
            self._close_dialog()

    def _close_dialog(self):
        """Show close dialog."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Fermer")
        dlg.geometry("300x140")
        dlg.configure(bg=C["surface"])
        dlg.attributes("-topmost", True)
        dlg.resizable(False, False)
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 140) // 2
        dlg.geometry(f"+{x}+{y}")
        tk.Label(dlg, text=T("close_q", self.lang),
                 font=("Segoe UI", 10, "bold"),
                 bg=C["surface"], fg=C["fg_hi"]).pack(pady=(16, 10))
        bf = tk.Frame(dlg, bg=C["surface"])
        bf.pack()
        rem = tk.BooleanVar(value=False)

        def do_hide():
            if rem.get():
                self.cfg["close_action"] = "hide"
            from config import save_cfg
            save_cfg(self.cfg)
            dlg.destroy()
            self.hide()

        def do_quit():
            if rem.get():
                self.cfg["close_action"] = "quit"
            from config import save_cfg
            save_cfg(self.cfg)
            dlg.destroy()
            self._do_quit()

        tk.Button(bf, text=T("minimize", self.lang), command=do_hide,
                  bg=C["surface2"], fg=C["fg"], font=("Segoe UI", 9),
                  relief="flat", padx=12, pady=6).pack(side="left", padx=6)
        tk.Button(bf, text=T("quit", self.lang), command=do_quit,
                  bg=C["acc_dim"], fg="#fff", font=("Segoe UI", 9),
                  relief="flat", padx=12, pady=6).pack(side="left", padx=6)
        tk.Checkbutton(dlg, text=T("remember", self.lang), variable=rem,
                       bg=C["surface"], fg=C["fg_dim"],
                       selectcolor=C["surface2"],
                       font=("Segoe UI", 8),
                       activebackground=C["surface"],
                       activeforeground=C["fg"]).pack(pady=8)

    def hide(self):
        """Hide the window."""
        self.root.withdraw()

    def show(self):
        """Show the window."""
        self.root.deiconify()
        self.root.lift()

    def _do_quit(self):
        """Quit the application."""
        self._alive = False
        self.collector.stop()
        from http_server import stop_http
        stop_http()
        from config import save_cfg
        save_cfg(self.cfg)
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            os._exit(0)
        except Exception:
            sys.exit(0)
