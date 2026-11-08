"""Entry point for source runs and the windowed Windows executable."""
import logging
import os
from pathlib import Path
import sys


def main() -> int:
    # Keep Qt imports inside the guarded entry point: a missing native DLL must
    # fail a packaged smoke test immediately, without a blocking bootloader UI.
    from PySide6.QtCore import QStandardPaths, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from desktop_cat.window import CatWindow

    app = QApplication(sys.argv)
    app.setApplicationName("DesktopCat")
    app.setOrganizationName("DesktopCat")
    app.setQuitOnLastWindowClosed(False)
    log_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=log_dir / "desktop_cat.log", level=logging.ERROR,
                        encoding="utf-8", format="%(asctime)s %(levelname)s %(message)s")

    def on_error(kind, value, traceback):
        logging.error("Unhandled error", exc_info=(kind, value, traceback))
        if "--smoke-test" not in sys.argv:
            QMessageBox.critical(None, "Desktop Cat", f"Không thể chạy mèo.\n{value}\n\nNhật ký: {log_dir}")
        app.quit()

    sys.excepthook = on_error
    try:
        cat = CatWindow()
    except Exception:
        on_error(*sys.exc_info())
        return 1
    cat.show()
    # Headless/build smoke checks may request a clean, automatic shutdown.
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(1500, app.quit)
    return app.exec()


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        import traceback
        error_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "DesktopCat"
        error_dir.mkdir(parents=True, exist_ok=True)
        error_log = error_dir / "startup-error.log"
        error_log.write_text(traceback.format_exc(), encoding="utf-8")
        if "--smoke-test" not in sys.argv and sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, f"Không thể nạp thư viện khởi động.\nChi tiết: {error_log}",
                "Desktop Cat", 0x10)
        result = 1
    raise SystemExit(result)
