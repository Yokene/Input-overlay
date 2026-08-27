import sys
import json
import os
import time
import traceback
import keyboard

from PySide6.QtGui import QPainter, QPen, QBrush, QFont, QColor, QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMenu,
    QSystemTrayIcon,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QPushButton,
)

# =========================================================
# CONFIG
# =========================================================

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

CRASH_LOG_FILE = os.path.join(BASE_DIR, "crash_log.txt")


DEFAULT_CONFIG = {
    "key": "up",
    "text": "↑",
    "close_key": "f8",
    "settings_close_key": "f9",

    "width": 100,
    "height": 100,

    "corner_radius": 20,
    "border_width": 3,

    "normal_color": "#FFFFFFFF",
    "pressed_color": "#00FF00FF",

    "border_color": "#000000FF",
    "pressed_border_color": "#000000FF",

    "text_color": "#000000FF",
    "pressed_text_color": "#000000FF",

    "font_size": 40,
    "cps_font_size": 20
}


# =========================================================
# CRASH LOGGING
# =========================================================
# Собранный в exe (--windowed/--noconsole) файл не показывает
# консоль, поэтому необработанные исключения раньше приводили
# к тихому закрытию программы без единого сообщения.
# Теперь любое такое исключение будет дописано в crash_log.txt
# рядом с exe — это позволит понять причину, если ещё что-то
# пойдёт не так.

def setup_crash_logging():

    def excepthook(exc_type, exc_value, exc_tb):
        try:
            with open(CRASH_LOG_FILE, "a", encoding="utf-8") as log_file:
                log_file.write("\n" + "=" * 60 + "\n")
                log_file.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=log_file)
        except Exception:
            pass

        # Если запущено из консоли/Python — выведем и туда
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = excepthook


# =========================================================
# LOAD CONFIG
# =========================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)

        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value

        return config

    except Exception as error:
        print("Ошибка config.json:", error)
        return DEFAULT_CONFIG.copy()


# =========================================================
# COLOR
# =========================================================

def parse_hex_color(hex_str):
    """
    Поддерживает:
    #RRGGBB
    #RRGGBBAA
    """

    if not hex_str:
        return QColor(255, 255, 255, 255)

    hex_str = str(hex_str).strip()

    if not hex_str.startswith("#"):
        hex_str = "#" + hex_str

    cleaned = hex_str[1:]

    # #RRGGBBAA
    if len(cleaned) == 8:
        try:
            r = int(cleaned[0:2], 16)
            g = int(cleaned[2:4], 16)
            b = int(cleaned[4:6], 16)
            a = int(cleaned[6:8], 16)

            return QColor(r, g, b, a)

        except ValueError:
            pass

    # #RRGGBB
    color = QColor(hex_str)

    if color.isValid():
        return color

    return QColor(255, 255, 255, 255)


# =========================================================
# SETTINGS WINDOW
# =========================================================
# Раньше self.open_settings вызывался из меню трея и из
# контекстного меню, но нигде не был определён. Это вызывало
# AttributeError уже в __init__ (при создании иконки трея),
# то есть программа падала ДО показа окна — из-за этого
# в exe-сборке казалось, что "main не запускается".

