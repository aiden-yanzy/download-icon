Download Website Icons via Google Favicon (Python + Tkinter)

一个使用 Google Favicon 服务下载网站图标的轻量工具。输入网站域名或 URL，选择图标尺寸，即可一键下载 favicon（支持 png/svg/ico 等）。

What this tool does

- Uses Google’s favicon endpoint to fetch icons reliably
- Accepts a domain or full URL (e.g., github.com or https://github.com)
- Lets you choose a size (16, 32, 64, 128, …)
- Saves the icon to a chosen output directory (default to your home directory)
- Offers multiple UI themes (dark, light, etc.)

Why Google Favicon service

- Stable and simple: no need to parse HTML or manifests
- Good fallback behavior for most sites
- Supports multiple sizes via a single API

Quick Start

Option A — One-click (macOS/Linux)
- `bash scripts/setup_and_run.sh`

Option B — Manual steps
- Create venv (Python 3.12 recommended): `python3 -m venv .venv`
- Activate: `source .venv/bin/activate`
- Upgrade pip: `python -m pip install -U pip`
- Install deps: `pip install -r requirements.txt`
- Run the GUI: `python3 download_icon_gui.py`

Usage (GUI)

- Enter a domain or URL, e.g. `github.com` or `https://linux.do`
- Pick a size (16/32/48/64/96/128/192/256/512)
- Choose output directory (defaults to your home directory)
- Click “开始下载” to fetch and save the icon
- Switch theme from the top-right theme selector
  - The app remembers your last selected theme and output directory in `~/.download_icon_prefs.json`
  - If no custom icon is provided, the app generates an abstract download-themed icon once and caches it

Custom App Icon

- Place a PNG or GIF at `assets/app_icon.png` (or `assets/app_icon.gif`). The app will load it as the window icon.
- Recommended: 64×64 or 128×128 PNG with transparent background for best scaling.
- If not provided, the app uses a built‑in cloud + download arrow icon (rounded white badge, fixed colors). Place a file to override.

Programmatic Use

- From `dd2.py`:
  - `from dd2 import download_icon_from_google`
  - `download_icon_from_google("github.com", save_dir="icons", size=128)`

How it works

- Calls `https://t0.gstatic.com/faviconV2` with parameters:
  - `client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=<your-url>&size=<N>`
- Determines file extension from `Content-Type` and saves as
  `"<domain>_<size>x<size>.<ext>"` under the output directory

Notes & Limitations

- Google may return different formats (PNG/SVG/ICO/JPEG) based on availability
- Some domains may not have an icon; request may return non-image or fail
- Network and certificate behavior depend on your Python/OpenSSL setup

License

MIT (see repository terms)
