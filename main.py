import sys
import json
import os
import time
import keyboard

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QPen, QBrush, QFont, QColor
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF


# =========================================================
# CONFIG
# =========================================================

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


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

        self.setWindowTitle("Input Overlay")

        # -------------------------------------------------
        # ПРОЗРАЧНОЕ ОКНО
        # -------------------------------------------------

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True
        )

        self.setAttribute(
            Qt.WA_NoSystemBackground,
            True
        )

        # Не показывать окно на панели задач
        self.setAttribute(
            Qt.WA_ShowWithoutActivating,
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

        self.show()

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

            self.timer.stop()
            self.refresh_timer.stop()

            QApplication.quit()
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
            QPainter.CompositionMode_Source
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
    # DRAGGING
    # =====================================================

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.dragging = True

            self.drag_position = (
                event.globalPosition().toPoint()
                -
                self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):

        if self.dragging:

            self.move(
                event.globalPosition().toPoint()
                -
                self.drag_position
            )

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.dragging = False


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    config = load_config()

    window = KeyOverlay(config)

    sys.exit(app.exec())