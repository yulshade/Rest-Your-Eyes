# Rest Your Eyes

A small **Windows desktop widget** that pins itself to your wallpaper and shows:

- 🔋 **Battery** — percentage, charging state, and estimated time remaining
- ⏱️ **Screentime** — today's *active* vs *idle* time, persisted across restarts
- 📅 **Interactive calendar** — click dates, page through months

Built with Python + PySide6 (Qt6). The widget is frameless and translucent, sits
**below** your normal windows (never covering your work), and is managed from a
**system-tray icon** (left-click to show/hide; right-click for Lock position / Quit).

## Setup

```powershell
py -m pip install -r requirements.txt
```

## Run

```powershell
py main.py
```

To launch **without a console window** (e.g. for everyday use), double-click
`run.pyw`, or:

```powershell
pythonw run.pyw
```

## Usage

- **Move it:** drag the widget with the left mouse button (anywhere except the
  calendar). Its position is remembered.
- **Tray icon:** left-click toggles show/hide. Right-click for:
  - **Lock position** — prevents accidental dragging
  - **Reload** — restarts the app to pick up edits to code or `style.qss`
  - **Quit** — exits and flushes screentime to disk
- **Idle threshold:** time counts as *idle* after 60 s without keyboard/mouse
  input (change `IDLE_THRESHOLD_S` in `panels/screentime.py`).

## Where data is stored

`%APPDATA%\RestYourEyes\`
- `screentime.json` — daily `{active, idle}` seconds, keyed by date
- `config.json` — window position and lock state

## Start automatically at login (optional)

Create a shortcut to `run.pyw` (launched with `pythonw.exe`) and drop it in your
Startup folder:

```powershell
explorer shell:startup
```

## Project layout

```
main.py              window assembly, tray icon, theme loading
run.pyw              console-less launcher
panels/
  battery.py         battery percentage / time-remaining
  screentime.py      ActivityTracker + active/idle display
  calendar.py        interactive QCalendarWidget
core/
  idle.py            Win32 GetLastInputInfo idle detection
  storage.py         atomic JSON persistence in %APPDATA%
  pinning.py         desktop window flags + drag-to-move
assets/style.qss     dark translucent theme
```
