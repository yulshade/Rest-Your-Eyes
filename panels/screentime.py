"""Screentime panel: tracks and displays active vs idle time for today.

ActivityTracker ticks once a second, attributing the elapsed wall-clock delta to
either "active" or "idle" based on the Win32 idle timer, and persists daily
totals to disk. ScreenTimePanel renders today's figures.
"""
from __future__ import annotations

import time
from datetime import date

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from core import storage
from core.idle import get_idle_seconds

IDLE_THRESHOLD_S = 60       # idle >= this many seconds => time counts as idle
SAVE_INTERVAL_S = 30        # flush to disk at most this often
MAX_DELTA_S = 5             # cap per-tick delta to absorb sleep/resume gaps


def _fmt_hm(secs: float) -> str:
    total = int(secs)
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


class ActivityTracker(QObject):
    """Accumulates active/idle seconds per calendar day and persists them."""

    updated = Signal(float, float)  # active_seconds, idle_seconds (today)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._history = storage.load_screentime()
        self._last_tick = time.monotonic()
        self._last_save = time.monotonic()
        self._continuous_active = 0.0  # for optional eye-break logic

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._emit()

    def _today(self) -> dict[str, float]:
        key = date.today().isoformat()
        return self._history.setdefault(key, {"active": 0.0, "idle": 0.0})

    def _tick(self) -> None:
        now = time.monotonic()
        delta = min(now - self._last_tick, MAX_DELTA_S)
        self._last_tick = now

        today = self._today()
        if get_idle_seconds() >= IDLE_THRESHOLD_S:
            today["idle"] += delta
            self._continuous_active = 0.0
        else:
            today["active"] += delta
            self._continuous_active += delta

        if now - self._last_save >= SAVE_INTERVAL_S:
            self.flush()
            self._last_save = now

        self._emit()

    def _emit(self) -> None:
        today = self._today()
        self.updated.emit(today["active"], today["idle"])

    @property
    def continuous_active_seconds(self) -> float:
        return self._continuous_active

    def flush(self) -> None:
        storage.save_screentime(self._history)


class ScreenTimePanel(QWidget):
    def __init__(self, tracker: ActivityTracker, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title = QLabel("Screentime today")
        title.setObjectName("panelTitle")

        row = QHBoxLayout()
        row.setSpacing(12)
        self._active = QLabel("Active 0m")
        self._active.setObjectName("activeValue")
        self._idle = QLabel("Idle 0m")
        self._idle.setObjectName("idleValue")
        self._idle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self._active)
        row.addWidget(self._idle)

        self._bar = QProgressBar()
        self._bar.setObjectName("ratioBar")
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)

        layout.addWidget(title)
        layout.addLayout(row)
        layout.addWidget(self._bar)

        tracker.updated.connect(self._on_update)

    def _on_update(self, active: float, idle: float) -> None:
        self._active.setText(f"Active  {_fmt_hm(active)}")
        self._idle.setText(f"Idle  {_fmt_hm(idle)}")
        total = active + idle
        self._bar.setValue(int(round(100 * active / total)) if total else 0)
