"""Reusable widgets for the NFS MW Save Editor UI."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QPropertyAnimation, QTimer, QEasingCurve
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.icon_map import token_icon_path


class WantSpinBox(QSpinBox):
    """SpinBox that ignores mouse wheel to prevent accidental edits."""

    def wheelEvent(self, event):
        event.ignore()


class TokenCard(QWidget):
    """A dark card representing a single Junkman token."""

    CARD_WIDTH = 240
    ICON_SIZE = 40

    def __init__(
        self,
        token_id: int,
        name: str,
        have: int,
        want: int,
        max_val: int,
        on_change: Callable[[int, int], None],
        on_rename: Callable[[int, str], None],
    ):
        super().__init__()
        self.token_id = token_id
        self._on_change = on_change
        self._on_rename = on_rename

        self.setObjectName("tokenCard")
        self.setFixedWidth(self.CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setToolTip(f"Token ID: {token_id}")
        self.setProperty("hovered", False)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)
        root.setAlignment(Qt.AlignTop)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        icon_path = token_icon_path(token_id)
        if icon_path and icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(
                self.ICON_SIZE,
                self.ICON_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.icon_label.setPixmap(pix)
        icon_row = QHBoxLayout()
        icon_row.setAlignment(Qt.AlignCenter)
        icon_row.addWidget(self.icon_label)
        root.addLayout(icon_row)

        self.name_edit = QLineEdit(name)
        self.name_edit.setAlignment(Qt.AlignCenter)
        self.name_edit.setObjectName("cardName")
        self.name_edit.setToolTip(name)
        self.name_edit.setCursorPosition(0)
        self.name_edit.setMinimumWidth(180)
        self.name_edit.editingFinished.connect(self._handle_rename)
        root.addWidget(self.name_edit)

        self.have_label = QLabel(f"Have: {have}")
        self.have_label.setObjectName("haveLabel")
        self.have_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.have_label)

        spin_row = QHBoxLayout()
        spin_row.setSpacing(4)
        spin_row.setAlignment(Qt.AlignCenter)

        self.btn_minus = QPushButton("-")
        self.btn_minus.setObjectName("cardBtn")
        self.btn_minus.setFixedSize(26, 26)
        self.btn_minus.clicked.connect(lambda: self._bump(-1))

        self.spin = WantSpinBox()
        self.spin.setRange(0, max_val)
        self.spin.setValue(want)
        self.spin.setFixedWidth(60)
        self.spin.setAlignment(Qt.AlignCenter)
        self.spin.valueChanged.connect(self._on_spin_changed)

        self.btn_plus = QPushButton("+")
        self.btn_plus.setObjectName("cardBtn")
        self.btn_plus.setFixedSize(26, 26)
        self.btn_plus.clicked.connect(lambda: self._bump(1))

        spin_row.addWidget(self.btn_minus)
        spin_row.addWidget(self.spin)
        spin_row.addWidget(self.btn_plus)
        root.addLayout(spin_row)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, max_val)
        self.slider.setValue(want)
        self.slider.setObjectName("cardSlider")
        self.slider.setTracking(False)
        self.slider.valueChanged.connect(self._on_slider_changed)
        root.addWidget(self.slider)

        self._apply_changed_state(want != have)

    def set_have_want(self, have: int, want: int) -> None:
        self.have_label.setText(f"Have: {have}")
        self.spin.blockSignals(True)
        self.spin.setValue(want)
        self.spin.blockSignals(False)
        self.slider.blockSignals(True)
        self.slider.setValue(want)
        self.slider.blockSignals(False)
        self._apply_changed_state(want != have)

    def set_max(self, max_val: int) -> None:
        cur = self.spin.value()
        self.spin.setRange(0, max_val)
        self.spin.setValue(min(cur, max_val))
        self.slider.setRange(0, max_val)
        self.slider.setValue(min(cur, max_val))

    def _bump(self, delta: int) -> None:
        new_val = max(self.spin.minimum(), min(self.spin.maximum(), self.spin.value() + delta))
        self.spin.setValue(new_val)

    def _on_spin_changed(self, val: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(val)
        self.slider.blockSignals(False)
        self._on_change(self.token_id, val)
        have = int(self.have_label.text().replace("Have: ", ""))
        self._apply_changed_state(val != have)

    def _on_slider_changed(self, val: int) -> None:
        self.spin.blockSignals(True)
        self.spin.setValue(val)
        self.spin.blockSignals(False)
        self._on_change(self.token_id, val)
        have = int(self.have_label.text().replace("Have: ", ""))
        self._apply_changed_state(val != have)

    def _handle_rename(self) -> None:
        new_name = self.name_edit.text().strip() or f"Token #{self.token_id}"
        self.name_edit.setText(new_name)
        self.name_edit.setToolTip(new_name)
        self.name_edit.setCursorPosition(0)
        self._on_rename(self.token_id, new_name)

    def _apply_changed_state(self, changed: bool) -> None:
        self.setProperty("changed", changed)
        self.style().unpolish(self)
        self.style().polish(self)

    # ── Hover effect ─────────────────────────────────────────────

    def enterEvent(self, event) -> None:
        self.setProperty("hovered", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setProperty("hovered", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)


class ToastNotification(QLabel):
    """A brief, self-destroying notification that appears at the top-right."""

    _active: list["ToastNotification"] = []   # class-level stack

    def __init__(self, parent: QWidget, message: str, *, is_error: bool = False):
        super().__init__(message, parent)
        self.setObjectName("toastError" if is_error else "toastSuccess")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(36)
        self.setMinimumWidth(220)
        self.adjustSize()
        self.setFixedWidth(max(220, self.sizeHint().width() + 32))

        # opacity effect for fade-out
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)

        # position at top-right
        px = parent.width() - self.width() - 16
        self.move(px, -self.height())
        self.show()
        self.raise_()

        # slide in
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(300)
        self._slide.setStartValue(self.pos())
        offset = 12 + len(ToastNotification._active) * 44
        from PySide6.QtCore import QPoint
        self._slide.setEndValue(QPoint(px, offset))
        self._slide.setEasingCurve(QEasingCurve.OutCubic)
        self._slide.start()

        ToastNotification._active.append(self)

        # auto-dismiss
        QTimer.singleShot(2500, self._fade_out)

    def _fade_out(self):
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(400)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._cleanup)
        self._fade.start()

    def _cleanup(self):
        if self in ToastNotification._active:
            ToastNotification._active.remove(self)
        self.deleteLater()

    @staticmethod
    def show_toast(parent: QWidget, message: str, *, is_error: bool = False):
        """Show a brief toast notification."""
        ToastNotification(parent, message, is_error=is_error)
