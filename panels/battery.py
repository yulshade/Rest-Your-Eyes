"""Battery panel: percentage, charging state, and time remaining."""
from __future__ import annotations

import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

REFRESH_MS = 5_000
# Windows derives secsleft from the *instantaneous* power draw, so it jumps
# around as CPU/GPU load changes. Smooth it with an exponential moving average.
EMA_ALPHA = 0.1          # lower = smoother/slower to react
ROUND_TO_MIN = 5         # round the displayed estimate to this many minutes


def _fmt_time(secs: float) -> str:
    minutes_total = int(round(secs / 60.0 / ROUND_TO_MIN)) * ROUND_TO_MIN
    hours, minutes = divmod(minutes_total, 60)
    if hours:
        return f"~{hours}h {minutes:02d}m remaining"
    return f"~{minutes}m remaining"


class BatteryPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self._title = QLabel("Battery")
        self._title.setObjectName("panelTitle")

        self._percent = QLabel("--%")
        self._percent.setObjectName("bigValue")

        self._bar = QProgressBar()
        self._bar.setObjectName("batteryBar")
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)

        self._status = QLabel("")
        self._status.setObjectName("subValue")

        # Smoothing state for the time-remaining estimate.
        self._smoothed_secs: float | None = None
        self._was_plugged: bool | None = None

        layout.addWidget(self._title)
        layout.addWidget(self._percent)
        layout.addWidget(self._bar)
        layout.addWidget(self._status)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(REFRESH_MS)
        self.refresh()

    def refresh(self) -> None:
        batt = psutil.sensors_battery()
        if batt is None:
            self._percent.setText("N/A")
            self._bar.setValue(0)
            self._status.setText("No battery detected")
            self._set_bar_color("#7a8290")
            return

        pct = int(round(batt.percent))
        self._percent.setText(f"{pct}%")
        self._bar.setValue(pct)

        # Reset the smoother whenever the power source changes, so we never
        # blend a charging estimate into a discharging one (or vice versa).
        if batt.power_plugged != self._was_plugged:
            self._smoothed_secs = None
            self._was_plugged = batt.power_plugged

        if batt.power_plugged:
            self._status.setText("⚡ Fully charged" if pct >= 100 else "⚡ Charging")
        elif batt.secsleft in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN):
            self._status.setText("On battery")
        else:
            self._status.setText(_fmt_time(self._smooth(batt.secsleft)))

        self._set_bar_color(self._color_for(pct, batt.power_plugged))

    def _smooth(self, secs: float) -> float:
        """Exponential moving average to tame Windows' noisy estimate."""
        if self._smoothed_secs is None:
            self._smoothed_secs = float(secs)
        else:
            self._smoothed_secs = (
                EMA_ALPHA * secs + (1 - EMA_ALPHA) * self._smoothed_secs
            )
        return self._smoothed_secs

    @staticmethod
    def _color_for(pct: int, plugged: bool) -> str:
        if plugged:
            return "#4ec46a"
        if pct >= 50:
            return "#4ec46a"
        if pct >= 20:
            return "#e0a32e"
        return "#e0533d"

    def _set_bar_color(self, color: str) -> None:
        self._bar.setStyleSheet(
            "QProgressBar#batteryBar{background:rgba(255,255,255,0.10);"
            "border:none;border-radius:4px;}"
            f"QProgressBar#batteryBar::chunk{{background:{color};border-radius:4px;}}"
        )
