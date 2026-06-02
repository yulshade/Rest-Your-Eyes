"""Interactive calendar panel built on Qt's QCalendarWidget.

The widget lives in a frameless, non-focusable desktop window, so Qt's default
navigation bar — which changes the year via a keyboard spinbox — can't be
confirmed (the window never takes keyboard focus). We hide that bar and provide
our own mouse-only navigation: prev/next month and prev/next year buttons, plus
a centre label that jumps back to today.
"""
from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCalendarWidget,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CalendarPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 12)
        layout.setSpacing(6)

        self._cal = QCalendarWidget()
        self._cal.setObjectName("calendar")
        self._cal.setGridVisible(False)
        self._cal.setFirstDayOfWeek(Qt.Monday)
        self._cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self._cal.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self._cal.setNavigationBarVisible(False)  # we supply our own below
        self._cal.clicked.connect(self._on_clicked)
        self._cal.currentPageChanged.connect(lambda *_: self._sync_header())

        layout.addLayout(self._build_navbar())
        layout.addWidget(self._cal)

        self._selected = QLabel()
        self._selected.setObjectName("subValue")
        layout.addWidget(self._selected)

        self._sync_header()
        self._on_clicked(QDate.currentDate())

    # ---- custom navigation bar ----
    def _build_navbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(2)

        self._prev_year = self._nav_button("«", "Previous year", lambda: self._shift_year(-1))
        self._prev_month = self._nav_button("‹", "Previous month", lambda: self._shift_month(-1))
        self._next_month = self._nav_button("›", "Next month", lambda: self._shift_month(1))
        self._next_year = self._nav_button("»", "Next year", lambda: self._shift_year(1))

        self._header = QToolButton()
        self._header.setObjectName("calHeader")
        self._header.setToolTip("Jump to today")
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.clicked.connect(self._goto_today)
        # No fixed width: the header sizes to its text and is kept centred by the
        # equal stretches on either side, so gaps stay symmetric for any month.
        # The window width is pinned (main.py) so nothing here can resize the card.

        bar.addWidget(self._prev_year)
        bar.addWidget(self._prev_month)
        bar.addStretch(1)
        bar.addWidget(self._header)
        bar.addStretch(1)
        bar.addWidget(self._next_month)
        bar.addWidget(self._next_year)
        return bar

    def _nav_button(self, text: str, tip: str, slot) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("calNav")
        btn.setText(text)
        btn.setToolTip(tip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    # ---- navigation logic ----
    def _shift_month(self, delta: int) -> None:
        month = self._cal.monthShown() + delta
        year = self._cal.yearShown()
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        self._cal.setCurrentPage(year, month)

    def _shift_year(self, delta: int) -> None:
        self._cal.setCurrentPage(self._cal.yearShown() + delta, self._cal.monthShown())

    def _goto_today(self) -> None:
        today = QDate.currentDate()
        self._cal.setCurrentPage(today.year(), today.month())
        self._cal.setSelectedDate(today)
        self._on_clicked(today)

    # ---- display sync ----
    def _sync_header(self) -> None:
        shown = QDate(self._cal.yearShown(), self._cal.monthShown(), 1)
        self._header.setText(shown.toString("MMMM yyyy"))

    def _on_clicked(self, qdate: QDate) -> None:
        self._selected.setText(qdate.toString("dddd, d MMMM yyyy"))
