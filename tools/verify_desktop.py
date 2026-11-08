"""Native Windows checks, without injecting input or changing system DPI.

Run in separate processes with QT_SCALE_FACTOR=1, 1.25 and 1.5.
Captures only our rendered cat; does not capture other desktop windows.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from desktop_cat.behavior import State
from desktop_cat.window import CatWindow


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    cat = CatWindow()
    cat.timer.stop()
    cat.show()
    failures = []
    results = {}

    def verify():
        try:
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user.GetWindowLongW.restype = wintypes.LONG
            user.WindowFromPoint.argtypes = [wintypes.POINT]
            user.WindowFromPoint.restype = wintypes.HWND
            user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
            user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            hwnd = int(cat.winId())
            style = user.GetWindowLongW(hwnd, -20)
            assert style & 0x00000080, "Missing WS_EX_TOOLWINDOW"
            assert style & 0x00000008, "Missing WS_EX_TOPMOST"
            assert style & 0x08000000, "Missing WS_EX_NOACTIVATE"
            native_rect = wintypes.RECT()
            assert user.GetClientRect(hwnd, ctypes.byref(native_rect))

            def hit(x, y):
                point = wintypes.POINT(round(x * native_rect.right / cat.width()),
                                       round(y * native_rect.bottom / cat.height()))
                assert user.ClientToScreen(hwnd, ctypes.byref(point))
                return user.WindowFromPoint(point)

            # A transparent corner must resolve to the underlying desktop/app.
            assert hit(1, 1) != hwnd, "Transparent corner intercepts mouse"
            assert cat.mask().contains(QPoint(80, 70))
            assert hit(80, 70) == hwnd, "Visible cat does not receive mouse"
            snapshots = ROOT / "previews" / "native"
            snapshots.mkdir(parents=True, exist_ok=True)
            scale = os.environ.get("QT_SCALE_FACTOR", "1")
            for state in State:
                cat.behavior._enter(state)
                cat.behavior.elapsed = 0.35
                cat._render_frame()
                app.processEvents()
                assert cat.grab().save(str(snapshots / f"{scale}-{state}.png"))
            cat.behavior.restart_walk()
            cat._render_frame()
            QTest.mouseClick(cat, Qt.MouseButton.LeftButton, pos=QPoint(80, 70))
            assert cat.behavior.state == State.ANGRY
            old_x = cat.x_float
            QTest.mousePress(cat, Qt.MouseButton.LeftButton, pos=QPoint(80, 70))
            QTest.mouseMove(cat, QPoint(112, 70))
            QTest.mouseRelease(cat, Qt.MouseButton.LeftButton, pos=QPoint(112, 70))
            assert cat.behavior.state == State.WALK
            assert cat.x_float > old_x, "Dragging did not move the cat"
            cat.toggle_pause()
            before = (cat.behavior.elapsed, cat.x_float)
            cat.last_tick -= 0.2
            cat._tick()
            assert before == (cat.behavior.elapsed, cat.x_float)
            cat.toggle_pause()
            if cat.tray_available:
                cat.toggle_visible()
                assert not cat.isVisible()
                cat.toggle_visible()
                assert cat.isVisible()
            cat.menu.popup(cat.pos() + QPoint(20, -100))
            app.processEvents()
            assert cat.menu.isVisible() and cat.menu_open
            cat.menu.close()
            app.processEvents()
            assert not cat.menu_open
            area = cat.screen.availableGeometry()
            for x in (-100000, 100000):
                cat.x_float = x
                cat._place()
                assert area.left() <= cat.x() <= area.x() + area.width() - cat.width()
                assert cat.y() + 120 == area.y() + area.height()
            results.update(scale=scale, device_pixel_ratio=cat.devicePixelRatioF(),
                           native_size=[native_rect.right, native_rect.bottom],
                           available_geometry=[area.x(), area.y(), area.width(), area.height()],
                           native_styles=True, transparent_hit_test=True, visible_hit_test=True,
                           click_drag=True, pause=True, tray_available=cat.tray_available,
                           menu=True, screen_edges=True, rendered_states=5)
        except Exception as error:
            failures.append(f"{type(error).__name__}: {error}")
        finally:
            cat.close()
            app.quit()

    QTimer.singleShot(300, verify)
    app.exec()
    print(json.dumps({"results": results, "failures": failures}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
