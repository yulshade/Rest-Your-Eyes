"""Rest Your Eyes — a pinned Windows desktop widget.

Shows battery life, today's active/idle screentime, and an interactive calendar
in a frameless translucent card that sits on the desktop. Managed from a system
tray icon (Show/Hide, Lock position, Quit).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMenu,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from core import storage
from core.pinning import DragMixin, apply_desktop_flags
from panels.battery import BatteryPanel
from panels.calendar import CalendarPanel
from panels.screentime import ActivityTracker, ScreenTimePanel

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SIZE = (300, 470)


def _separator() -> QFrame:
    line = QFrame()
    line.setObjectName("separator")
    line.setFrameShape(QFrame.HLine)
    return line


def _make_icon() -> QIcon:
    """Draw a simple eye glyph so the app needs no bundled image file."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#161a22"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 2, 60, 60)
    p.setBrush(QColor("#5cc8ff"))
    p.drawEllipse(16, 22, 32, 20)   # eye outline area
    p.setBrush(QColor("#0d1017"))
    p.drawEllipse(26, 26, 12, 12)   # pupil
    p.end()
    return QIcon(pix)


class RestYourEyes(DragMixin, QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("root")
        apply_desktop_flags(self)
        self._config = storage.load_config()
        self._init_drag(self._save_position)
        self.set_locked(bool(self._config.get("locked", False)))

        # Outer transparent root holds the visible "card" frame.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(4, 10, 4, 8)
        layout.setSpacing(2)

        self._tracker = ActivityTracker(self)

        self._calendar = CalendarPanel()
        layout.addWidget(BatteryPanel())
        layout.addWidget(_separator())
        layout.addWidget(ScreenTimePanel(self._tracker))
        layout.addWidget(_separator())
        layout.addWidget(self._calendar)

        # Pin the width so variable content (long month names like "December",
        # battery time strings) can never resize the card horizontally.
        self.setFixedWidth(DEFAULT_SIZE[0])
        self.resize(DEFAULT_SIZE[0], DEFAULT_SIZE[1])
        self._restore_position()
        # Drag from anywhere except the calendar (whose clicks select dates).
        self.enable_drag(exclude=[self._calendar])

        self._build_tray()

    # ---- position persistence ----
    def _restore_position(self) -> None:
        x, y = self._config.get("x"), self._config.get("y")
        if x is not None and y is not None:
            self.move(int(x), int(y))
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(screen.right() - self.width() - 24, screen.top() + 24)

    def _save_position(self, x: int, y: int) -> None:
        self._config["x"] = x
        self._config["y"] = y
        storage.save_config(self._config)

    # ---- system tray ----
    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(_make_icon(), self)
        self._tray.setToolTip("Rest Your Eyes")
        menu = QMenu()

        toggle = QAction("Hide widget", self)
        toggle.triggered.connect(self._toggle_visible)
        menu.addAction(toggle)
        self._toggle_action = toggle

        lock = QAction("Lock position", self)
        lock.setCheckable(True)
        lock.setChecked(self._locked)
        lock.toggled.connect(self._toggle_lock)
        menu.addAction(lock)

        menu.addSeparator()
        reload_action = QAction("Reload", self)
        reload_action.setToolTip("Restart to apply edits to code or styles")
        reload_action.triggered.connect(self._reload)
        menu.addAction(reload_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:  # left click
            self._toggle_visible()

    def _toggle_visible(self) -> None:
        if self.isVisible():
            self.hide()
            self._toggle_action.setText("Show widget")
        else:
            self.show()
            self.lower()
            self._toggle_action.setText("Hide widget")

    def _toggle_lock(self, locked: bool) -> None:
        self.set_locked(locked)
        self._config["locked"] = locked
        storage.save_config(self._config)

    def _reload(self) -> None:
        """Relaunch the app so edits to code or style.qss take effect."""
        self.flush()
        self._tray.hide()  # avoid a lingering duplicate tray icon
        script = str(Path(sys.argv[0]).resolve())
        QProcess.startDetached(sys.executable, [script], str(BASE_DIR))
        QApplication.quit()

    def flush(self) -> None:
        self._tracker.flush()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # tray keeps app alive when hidden

    qss = (BASE_DIR / "assets" / "style.qss").read_text(encoding="utf-8")
    app.setStyleSheet(qss)

    widget = RestYourEyes()
    widget.show()
    widget.lower()
    app.aboutToQuit.connect(widget.flush)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
