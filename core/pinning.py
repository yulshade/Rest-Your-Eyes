"""Helpers to make a QWidget behave as a desktop-pinned widget.

The window is frameless, translucent, kept on the bottom z-layer (so it sits on
the wallpaper but never covers your work), has no taskbar button, and does not
steal keyboard focus. It is draggable with the left mouse button.

Because the window is frameless and filled with child panels, mouse presses land
on those children and do NOT propagate to the top-level widget. So instead of
relying on propagation we install an event filter on every descendant we want to
be draggable (everything except an excluded subtree, e.g. the calendar, whose
own clicks must keep working).
"""
from __future__ import annotations

from typing import Callable, Iterable

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtWidgets import QWidget


def apply_desktop_flags(widget: QWidget) -> None:
    """Configure window flags/attributes for a pinned desktop widget."""
    widget.setWindowFlags(
        Qt.FramelessWindowHint
        | Qt.WindowStaysOnBottomHint
        | Qt.Tool  # keeps it out of the taskbar and Alt-Tab
        | Qt.WindowDoesNotAcceptFocus
    )
    widget.setAttribute(Qt.WA_TranslucentBackground, True)


class DragMixin:
    """Adds left-button drag-to-move to a frameless top-level QWidget.

    Host usage:
        self._init_drag(on_drop)          # once, before building children
        ...build UI...
        self.enable_drag(exclude=[cal])   # after children exist

    ``on_drop`` receives the final (x, y) once a drag ends and can persist it.
    Dragging is disabled while locked.
    """

    _drag_offset: QPoint | None
    _locked: bool

    def _init_drag(self, on_drop: Callable[[int, int], None]) -> None:
        self._drag_offset = None
        self._locked = False
        self._on_drop = on_drop
        self._drag_excluded: list[QWidget] = []
        self._drag_blocked = False

    def set_locked(self, locked: bool) -> None:
        self._locked = locked

    def enable_drag(self, exclude: Iterable[QWidget] = ()) -> None:
        """Install the drag event filter on this widget and its descendants.

        Widgets that are (or are inside) any of ``exclude`` are skipped so their
        own mouse handling — e.g. selecting a calendar date — is preserved.
        """
        self._drag_excluded = list(exclude)

        # Install on every descendant — including excluded ones — so we always
        # see the leaf press first and can tell where a drag attempt began.
        self.installEventFilter(self)
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)

    def _is_excluded(self, w: QWidget | None) -> bool:
        if w is None:
            return False
        for ex in self._drag_excluded:
            if w is ex or ex.isAncestorOf(w):
                return True
        return False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        etype = event.type()
        if etype == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and not self._locked:
                # Qt delivers the press to the leaf widget first, then bubbles it
                # up to ancestors. If the leaf is inside an excluded subtree
                # (e.g. the calendar) we mark this press so the bubble-up to the
                # draggable card never arms a drag.
                if isinstance(obj, QWidget) and self._is_excluded(obj):
                    self._drag_blocked = True
                elif not self._drag_blocked and self._drag_offset is None:
                    self._drag_offset = (
                        event.globalPosition().toPoint()
                        - self.frameGeometry().topLeft()
                    )
        elif etype == QEvent.MouseMove:
            if self._drag_offset is not None and (event.buttons() & Qt.LeftButton):
                self.move(event.globalPosition().toPoint() - self._drag_offset)
        elif etype == QEvent.MouseButtonRelease:
            self._drag_blocked = False
            if self._drag_offset is not None:
                self._drag_offset = None
                pos = self.pos()
                self._on_drop(pos.x(), pos.y())
        # Never consume the event — children still receive their clicks.
        return False
