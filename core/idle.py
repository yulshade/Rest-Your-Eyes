"""Windows idle-time detection via the Win32 GetLastInputInfo API.

Returns the number of seconds since the last keyboard or mouse input. Used by
the screentime tracker to decide whether the current second counts as "active"
or "idle". Falls back to 0.0 on non-Windows platforms (always reports active).
"""
from __future__ import annotations

import ctypes
import sys


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    """Seconds since the last user input (keyboard/mouse). 0.0 if unavailable."""
    if sys.platform != "win32":
        return 0.0

    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0

    # GetTickCount and dwTime are 32-bit millisecond counters that wrap roughly
    # every 49.7 days. Masking keeps the subtraction correct across a wrap.
    now = ctypes.windll.kernel32.GetTickCount()
    elapsed_ms = (now - info.dwTime) & 0xFFFFFFFF
    return elapsed_ms / 1000.0
