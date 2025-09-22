import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from tkinter import font as tkfont
import base64, zlib, struct
import json

from dd2 import download_icon_from_google

# 主题配色预设（可扩展）
THEMES = {
    "深色": {
        "bg": "#1e1e2f",
        "panel": "#23233a",
        "text": "#e5e9f0",
        "subtext": "#a6accd",
        "accent": "#7aa2f7",
        "success": "#9ece6a",
        "field_bg": "#2b2b40",
    },
    "浅色": {
        "bg": "#f7f7fb",
        "panel": "#ffffff",
        "text": "#1f2335",
        "subtext": "#6b7280",
        "accent": "#2563eb",
        "success": "#16a34a",
        "field_bg": "#f3f4f6",
    },
    "墨绿": {
        "bg": "#0f1a14",
        "panel": "#132018",
        "text": "#d9f5e6",
        "subtext": "#8ebfa6",
        "accent": "#34d399",
        "success": "#86efac",
        "field_bg": "#12261b",
    },
    "摩卡": {
        "bg": "#2b2a33",
        "panel": "#35343d",
        "text": "#f2e9de",
        "subtext": "#c8b8a9",
        "accent": "#d66f4f",
        "success": "#a3d9a5",
        "field_bg": "#3c3a45",
    },
}


class RoundedButton(tk.Canvas):
    def __init__(self, master, text: str, command=None, colors=None, radius=10, padx=14, pady=8, variant="primary", **kwargs):
        super().__init__(master, highlightthickness=0, bd=0, background=colors.get("panel") if colors else None, **kwargs)
        self._text = text
        self._command = command
        self._radius = radius
        self._padx = padx
        self._pady = pady
        self._state = "normal"
        self._colors = colors or {}
        self._variant = variant
        self._font = tkfont.nametofont("TkDefaultFont")
        self._font.configure(size=max(10, self._font.cget("size")))
        self._items = {}
        self._hover = False
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._redraw()

    # Public API
    def set_state(self, state: str):
        self._state = "disabled" if state.lower().startswith("dis") else "normal"
        self._redraw()

    def update_theme(self, colors: dict, variant: str | None = None):
        self._colors = colors
        if variant:
            self._variant = variant
        try:
            self.configure(background=self._colors.get("panel", self["background"]))
        except Exception:
            pass
        self._redraw()

    # Internal
    def _on_enter(self, _):
        self._hover = True
        self._redraw()

    def _on_leave(self, _):
        self._hover = False
        self._redraw()

    def _on_press(self, _):
        if self._state == "disabled":
            return
        self._pressed = True
        self._redraw()

    def _on_release(self, event):
        if getattr(self, "_pressed", False):
            self._pressed = False
            self._redraw()
            # Only trigger if release inside bounds
            x, y = event.x, event.y
            if 0 <= x <= int(self["width"]) and 0 <= y <= int(self["height"]):
                if callable(self._command) and self._state != "disabled":
                    self._command()

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        # Draw a rounded rectangle via arcs + rects
        r = max(0, min(r, (x2-x1)//2, (y2-y1)//2))
        items = []
        # center rectangles
        items.append(self.create_rectangle(x1+r, y1, x2-r, y2, outline="", **kwargs))
        items.append(self.create_rectangle(x1, y1+r, x2, y2-r, outline="", **kwargs))
        # corners
        items.append(self.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style=tk.PIESLICE, outline="", **kwargs))
        items.append(self.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style=tk.PIESLICE, outline="", **kwargs))
        items.append(self.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style=tk.PIESLICE, outline="", **kwargs))
        items.append(self.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style=tk.PIESLICE, outline="", **kwargs))
        return items

    def _current_colors(self):
        c = self._colors
        prefix = "button2" if self._variant == "secondary" else "button"
        if self._state == "disabled":
            return c.get(f"{prefix}_disabled", c.get("button_disabled", "#777777")), c.get(f"{prefix}_disabled_fg", c.get("button_disabled_fg", "#cccccc"))
        if getattr(self, "_pressed", False):
            return c.get(f"{prefix}_active", c.get("button_active", "#6666aa")), c.get(f"{prefix}_fg", c.get("button_fg", "#ffffff"))
        if self._hover:
            return c.get(f"{prefix}_hover", c.get("button_hover", "#8888cc")), c.get(f"{prefix}_fg", c.get("button_fg", "#ffffff"))
        return c.get(f"{prefix}_bg", c.get("button_bg", "#7777bb")), c.get(f"{prefix}_fg", c.get("button_fg", "#ffffff"))

    def _redraw(self):
        self.delete("all")
        text_w = self._font.measure(self._text)
        text_h = self._font.metrics("linespace")
        w = text_w + self._padx * 2
        h = text_h + self._pady * 2
        self.configure(width=w, height=h)
        bg, fg = self._current_colors()
        # background rect
        self._round_rect(1, 1, w-1, h-1, self._radius, fill=bg)
        # text
        self.create_text(w//2, h//2, text=self._text, fill=fg, font=self._font)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("网站图标下载器 (Google Favicon)")
        self.geometry("1040x680")
        self.minsize(900, 600)
        self._set_app_icon()

        self.url_var = tk.StringVar()
        self.out_dir_var = tk.StringVar(value=os.path.expanduser("~"))
        self.size_var = tk.StringVar(value="128")
        self.status_var = tk.StringVar(value="🟢 空闲")
        self.theme_var = tk.StringVar(value="浅色")
        self._rounded_buttons = []
        self._prefs_path = os.path.join(os.path.expanduser("~"), ".download_icon_prefs.json")

        # Load user preferences
        self._load_prefs_into_vars()

        # 初始主题
        self._apply_theme(THEMES[self.theme_var.get()])

        self._build_ui()
        # progress helpers
        self._progress_job = None
        self._progress_target = 0

        # Save prefs on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # Ensure message boxes are invoked on the Tk main thread (macOS safety)
    def show_info_async(self, title: str, message: str):
        self.after(0, lambda: messagebox.showinfo(title, message, parent=self))

    def show_error_async(self, title: str, message: str):
        self.after(0, lambda: messagebox.showerror(title, message, parent=self))

    def _apply_theme(self, theme: dict):
        bg = theme["bg"]
        panel = theme["panel"]
        text = theme["text"]
        subtext = theme["subtext"]
        accent = theme["accent"]
        success = theme["success"]
        field_bg = theme.get("field_bg", panel)

        self.configure(bg=bg)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Base styles
        style.configure("App.TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("TLabel", background=panel, foreground=text)
        style.configure("Header.TLabel", background=bg, foreground=text, font=("Helvetica", 18, "bold"))
        style.configure("SubHeader.TLabel", background=bg, foreground=subtext, font=("Helvetica", 11))
        style.configure("TEntry", fieldbackground=field_bg, foreground=text)
        # Soft, theme-aware button palette
        def _hex_to_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def _rgb_to_hex(rgb):
            return '#%02x%02x%02x' % rgb

        def _blend(a, b, t):
            ar, ag, ab = _hex_to_rgb(a)
            br, bg2, bb = _hex_to_rgb(b)
            r = int(ar + (br - ar) * t)
            g = int(ag + (bg2 - ag) * t)
            b2 = int(ab + (bb - ab) * t)
            return _rgb_to_hex((r, g, b2))

        def _luma(h):
            r, g, b2 = _hex_to_rgb(h)
            return 0.2126*r + 0.7152*g + 0.0722*b2

        button_bg = _blend(panel, accent, 0.28)
        button_hover = _blend(panel, accent, 0.38)
        button_active = _blend(panel, accent, 0.45)
        button_disabled = _blend(panel, text, 0.08)
        button_fg = "#0b1221" if _luma(button_bg) > 180 else text
        button_disabled_fg = _blend(text, panel, 0.5)

        # Secondary button palette（更弱对比）
        button2_bg = _blend(panel, accent, 0.16)
        button2_hover = _blend(panel, accent, 0.22)
        button2_active = _blend(panel, accent, 0.28)
        button2_disabled = _blend(panel, text, 0.06)
        button2_fg = "#0b1221" if _luma(button2_bg) > 180 else text
        button2_disabled_fg = _blend(text, panel, 0.55)

        style.configure("TButton", background=button_bg, foreground=button_fg)
        style.map("TButton",
                   background=[("active", button_active), ("!disabled", button_hover), ("disabled", button_disabled)],
                   foreground=[("disabled", button_disabled_fg)])
        style.configure("Primary.TButton", background=button_bg, foreground=button_fg, padding=6)
        style.configure("TCombobox", fieldbackground=field_bg, foreground=text, background=field_bg)
        style.map("TCombobox",
                   fieldbackground=[("readonly", field_bg)],
                   foreground=[("disabled", "#9aa4c3")])
        style.configure("Status.TLabel", background=bg, foreground=success)

        # Modern progressbar style (soft green bar)
        pb_style = "Green.Horizontal.TProgressbar"
        style.configure(pb_style,
                        troughcolor=field_bg,
                        background=success,
                        lightcolor=success,
                        darkcolor=success,
                        bordercolor=panel,
                        thickness=12)

        # Modern combobox and scrollbar styles
        style.configure("Modern.TCombobox", fieldbackground=field_bg, background=field_bg,
                        foreground=text, bordercolor=panel)
        style.map("Modern.TCombobox",
                  fieldbackground=[("readonly", field_bg)],
                  foreground=[("disabled", "#9aa4c3")])

        style.configure("Modern.Vertical.TScrollbar",
                        background=field_bg, troughcolor=panel, bordercolor=panel,
                        arrowcolor=subtext)
        style.map("Modern.Vertical.TScrollbar",
                  background=[("active", _blend(field_bg, accent, 0.15))])

        # Save for later (make available before any redraws)
        self._colors = {
            "bg": bg, "panel": panel, "text": text, "subtext": subtext,
            "accent": accent, "success": success, "field_bg": field_bg,
            "button_bg": button_bg, "button_hover": button_hover,
            "button_active": button_active, "button_disabled": button_disabled,
            "button_fg": button_fg, "button_disabled_fg": button_disabled_fg,
            "button2_bg": button2_bg, "button2_hover": button2_hover,
            "button2_active": button2_active, "button2_disabled": button2_disabled,
            "button2_fg": button2_fg, "button2_disabled_fg": button2_disabled_fg,
            "pb_style": pb_style,
            "card_border": _blend(field_bg, "#000000", 0.18),
        }

        # Update preview area to reflect new theme colors
        if hasattr(self, "preview_canvas"):
            try:
                self.preview_canvas.configure(bg=panel)
                self._redraw_preview()
                self.after(0, self._redraw_preview)
            except Exception:
                pass

        # 动态更新非 ttk 控件（如 Text）
        if hasattr(self, "log") and isinstance(self.log, tk.Text):
            try:
                self.log.configure(bg=bg, fg=text, insertbackground=text)
            except Exception:
                pass
        # 动态更新自定义圆角按钮
        # 更新所有自定义圆角按钮
        if hasattr(self, "_rounded_buttons"):
            for btn in self._rounded_buttons:
                try:
                    btn.update_theme(self._colors)
                except Exception:
                    pass
        # 图标现在采用缓存文件，不随主题实时重绘

    def _set_app_icon(self):
        # Prefer user-provided icon; otherwise use built-in cloud+arrow icon (fixed palette)
        candidates = [os.path.join("assets", "app_icon.png"), os.path.join("assets", "app_icon.gif")]
        img = None
        for p in candidates:
            if os.path.exists(p):
                try:
                    img = tk.PhotoImage(file=p)
                    break
                except Exception:
                    img = None
        if img is None:
            try:
                png_bytes = self._build_cloud_download_png()
                b64 = base64.b64encode(png_bytes).decode('ascii')
                img = tk.PhotoImage(data=b64)
            except Exception:
                img = None
        if img is not None:
            try:
                self.iconphoto(True, img)
                self._app_icon_img = img
            except Exception:
                pass

    def _build_cloud_download_png(self) -> bytes:
        # Build a 128x128 transparent PNG with a white rounded-square badge,
        # a slate cloud, and a blue download arrow.
        size = 128
        transparent = (0, 0, 0, 0)
        white = (255, 255, 255, 255)
        border = (229, 231, 235, 255)  # Tailwind gray-200
        cloud = (226, 232, 240, 255)   # slate-200 (softer)
        arrow = (63, 140, 255, 255)    # JetBrains-like blue

        px = [[transparent for _ in range(size)] for _ in range(size)]

        # Rounded square parameters
        pad = 12
        x1, y1, x2, y2 = pad, pad, size - pad, size - pad
        r = 22

        def inside_round_rect(x, y):
            if x1 + r <= x <= x2 - r and y1 <= y <= y2:
                return True
            if x1 <= x <= x2 and y1 + r <= y <= y2 - r:
                return True
            # corners
            dx, dy = x - (x1 + r), y - (y1 + r)
            if dx*dx + dy*dy <= r*r:
                return True
            dx, dy = x - (x2 - r), y - (y1 + r)
            if dx*dx + dy*dy <= r*r:
                return True
            dx, dy = x - (x1 + r), y - (y2 - r)
            if dx*dx + dy*dy <= r*r:
                return True
            dx, dy = x - (x2 - r), y - (y2 - r)
            if dx*dx + dy*dy <= r*r:
                return True
            return False

        # Fill badge
        for y in range(size):
            for x in range(size):
                if inside_round_rect(x, y):
                    px[y][x] = white

        # 1px border
        for y in range(size):
            for x in range(size):
                inside = inside_round_rect(x, y)
                if inside:
                    for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                        if 0 <= nx < size and 0 <= ny < size and not inside_round_rect(nx, ny):
                            px[y][x] = border
                            break

        # Cloud shape (union of circles; more rounded)
        cx, cy = size//2, size//2 + 6
        # Make cloud slimmer horizontally (closer centers, smaller radii)
        c1 = (cx - 20, cy - 6, 20)
        c2 = (cx, cy - 14, 26)
        c3 = (cx + 20, cy - 6, 20)
        c4 = (cx, cy + 2, 18)

        def inside_circle(x, y, cx0, cy0, rr):
            dx, dy = x - cx0, y - cy0
            return dx*dx + dy*dy <= rr*rr

        def inside_cloud(x, y):
            return (inside_circle(x,y,*c1) or inside_circle(x,y,*c2) or
                    inside_circle(x,y,*c3) or inside_circle(x,y,*c4))

        for y in range(size):
            for x in range(size):
                if inside_cloud(x, y):
                    px[y][x] = cloud

        # Arrow (shaft + head), centered, over the cloud
        shaft_w = 16  # thicker shaft
        base_y = cy + 6
        # Shaft ends at base_y (just above arrow head base)
        for y in range(cy - 24, base_y):
            for x in range(cx - shaft_w//2, cx + shaft_w//2 + 1):
                px[y][x] = arrow
        # Arrow head triangle (pointing down): base near shaft, apex at bottom
        head_h = 18
        base_half = max(shaft_w//2 + 4, 12)
        for t in range(head_h):
            y = base_y + t
            half = max(base_half - t, 0)
            for x in range(cx - half, cx + half + 1):
                if 0 <= x < size and 0 <= y < size:
                    px[y][x] = arrow

        # Tray line under arrow (thicker, slightly lower)
        tray_y = base_y + head_h + 4
        for x in range(cx - 30, cx + 30):
            for dy in (-1, 0, 1):  # 3px thick
                y = tray_y + dy
                if 0 <= y < size:
                    px[y][x] = arrow

        # Encode to PNG
        raw = bytearray()
        for y in range(size):
            raw.append(0)
            for x in range(size):
                r8, g8, b8, a8 = px[y][x]
                raw.extend((r8, g8, b8, a8))

        def png_chunk(typ: bytes, data: bytes) -> bytes:
            return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)

        sig = b'\x89PNG\r\n\x1a\n'
        ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
        idat = zlib.compress(bytes(raw), 9)
        png_bytes = sig + png_chunk(b'IHDR', ihdr) + png_chunk(b'IDAT', idat) + png_chunk(b'IEND', b'')
        return png_bytes

    def _make_generated_icon(self, accent_hex: str):
        # Deprecated in new flow; kept for fallback compatibility
        try:
            png_bytes = self._build_abstract_download_png(accent_hex)
            b64 = base64.b64encode(png_bytes).decode('ascii')
            return tk.PhotoImage(data=b64)
        except Exception:
            return None

    def _build_abstract_download_png(self, accent_hex: str) -> bytes:
        # Build a 128x128 transparent PNG with abstract download motif (ring + arrow + tray)
        size = 128

        def hex_to_rgba(h, a=255):
            h = h.lstrip('#')
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return (r, g, b, a)

        transparent = (0, 0, 0, 0)
        stroke = hex_to_rgba(accent_hex, 255)
        accent = stroke

        px = [[transparent for _ in range(size)] for _ in range(size)]

        cx, cy = size // 2, size // 2

        def set_pixel(x, y, color):
            if 0 <= x < size and 0 <= y < size:
                px[y][x] = color

        def draw_line(x1, y1, x2, y2, color):
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            x, y = x1, y1
            sx = 1 if x1 < x2 else -1
            sy = 1 if y1 < y2 else -1
            if dx > dy:
                err = dx // 2
                while x != x2:
                    set_pixel(x, y, color)
                    err -= dy
                    if err < 0:
                        y += sy
                        err += dx
                    x += sx
                set_pixel(x2, y2, color)
            else:
                err = dy // 2
                while y != y2:
                    set_pixel(x, y, color)
                    err -= dx
                    if err < 0:
                        x += sx
                        err += dy
                    y += sy
                set_pixel(x2, y2, color)

        def draw_circle_outline(cx0, cy0, r, color, thickness=2):
            r2 = r * r
            r1_2 = (r - thickness) * (r - thickness)
            for y in range(cy0 - r - 1, cy0 + r + 2):
                for x in range(cx0 - r - 1, cx0 + r + 2):
                    d2 = (x - cx0) * (x - cx0) + (y - cy0) * (y - cy0)
                    if r1_2 <= d2 <= r2:
                        set_pixel(x, y, color)

        def draw_line_thick(x1, y1, x2, y2, color, thickness=3):
            for off in range(-thickness//2, thickness//2 + 1):
                if abs(x2 - x1) >= abs(y2 - y1):
                    draw_line(x1, y1 + off, x2, y2 + off, color)
                else:
                    draw_line(x1 + off, y1, x2 + off, y2, color)

        # Abstract motif: outer ring
        draw_circle_outline(cx, cy, 40, stroke, thickness=4)
        # Arrow shaft
        draw_line_thick(cx, cy - 18, cx, cy + 10, accent, thickness=4)
        # Arrow head
        draw_line_thick(cx - 8, cy + 2, cx, cy + 12, accent, thickness=4)
        draw_line_thick(cx + 8, cy + 2, cx, cy + 12, accent, thickness=4)
        # Tray line
        draw_line_thick(cx - 16, cy + 18, cx + 16, cy + 18, accent, thickness=4)

        # Encode to PNG RGBA
        raw = bytearray()
        for y in range(size):
            raw.append(0)
            for x in range(size):
                r, g, b, a = px[y][x]
                raw.extend((r, g, b, a))

        def png_chunk(typ: bytes, data: bytes) -> bytes:
            return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)

        sig = b'\x89PNG\r\n\x1a\n'
        ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
        idat = zlib.compress(bytes(raw), 9)
        png_bytes = sig + png_chunk(b'IHDR', ihdr) + png_chunk(b'IDAT', idat) + png_chunk(b'IEND', b'')
        return png_bytes

    def _build_ui(self):
        pad = 12
        root_frame = ttk.Frame(self, style="App.TFrame")
        root_frame.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)

        # Header
        header = ttk.Frame(root_frame, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=4, sticky="we")
        ttk.Label(header, text="🧩 网站图标下载器", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="基于 Google Favicon 服务 · 选择尺寸一键下载", style="SubHeader.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 8))
        header.columnconfigure(1, weight=1)
        # 主题选择控件（右上角）
        ttk.Label(header, text="主题:", style="SubHeader.TLabel").grid(row=0, column=2, sticky="e", padx=(8, 4))
        self.theme_combo = ttk.Combobox(header, textvariable=self.theme_var, values=list(THEMES.keys()), state="readonly", width=8, style="Modern.TCombobox")
        self.theme_combo.grid(row=0, column=3, sticky="e")
        self.theme_combo.bind("<<ComboboxSelected>>", self.on_theme_change)

        # Panel
        panel = ttk.Frame(root_frame, padding=14, style="Panel.TFrame")
        panel.grid(row=1, column=0, columnspan=4, sticky="nsew")

        # URL input
        ttk.Label(panel, text="网站地址 URL:").grid(row=0, column=0, sticky="w")
        url_entry = ttk.Entry(panel, textvariable=self.url_var)
        url_entry.grid(row=1, column=0, columnspan=3, sticky="we", pady=(2, pad))
        url_entry.focus_set()
        url_entry.bind("<Return>", lambda e: self.on_download())
        self.url_entry = url_entry

        # Output dir
        ttk.Label(panel, text="输出目录:").grid(row=2, column=0, sticky="w")
        out_entry = ttk.Entry(panel, textvariable=self.out_dir_var)
        out_entry.grid(row=3, column=0, columnspan=2, sticky="we")
        self.choose_btn = RoundedButton(panel, text="选择…", command=self.choose_out_dir, colors=self._colors, variant="secondary", radius=10, padx=12, pady=6)
        self.choose_btn.grid(row=3, column=2, sticky="e", padx=(6, 0))
        self._rounded_buttons.append(self.choose_btn)

        # Size selection
        ttk.Label(panel, text="图标尺寸:").grid(row=4, column=0, sticky="w", pady=(pad, 0))
        size_choices = ["16", "32", "48", "64", "96", "128", "192", "256", "512"]
        self.size_combo = ttk.Combobox(panel, textvariable=self.size_var, values=size_choices, state="readonly", width=8, style="Modern.TCombobox")
        self.size_combo.grid(row=4, column=1, sticky="w", pady=(pad, 0))
        self.size_combo.bind("<<ComboboxSelected>>", self.on_size_change)

        # Actions and spinner
        btn_frame = ttk.Frame(panel, style="Panel.TFrame")
        btn_frame.grid(row=5, column=0, columnspan=3, sticky="we", pady=(pad, pad))
        self.start_btn = RoundedButton(btn_frame, text="▶ 开始下载", command=self.on_download, colors=self._colors, variant="primary")
        self.start_btn.pack(side=tk.LEFT, pady=2)
        self._rounded_buttons.append(self.start_btn)

        self.progress = ttk.Progressbar(btn_frame, mode="determinate", style=self._colors.get("pb_style", "Horizontal.TProgressbar"))
        self.progress.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.percent_var = tk.StringVar(value="0%")
        self.percent_lbl = ttk.Label(btn_frame, textvariable=self.percent_var, style="SubHeader.TLabel")
        self.percent_lbl.pack(side=tk.LEFT, padx=(8, 0))

        # Removed completion popup option per preference

        # Log + preview area
        ttk.Label(panel, text="🧾 日志:").grid(row=6, column=0, sticky="w")
        self.log = tk.Text(panel, height=10, bg=self._colors["bg"], fg=self._colors["text"],
                           insertbackground=self._colors["text"], highlightthickness=0, bd=0)
        self.log.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(2, 0))
        self.scroll = ttk.Scrollbar(panel, command=self.log.yview, style="Modern.Vertical.TScrollbar")
        self.scroll.grid(row=7, column=2, sticky="ns")
        self.log.configure(yscrollcommand=self.scroll.set)

        # Right side: icon preview (larger square with padding)
        self._preview_size = 280
        self.preview_wrap = ttk.Frame(panel, padding=10, style="Panel.TFrame")
        self.preview_wrap.grid(row=7, column=3, sticky="nsew", padx=(24, 12), pady=(8, 8))
        self.preview_canvas = tk.Canvas(self.preview_wrap, width=self._preview_size, height=self._preview_size,
                                        highlightthickness=0, bd=0, bg=self._colors["panel"])
        self.preview_canvas.pack(expand=True)
        self._preview_image = None  # keep reference
        self._preview_path = None
        self.preview_wrap.bind("<Configure>", self._on_preview_container_configure)
        self._draw_preview_placeholder()

        # Status bar
        status = ttk.Label(root_frame, textvariable=self.status_var, style="Status.TLabel")
        status.grid(row=99, column=0, columnspan=4, sticky="we", pady=(8, 0))

        # Configure grid weights
        root_frame.columnconfigure(0, weight=1)
        root_frame.columnconfigure(1, weight=0)
        root_frame.columnconfigure(2, weight=0)
        root_frame.columnconfigure(3, weight=1)
        root_frame.rowconfigure(1, weight=1)

        panel.columnconfigure(0, weight=3)
        panel.columnconfigure(1, weight=1)
        panel.columnconfigure(2, weight=0)
        panel.columnconfigure(3, weight=2)
        panel.rowconfigure(7, weight=1)

    def on_theme_change(self, *_):
        name = self.theme_var.get()
        theme = THEMES.get(name, THEMES["深色"])
        self._apply_theme(theme)
        self._save_prefs()
        # Move focus away so combobox doesn't appear selected
        try:
            self.theme_combo.selection_clear()
        except Exception:
            pass
        try:
            self.url_entry.focus_set()
        except Exception:
            pass

    def on_size_change(self, *_):
        self._save_prefs()

    def choose_out_dir(self):
        path = filedialog.askdirectory(initialdir=self.out_dir_var.get() or os.getcwd())
        if path:
            self.out_dir_var.set(path)
            self._save_prefs()

    def append_log(self, text: str):
        def _do():
            self.log.insert(tk.END, text + "\n")
            self.log.see(tk.END)
        self.log.after(0, _do)

    def on_download(self):
        url = (self.url_var.get() or "").strip()
        out_dir = (self.out_dir_var.get() or "").strip()
        try:
            size = int(self.size_var.get() or 128)
        except Exception:
            size = 128

        if not url:
            messagebox.showwarning("提示", "请输入网站地址 URL")
            return
        if not out_dir:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        self.append_log(f"🚀 获取图标: {url}")
        self.append_log(f"📁 保存目录: {out_dir}")
        self.append_log(f"🔧 尺寸: {size}x{size}")

        # UI: set busy
        self._set_busy(True)

        def worker():
            try:
                path = download_icon_from_google(url, save_dir=out_dir, size=size)
                if path:
                    self.append_log("✅ 下载完成")
                    self.append_log(f"📥 保存路径: {path}")
                    self._update_preview_async(path)
                    success = True
                    result = path
                else:
                    self.append_log("❌ 未获取到图标 (服务可能未返回图像)")
                    success = False
                    result = None
            except Exception as e:
                self.append_log(f"💥 下载失败: {e}")
                success = False
                result = None
            finally:
                # complete progress then finish UI and optional notify
                self.after(0, lambda: self._finish_ui_post_download())

        threading.Thread(target=worker, daemon=True).start()

    def _set_busy(self, busy: bool):
        def _apply():
            if busy:
                self.status_var.set("🟡 下载中…")
                self._progress_start()
                try:
                    self.start_btn.set_state("disabled")
                except Exception:
                    pass
                try:
                    self.choose_btn.set_state("disabled")
                except Exception:
                    pass
                try:
                    self.size_combo.configure(state="disabled")
                except Exception:
                    pass
                try:
                    self.theme_combo.configure(state="disabled")
                except Exception:
                    pass
            else:
                self.status_var.set("🟢 空闲")
                self._progress_reset()
                try:
                    self.start_btn.set_state("normal")
                except Exception:
                    pass
                try:
                    self.choose_btn.set_state("normal")
                except Exception:
                    pass
                try:
                    self.size_combo.configure(state="readonly")
                except Exception:
                    pass
                try:
                    self.theme_combo.configure(state="readonly")
                except Exception:
                    pass
        self.after(0, _apply)

    # Progress handling
    def _progress_start(self):
        try:
            self.progress.configure(value=0, maximum=100)
        except Exception:
            pass
        self.percent_var.set("0%")
        self._progress_target = 90
        if self._progress_job:
            try:
                self.after_cancel(self._progress_job)
            except Exception:
                pass
        self._progress_job = self.after(100, self._tick_progress)

    def _tick_progress(self):
        try:
            val = float(self.progress.cget("value"))
        except Exception:
            val = 0.0
        step = 2.5
        target = float(self._progress_target)
        if val < target:
            val = min(val + step, target)
            try:
                self.progress.configure(value=val)
            except Exception:
                pass
            self.percent_var.set(f"{int(val)}%")
            self._progress_job = self.after(120, self._tick_progress)
        else:
            self._progress_job = None

    def _progress_complete(self):
        try:
            self.progress.configure(value=100)
        except Exception:
            pass
        self.percent_var.set("100%")

    def _progress_reset(self):
        if self._progress_job:
            try:
                self.after_cancel(self._progress_job)
            except Exception:
                pass
            self._progress_job = None
        try:
            self.progress.configure(value=0)
        except Exception:
            pass
        self.percent_var.set("0%")

    def _finish_ui_post_download(self):
        # Ensure bar hits 100% then re-enable UI after a short delay; no popup
        self._progress_complete()
        self.after(420, lambda: self._set_busy(False))

    def _update_preview_async(self, path: str):
        # Show preview for PNG/GIF in the square canvas; center and fit
        def _apply():
            try:
                ext = os.path.splitext(path)[1].lower()
                if ext in (".png", ".gif"):
                    self._preview_path = path
                    self._redraw_preview()
                else:
                    self._preview_path = None
                    self._preview_image = None
                    self._draw_preview_placeholder("(图像预览不支持该格式)")
            except Exception:
                self._preview_path = None
                self._preview_image = None
                self._draw_preview_placeholder("(无法预览)")
        self.after(0, _apply)

    # Preferences
    def _load_prefs_into_vars(self):
        try:
            with open(self._prefs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        theme = data.get("theme")
        out_dir = data.get("out_dir")
        size = data.get("size")
        if isinstance(theme, str) and theme in THEMES:
            self.theme_var.set(theme)
        if isinstance(out_dir, str) and out_dir.strip():
            self.out_dir_var.set(out_dir)
        if isinstance(size, (str, int)):
            try:
                self.size_var.set(str(int(size)))
            except Exception:
                pass

    def _save_prefs(self):
        data = {
            "theme": self.theme_var.get(),
            "out_dir": self.out_dir_var.get(),
            "size": self.size_var.get(),
        }
        try:
            with open(self._prefs_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self):
        try:
            self._save_prefs()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _draw_preview_card(self):
        # Draw subtle rounded square background on canvas
        c = self.preview_canvas
        c.delete("card")
        s = min(max(c.winfo_width(), 40), max(c.winfo_height(), 40))
        pad = 6
        r = 16
        bg = self._colors.get("field_bg", self._colors.get("panel"))
        border = self._colors.get("card_border", bg)
        # Simple rounded rect approximation
        c.create_rectangle(pad+r, pad, s-pad-r, s-pad, fill=bg, outline=border, width=1, tags="card")
        c.create_rectangle(pad, pad+r, s-pad, s-pad-r, fill=bg, outline=border, width=1, tags="card")
        c.create_oval(pad, pad, pad+2*r, pad+2*r, fill=bg, outline=border, width=1, tags="card")
        c.create_oval(s-pad-2*r, pad, s-pad, pad+2*r, fill=bg, outline=border, width=1, tags="card")
        c.create_oval(pad, s-pad-2*r, pad+2*r, s-pad, fill=bg, outline=border, width=1, tags="card")
        c.create_oval(s-pad-2*r, s-pad-2*r, s-pad, s-pad, fill=bg, outline=border, width=1, tags="card")

    def _draw_preview_placeholder(self, text="(预览区)"):
        c = self.preview_canvas
        c.delete("all")
        self._draw_preview_card()
        cx = max(c.winfo_width(), 1) // 2
        cy = max(c.winfo_height(), 1) // 2
        c.create_text(cx, cy, text=text, fill=self._colors.get("subtext", "#888"))

    def _on_preview_container_configure(self, event):
        size = max(140, min(event.width - 20, event.height - 20))
        self._preview_size = size
        try:
            self.preview_canvas.configure(width=size, height=size)
        except Exception:
            pass
        self._redraw_preview()

    def _redraw_preview(self):
        self.preview_canvas.delete("all")
        self._draw_preview_card()
        if self._preview_path and os.path.exists(self._preview_path):
            try:
                img = tk.PhotoImage(file=self._preview_path)
                w, h = img.width(), img.height()
                max_side = max(1, min(self.preview_canvas.winfo_width(), self.preview_canvas.winfo_height()) - 16)
                subs = max(1, (max(w, h) + max_side - 1) // max_side)
                if subs > 1:
                    try:
                        img = img.subsample(subs, subs)
                        w, h = img.width(), img.height()
                    except Exception:
                        pass
                self._preview_image = img
                x = max(0, (self.preview_canvas.winfo_width() - w) // 2)
                y = max(0, (self.preview_canvas.winfo_height() - h) // 2)
                self.preview_canvas.create_image(x, y, anchor="nw", image=img)
                return
            except Exception:
                pass
        # else draw placeholder
        self._draw_preview_placeholder()


if __name__ == "__main__":
    app = App()
    app.mainloop()
