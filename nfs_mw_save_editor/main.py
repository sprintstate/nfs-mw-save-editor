from __future__ import annotations

import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from resources import resource_path
from ui.main_window import MainWindow
from ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    icon_path = resource_path("assets", "icon.ico")
    icon = QIcon(str(icon_path)) if icon_path.exists() else None
    if icon is not None:
        app.setWindowIcon(icon)
    apply_theme(app)
    w = MainWindow()
    if icon is not None:
        w.setWindowIcon(icon)
    w.resize(1180, 780)
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
