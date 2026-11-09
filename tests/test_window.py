"""Qt integration checks. Run with QT_QPA_PLATFORM=offscreen for CI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QRegion
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from desktop_cat.behavior import State
from desktop_cat.window import CatWindow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    cat = CatWindow()
    cat.timer.stop()
    cat.show()
    app.processEvents()
    yield cat
    cat.tray.hide()
    cat.close()
    cat.deleteLater()
    app.processEvents()


def test_all_frames_mask_and_native_pixel_scale(window):
    expected = {State.WALK: 8, State.EAT: 6, State.SLEEP: 4, State.WAKE: 6, State.ANGRY: 6}
    for state, count in expected.items():
        for direction in (-1, 1):
            frames = window.library.frames[state, direction]
            assert len(frames) == count
            for frame in frames:
                assert frame.size().width() == 128
                region = QRegion(frame.mask())
                assert not region.isEmpty()
                assert not region.contains(QPoint(0, 0))
                image = frame.toImage()
                for y in range(0, 128, 2):
                    for x in range(0, 128, 2):
                        assert image.pixel(x, y) == image.pixel(x + 1, y + 1)
    assert window.library.index(State.WAKE, 100) == 5


def test_click_and_drag_are_different(window, app):
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(80, 70))
    assert window.behavior.state == State.ANGRY
    QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(80, 70))
    QTest.mouseMove(window, QPoint(105, 70))
    QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(105, 70))
    assert window.behavior.state == State.WALK
    assert window.press_position is None
    assert not window.dragging


def test_pause_freezes_behavior_and_movement(window):
    window.toggle_pause()
    before = window.behavior.elapsed, window.x_float
    window.last_tick -= 0.2
    window._tick()
    assert (window.behavior.elapsed, window.x_float) == before
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(80, 70))
    assert window.behavior.state == State.WALK
    window.toggle_pause()
    window.last_tick -= 0.1
    window._tick()
    assert window.behavior.elapsed > 0


def test_hidden_menu_and_press_freeze_time(window):
    for reason in ("hidden", "menu", "pressed"):
        window.show()
        window.menu_open = reason == "menu"
        window.press_position = QPoint(0, 0) if reason == "pressed" else None
        if reason == "hidden":
            window.hide()
        before = window.behavior.elapsed
        window.last_tick -= 0.1
        window._tick()
        assert window.behavior.elapsed == before


def test_placement_clamps_and_baseline_is_above_taskbar(window):
    area = window.screen.availableGeometry()
    for x in (-100000, 100000):
        window.x_float = x
        window._place()
        assert window.x() >= area.x()
        assert window.x() + window.width() <= area.x() + area.width()
        assert window.y() + 60 * window.settings.display_scale == area.y() + area.height()


def test_no_tray_means_hide_is_disabled(window):
    window.tray_available = False
    window.toggle_visible()
    assert window.isVisible()

def test_drag_selects_screen_at_cursor_and_settles_at_bottom(window, monkeypatch):
    from PySide6.QtCore import QObject, QRect, Signal, QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    class Screen(QObject):
        availableGeometryChanged = Signal(object)
        geometryChanged = Signal(object)

        def availableGeometry(self):
            return QRect(-1600, -200, 1600, 900)

    secondary = Screen()
    monkeypatch.setattr(QApplication, "screenAt", staticmethod(lambda point: secondary))
    window.press_position = QPoint(100, 100)
    window.press_offset = QPoint(50, 60)
    event = QMouseEvent(QEvent.Type.MouseMove, QPointF(30, 30), QPointF(-500, 200),
                        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)
    window.mouseMoveEvent(event)
    assert window.screen is secondary
    assert window.pos() == QPoint(-550, 140)
    release = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(50, 60),
                          QPointF(-500, 200), Qt.MouseButton.LeftButton,
                          Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    window.mouseReleaseEvent(release)
    assert window.screen is secondary
    assert window.x() == -550
    assert window.y() + 120 == 700
    assert window.behavior.state == State.WALK
    window.screen = None
    window._bind_screen(QApplication.primaryScreen())
