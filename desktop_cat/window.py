import time

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from .animation import AnimationLibrary, COATS
from .behavior import Behavior, State, move_within_bounds
from .settings import Settings


class CatWindow(QWidget):
    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or Settings()
        self.setWindowTitle("Mèo tam thể — Desktop Cat")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool |
                            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(self.settings.display_size, self.settings.display_size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preferences = QSettings("DesktopCat", "DesktopCat")
        saved = self.preferences.value("coat", "calico")
        self.coat = saved if saved in COATS else "calico"
        if saved != self.coat:
            self.preferences.setValue("coat", self.coat)
        self.library = AnimationLibrary(self.width(), coat=self.coat)
        self.behavior = Behavior(self.settings, self.library.duration(State.WAKE))
        self.direction = 1
        self.paused = False
        self.menu_open = False
        self.press_position: QPoint | None = None
        self.dragging = False
        self.press_x = 0.0
        self.press_offset = QPoint()
        self.screen = None
        self.x_float = 0.0
        self.current_pixmap = None
        self.frame_key = None
        self.last_tick = time.monotonic()

        self.menu = QMenu(self)
        self.menu.setStyleSheet(
            "QMenu { background: #fff8ef; color: #40352e; border: 1px solid #d6bda4;"
            "padding: 6px; font: 10pt 'Segoe UI'; }"
            "QMenu::item { padding: 7px 24px; }"
            "QMenu::item:selected { background: #f3dcc0; border-radius: 4px; }"
            "QMenu::separator { height: 1px; background: #e7d6c3; margin: 4px; }")
        title = self.menu.addAction("🐾  Mèo tam thể")
        title.setEnabled(False)
        self.menu.addSeparator()
        colors = self.menu.addMenu("Màu mèo")
        self.color_group = QActionGroup(self)
        self.color_group.setExclusive(True)
        for key, (label, _) in COATS.items():
            action = colors.addAction(label)
            action.setCheckable(True)
            action.setChecked(key == self.coat)
            action.setData(key)
            self.color_group.addAction(action)
        self.color_group.triggered.connect(lambda action: self.change_coat(action.data()))
        self.pause_action = QAction("Tạm dừng", self)
        self.pause_action.triggered.connect(self.toggle_pause)
        self.menu.addAction(self.pause_action)
        self.visible_action = QAction("Ẩn mèo", self)
        self.visible_action.triggered.connect(self.toggle_visible)
        self.menu.addAction(self.visible_action)
        self.menu.addSeparator()
        self.menu.addAction("Thoát", QApplication.instance().quit)
        self.menu.aboutToShow.connect(self._menu_showing)
        self.menu.aboutToHide.connect(self._menu_hiding)

        icon = QIcon(self.library.frame(State.WALK, 0, 1))
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Mèo tam thể • Chuột phải để mở menu")
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        if self.tray_available:
            self.tray.show()
        else:
            self.visible_action.setEnabled(False)

        app = QApplication.instance()
        app.screenRemoved.connect(self._screen_removed)
        self._bind_screen(app.primaryScreen())
        self.x_float = self.screen.availableGeometry().center().x() - self.width() / 2
        self._place()
        self._render_frame()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timer.start(self.settings.frame_interval_ms)

    def change_coat(self, coat):
        library = AnimationLibrary(self.width(), coat=coat)
        self.library = library
        self.coat = coat
        self.preferences.setValue("coat", coat)
        self.frame_key = None
        self._render_frame()
        icon = QIcon(self.library.frame(State.WALK, 0, 1))
        self.setWindowIcon(icon)
        self.tray.setIcon(icon)
        self.tray.setToolTip("Mèo " + COATS[coat][0] + " • Chuột phải để chọn màu")

    def _bind_screen(self, screen):
        if self.screen is not None:
            try:
                self.screen.availableGeometryChanged.disconnect(self._geometry_changed)
                self.screen.geometryChanged.disconnect(self._geometry_changed)
            except (RuntimeError, TypeError):
                pass
        self.screen = screen or QApplication.primaryScreen()
        if self.screen is not None:
            self.screen.availableGeometryChanged.connect(self._geometry_changed)
            self.screen.geometryChanged.connect(self._geometry_changed)
            self._place()

    def _screen_removed(self, screen):
        if screen is self.screen:
            self.screen = None
            self._bind_screen(QApplication.primaryScreen())

    def _geometry_changed(self, _geometry):
        self._place()

    def _bounds(self):
        area = self.screen.availableGeometry()
        return area.left(), max(area.left(), area.x() + area.width() - self.width())

    def _place(self):
        if self.screen is None:
            return
        left, right = self._bounds()
        self.x_float = max(left, min(self.x_float, right))
        area = self.screen.availableGeometry()
        # All drawings share baseline y=59 (exclusive y=60).
        # Align that baseline, not the transparent bottom margin, to the taskbar.
        ground = self.library.animations[State.WALK.value].get("ground_y", 60)
        bottom_margin = (self.settings.sprite_size - ground) * self.settings.display_scale
        self.move(round(self.x_float), area.y() + area.height() - self.height() + bottom_margin)

    @property
    def frozen(self):
        return (self.paused or self.menu_open or self.press_position is not None
                or not self.isVisible())

    def _tick(self):
        now = time.monotonic()
        # Avoid a leap across the desktop after Windows wakes from suspend.
        dt = min(max(now - self.last_tick, 0.0), 0.25)
        self.last_tick = now
        walking = self.behavior.advance(dt, frozen=self.frozen)
        if walking:
            self.x_float, self.direction = move_within_bounds(
                self.x_float, self.direction, walking * self.settings.speed, *self._bounds())
            self._place()
        self._render_frame()

    def _render_frame(self):
        key = (self.behavior.state,
               self.library.index(self.behavior.state, self.behavior.elapsed), self.direction)
        if key == self.frame_key:
            return
        self.frame_key = key
        self.current_pixmap = self.library.frame(
            self.behavior.state, self.behavior.elapsed, self.direction)
        # A native window region excludes transparent pixels from hit testing.
        self.setMask(self.current_pixmap.mask())
        self.update()

    def paintEvent(self, event):
        if self.current_pixmap is not None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.drawPixmap(0, 0, self.current_pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_position = event.globalPosition().toPoint()
            self.press_x = self.x_float
            self.press_offset = self.press_position - self.pos()
            self.dragging = False
            self.last_tick = time.monotonic()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.press_position is None:
            return
        delta = event.globalPosition().toPoint() - self.press_position
        if not self.dragging and delta.manhattanLength() >= QApplication.startDragDistance():
            self.dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        if self.dragging:
            cursor = event.globalPosition().toPoint()
            target = QApplication.screenAt(cursor)
            if target is not None and target is not self.screen:
                self._bind_screen(target)
            position = cursor - self.press_offset
            self.x_float = float(position.x())
            self.move(position)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.press_position is not None:
            dragged = self.dragging
            self.press_position = None
            self.dragging = False
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            if dragged:
                target = QApplication.screenAt(event.globalPosition().toPoint())
                if target is not None and target is not self.screen:
                    self._bind_screen(target)
                self._place()
                self.behavior.restart_walk()
            elif not self.paused:
                self.behavior.click()
            self.last_tick = time.monotonic()
            self._render_frame()
            event.accept()

    def contextMenuEvent(self, event):
        self.menu.popup(event.globalPos())
        event.accept()

    def _menu_showing(self):
        self.menu_open = True

    def _menu_hiding(self):
        self.menu_open = False
        self.last_tick = time.monotonic()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_action.setText("Tiếp tục" if self.paused else "Tạm dừng")
        self.last_tick = time.monotonic()

    def toggle_visible(self):
        if not self.tray_available:
            return
        if self.isVisible():
            self.hide()
            self.visible_action.setText("Hiện mèo")
        else:
            self._place()
            self.show()
            self.visible_action.setText("Ẩn mèo")
        self.last_tick = time.monotonic()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visible()

    def closeEvent(self, event):
        self.tray.hide()
        QApplication.instance().quit()
        event.accept()