class SettingsWindow(QWidget):

    def __init__(self, overlay):
        super().__init__()

        self.overlay = overlay
        self.config = overlay.config

        self.setWindowTitle("Настройки Input Overlay")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.resize(380, 520)

        layout = QFormLayout(self)

        self.key_edit = QLineEdit(str(self.config.get("key", "")))
        layout.addRow("Клавиша (key):", self.key_edit)

        self.text_edit = QLineEdit(str(self.config.get("text", "")))
        layout.addRow("Текст на кнопке:", self.text_edit)

        self.close_key_edit = QLineEdit(str(self.config.get("close_key", "")))
        layout.addRow("Клавиша закрытия программы:", self.close_key_edit)

        self.settings_close_key_edit = QLineEdit(
            str(self.config.get("settings_close_key", ""))
        )
        layout.addRow("Клавиша закрытия настроек:", self.settings_close_key_edit)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 2000)
        self.width_spin.setValue(int(self.config.get("width", 100)))
        layout.addRow("Ширина:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 2000)
        self.height_spin.setValue(int(self.config.get("height", 100)))
        layout.addRow("Высота:", self.height_spin)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 200)
        self.radius_spin.setValue(int(self.config.get("corner_radius", 20)))
        layout.addRow("Радиус углов:", self.radius_spin)

        self.border_spin = QSpinBox()
        self.border_spin.setRange(0, 50)
        self.border_spin.setValue(int(self.config.get("border_width", 3)))
        layout.addRow("Толщина рамки:", self.border_spin)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(4, 200)
        self.font_spin.setValue(int(self.config.get("font_size", 40)))
        layout.addRow("Размер шрифта:", self.font_spin)

        self.cps_font_spin = QSpinBox()
        self.cps_font_spin.setRange(4, 200)
        self.cps_font_spin.setValue(int(self.config.get("cps_font_size", 20)))
        layout.addRow("Размер шрифта CPS:", self.cps_font_spin)

        self.normal_color_edit = QLineEdit(str(self.config.get("normal_color", "")))
        layout.addRow("Цвет (обычный):", self.normal_color_edit)

        self.pressed_color_edit = QLineEdit(str(self.config.get("pressed_color", "")))
        layout.addRow("Цвет (нажато):", self.pressed_color_edit)

        self.border_color_edit = QLineEdit(str(self.config.get("border_color", "")))
        layout.addRow("Цвет рамки:", self.border_color_edit)

        self.pressed_border_color_edit = QLineEdit(
            str(self.config.get("pressed_border_color", ""))
        )
        layout.addRow("Цвет рамки (нажато):", self.pressed_border_color_edit)

        self.text_color_edit = QLineEdit(str(self.config.get("text_color", "")))
        layout.addRow("Цвет текста:", self.text_color_edit)

        self.pressed_text_color_edit = QLineEdit(
            str(self.config.get("pressed_text_color", ""))
        )
        layout.addRow("Цвет текста (нажато):", self.pressed_text_color_edit)

        buttons_row = QHBoxLayout()

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_settings)
        buttons_row.addWidget(save_button)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        buttons_row.addWidget(close_button)

        layout.addRow(buttons_row)

        # Опрос клавиши закрытия настроек (работает даже без фокуса окна)
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.check_close_key)
        self.close_timer.start(50)

    def check_close_key(self):
        try:
            if keyboard.is_pressed(self.config.get("settings_close_key", "f9")):
                self.close()
        except Exception:
            pass

    def save_settings(self):

        self.config["key"] = self.key_edit.text().strip() or self.config["key"]
        self.config["text"] = self.text_edit.text()
        self.config["close_key"] = (
            self.close_key_edit.text().strip() or self.config["close_key"]
        )
        self.config["settings_close_key"] = (
            self.settings_close_key_edit.text().strip()
            or self.config["settings_close_key"]
        )

        self.config["width"] = self.width_spin.value()
        self.config["height"] = self.height_spin.value()
        self.config["corner_radius"] = self.radius_spin.value()
        self.config["border_width"] = self.border_spin.value()
        self.config["font_size"] = self.font_spin.value()
        self.config["cps_font_size"] = self.cps_font_spin.value()

        self.config["normal_color"] = self.normal_color_edit.text().strip()
        self.config["pressed_color"] = self.pressed_color_edit.text().strip()
        self.config["border_color"] = self.border_color_edit.text().strip()
        self.config["pressed_border_color"] = (
            self.pressed_border_color_edit.text().strip()
        )
        self.config["text_color"] = self.text_color_edit.text().strip()
        self.config["pressed_text_color"] = (
            self.pressed_text_color_edit.text().strip()
        )

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as file:
                json.dump(self.config, file, ensure_ascii=False, indent=4)
        except Exception as error:
            print("Ошибка сохранения config.json:", error)

        self.overlay.update_size()
        self.overlay.update()

    def closeEvent(self, event):
        self.close_timer.stop()
        event.accept()


# =========================================================
# OVERLAY
# =========================================================

class KeyOverlay(QWidget):

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.key_pressed = False
        self.click_times = []

        self.dragging = False
        self.drag_position = QPoint()

        self.settings_window = None

        self.setWindowTitle("Input Overlay")

        # -------------------------------------------------
        # ПРОЗРАЧНОЕ ОКНО
        # -------------------------------------------------

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True
        )

        self.setAttribute(
            Qt.WA_NoSystemBackground,
            True
        )

        self.update_size()

        # -------------------------------------------------
        # CHECK KEY
        # -------------------------------------------------

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_key)
        self.timer.start(10)

        # -------------------------------------------------
        # CPS UPDATE
        # -------------------------------------------------

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update)
        self.refresh_timer.start(50)

        # -------------------------------------------------
        # TRAY ICON (сворачивание/разворачивание/закрытие)
        # -------------------------------------------------

        self.create_tray_icon()

        self.show()


    # =====================================================
    # TRAY ICON
    # =====================================================

    def create_tray_icon(self):

        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QColor("#4CAF50"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pixmap), self)
        self.tray_icon.setToolTip("Input Overlay")

        tray_menu = QMenu()

        self.toggle_action = tray_menu.addAction("Свернуть оверлей")
        self.toggle_action.triggered.connect(self.toggle_visibility)

        tray_menu.addSeparator()

        exit_action = tray_menu.addAction("Закрыть программу")
        exit_action.triggered.connect(self.close_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)

        self.tray_icon.show()

    def on_tray_activated(self, reason):

        # Клик левой кнопкой по иконке в трее — тоже сворачивает/разворачивает
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):

        if self.isVisible():
            self.hide()
            self.toggle_action.setText("Развернуть оверлей")
        else:
            self.show()
            self.toggle_action.setText("Свернуть оверлей")

    def close_app(self):

        self.timer.stop()
        self.refresh_timer.stop()
        self.tray_icon.hide()

        QApplication.quit()

    # =====================================================
    # SIZE
    # =====================================================

    def update_size(self):

        self.setFixedSize(
            self.config["width"] + 20,
            self.config["height"] + 20
        )

        self.update()

    # =====================================================
    # CPS
    # =====================================================

    def get_cps(self):

        current_time = time.time()

        self.click_times = [
            t for t in self.click_times
            if current_time - t <= 1.0
        ]

        return len(self.click_times)

    # =====================================================
    # KEY CHECK
    # =====================================================

    def check_key(self):

        # -------------------------------------------------
        # CLOSE KEY
        # -------------------------------------------------

        try:
            close_pressed = keyboard.is_pressed(
                self.config["close_key"]
            )
        except Exception:
            close_pressed = False

        if close_pressed:
            self.close_app()
            return

        # -------------------------------------------------
        # MAIN KEY
        # -------------------------------------------------

        try:
            pressed = keyboard.is_pressed(
                self.config["key"]
            )
        except Exception:
            pressed = False

        # Новый клик
        if pressed and not self.key_pressed:
            self.click_times.append(time.time())

        # Изменилось состояние клавиши
        if pressed != self.key_pressed:

            self.key_pressed = pressed

            self.update()

    # =====================================================
    # PAINT
    # =====================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        # -------------------------------------------------
        # СЛОЙ ДЛЯ ПЕРЕХВАТА КЛИКОВ
        # -------------------------------------------------
        # У окон с WA_TranslucentBackground Windows пропускает клики
        # мимо (click-through) в тех местах, где альфа пикселя = 0.
        # Поэтому заливаем ВЕСЬ виджет почти незаметным цветом
        # (альфа = 1 из 255 — глазом не видно), чтобы перетаскивание
        # работало по любой точке оверлея, даже если normal_color
        # / pressed_color заданы полностью прозрачными, и даже
        # в пустых отступах вокруг самой кнопки.

        painter.fillRect(
            self.rect(),
            QColor(0, 0, 0, 1)
        )

        width = self.config["width"]
        height = self.config["height"]

        radius = self.config["corner_radius"]
        border_width = self.config["border_width"]

        # -------------------------------------------------
        # COLORS
        # -------------------------------------------------

        if self.key_pressed:

            fill_key = "pressed_color"
            border_key = "pressed_border_color"
            text_key = "pressed_text_color"

        else:

            fill_key = "normal_color"
            border_key = "border_color"
            text_key = "text_color"

        fill_color = parse_hex_color(
            self.config.get(
                fill_key,
                self.config["normal_color"]
            )
        )

        border_color = parse_hex_color(
            self.config.get(
                border_key,
                self.config["border_color"]
            )
        )

        text_color = parse_hex_color(
            self.config.get(
                text_key,
                self.config["text_color"]
            )
        )

        # -------------------------------------------------
        # TRANSPARENT BACKGROUND
        # -------------------------------------------------

        painter.setCompositionMode(
            QPainter.CompositionMode_SourceOver
        )

        painter.setBrush(
            Qt.NoBrush
        )

        painter.setPen(
            Qt.NoPen
        )

        # -------------------------------------------------
        # BUTTON
        # -------------------------------------------------

        button_rect = QRectF(
            10,
            10,
            width,
            height
        )

        # -------------------------------------------------
        # FILL
        # -------------------------------------------------

        if fill_color.alpha() > 0:

            painter.setBrush(
                QBrush(fill_color)
            )

        else:

            painter.setBrush(
                Qt.NoBrush
            )

        # -------------------------------------------------
        # BORDER
        # -------------------------------------------------

        if border_width > 0 and border_color.alpha() > 0:

            pen = QPen(border_color)
            pen.setWidth(border_width)

            painter.setPen(pen)

        else:

            painter.setPen(
                Qt.NoPen
            )

        painter.drawRoundedRect(
            button_rect,
            radius,
            radius
        )

        # -------------------------------------------------
        # TEXT
        # -------------------------------------------------

        if text_color.alpha() > 0:

            painter.setPen(
                QPen(text_color)
            )

            # -------------------------------------------------
            # MAIN TEXT
            # -------------------------------------------------

            top_rect = QRectF(
                10,
                10,
                width,
                height * 0.52
            )

            font_main = QFont()

            font_main.setPixelSize(
                self.config["font_size"]
            )

            font_main.setBold(True)

            painter.setFont(
                font_main
            )

            painter.drawText(
                top_rect,
                Qt.AlignCenter | Qt.AlignBottom,
                self.config["text"]
            )

            # -------------------------------------------------
            # CPS
            # -------------------------------------------------

            cps_val = self.get_cps()

            cps_text = str(cps_val)

            bottom_rect = QRectF(
                10,
                10 + height * 0.52,
                width,
                height * 0.40
            )

            font_cps = QFont()

            font_cps.setPixelSize(
                self.config["cps_font_size"]
            )

            font_cps.setBold(True)

            painter.setFont(
                font_cps
            )

            painter.drawText(
                bottom_rect,
                Qt.AlignCenter | Qt.AlignTop,
                cps_text
            )

        painter.end()

    # =====================================================
    # DRAGGING + CONTEXT MENU
    # =====================================================

    def mousePressEvent(self, event):

        # -------------------------------------------------
        # ЛЕВАЯ КНОПКА — ПЕРЕТАСКИВАНИЕ (по любой точке оверлея)
        # -------------------------------------------------
        if event.button() == Qt.LeftButton:

            self.dragging = True

            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            event.accept()
            return

        # -------------------------------------------------
        # ПРАВАЯ КНОПКА — МЕНЮ
        # -------------------------------------------------
        if event.button() == Qt.RightButton:

            self.show_context_menu(
                event.globalPosition().toPoint()
            )

            event.accept()
            return

    def mouseMoveEvent(self, event):

        if self.dragging and event.buttons() & Qt.LeftButton:

            self.move(
                event.globalPosition().toPoint()
                - self.drag_position
            )

            event.accept()

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.dragging = False

            event.accept()

    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        if self.isVisible():
            toggle_action = menu.addAction("Свернуть оверлей")
        else:
            toggle_action = menu.addAction("Развернуть оверлей")

        menu.addSeparator()

        close_action = menu.addAction("Закрыть программу")

        action = menu.exec(global_pos)

        if action == toggle_action:
            self.toggle_visibility()
        elif action == close_action:
            self.close_app()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    setup_crash_logging()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = load_config()

    window = KeyOverlay(config)
    window.show()

    sys.exit(app.exec())