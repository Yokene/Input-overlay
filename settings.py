import sys
import json
import os
import keyboard

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QSlider, QSpinBox, 
    QPushButton, QLineEdit, QMessageBox, QHBoxLayout, QDialog, 
    QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QPoint
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QPen, QIcon


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def resource_path(filename):
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

DEFAULT_CONFIG = {
    "key": "up",
    "text": "↑",
    "close_key": "f8",
    "settings_close_key": "f9",
    "width": 100,
    "height": 100,
    "corner_radius": 20,
    "border_width": 3,
    "normal_color": "#FFFFFF",
    "pressed_color": "#00FF00",
    "border_color": "#000000",
    "pressed_border_color": "#000000",
    "text_color": "#000000",
    "pressed_text_color": "#000000",
    "font_size": 40,
    "cps_font_size": 20
}




if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")


def load_stylesheet():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    qss_path = os.path.join(base_dir, "style.qss")

    try:
        with open(qss_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as error:
        print("Ошибка загрузки style.qss:", error)
        return ""


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    except Exception as error:
        print("Ошибка загрузки config.json:", error)
        return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4, ensure_ascii=False)
        return True
    except Exception as error:
        print("Ошибка сохранения:", error)
        return False


def normalize_hex_color(hex_str):
    """Приводит HEX-строку к валидному стандарту #RRGGBB или #RRGGBBAA"""
    hex_str = hex_str.strip()
    if not hex_str.startswith("#"):
        hex_str = "#" + hex_str

    cleaned = hex_str[1:]
    if len(cleaned) == 8:
        try:
            r = int(cleaned[0:2], 16)
            g = int(cleaned[2:4], 16)
            b = int(cleaned[4:6], 16)
            a = int(cleaned[6:8], 16)
            return f"#{r:02X}{g:02X}{b:02X}{a:02X}".upper()
        except ValueError:
            pass

    color = QColor(hex_str)
    if not color.isValid():
        return "#FFFFFF"

    if color.alpha() < 255:
        return f"#{color.red():02X}{color.green():02X}{color.blue():02X}{color.alpha():02X}".upper()
    
    return f"#{color.red():02X}{color.green():02X}{color.blue():02X}".upper()


# ============================================================
# Поток для назначения клавиши
# ============================================================

class KeyListenerThread(QThread):
    key_captured = Signal(str)

    def run(self):
        try:
            key = keyboard.read_key()
        except Exception:
            key = None

        if key:
            self.key_captured.emit(key)


# ============================================================
# Палитра цвета
# ============================================================

class ColorArea(QWidget):
    color_changed = Signal(QColor)

    def __init__(self, color=None):
        super().__init__()
        self.setMinimumSize(260, 220)
        self.setMouseTracking(True)

        self.hue = 0
        self.saturation = 1.0
        self.value = 1.0

        if color and color.isValid():
            self.setColor(color)

    def setColor(self, color):
        h, s, v, _ = color.getHsvF()
        if h < 0:
            h = 0
        self.hue = h
        self.saturation = s
        self.value = v
        self.update()

    def getColor(self):
        return QColor.fromHsvF(self.hue, self.saturation, self.value)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        base_color = QColor.fromHsvF(self.hue, 1.0, 1.0)

        gradient_white = QLinearGradient(rect.left(), 0, rect.right(), 0)
        gradient_white.setColorAt(0, QColor(255, 255, 255))
        gradient_white.setColorAt(1, base_color)
        painter.fillRect(rect, gradient_white)

        gradient_black = QLinearGradient(0, 0, 0, rect.height())
        gradient_black.setColorAt(0, QColor(0, 0, 0, 0))
        gradient_black.setColorAt(1, QColor(0, 0, 0, 255))
        painter.fillRect(rect, gradient_black)

        x = int(self.saturation * rect.width())
        y = int((1.0 - self.value) * rect.height())

        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(x, y), 6, 6)

        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(QPoint(x, y), 7, 7)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.update_from_mouse(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.update_from_mouse(event.position())

    def update_from_mouse(self, position):
        x = max(0, min(self.width(), position.x()))
        y = max(0, min(self.height(), position.y()))

        self.saturation = x / self.width()
        self.value = 1.0 - (y / self.height())
        self.update()
        self.color_changed.emit(self.getColor())


class HueSlider(QWidget):
    color_changed = Signal(float)

    def __init__(self, hue=0):
        super().__init__()
        self.hue = hue
        self.setFixedWidth(18)
        self.setMinimumHeight(220)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        gradient = QLinearGradient(0, 0, 0, rect.height())

        colors = [
            QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0),
            QColor(0, 255, 255), QColor(0, 0, 255), QColor(255, 0, 255),
            QColor(255, 0, 0)
        ]

        for i, color in enumerate(colors):
            gradient.setColorAt(i / 6, color)

        painter.fillRect(rect, gradient)

        y = int(self.hue * rect.height())
        painter.setPen(QPen(Qt.white, 2))
        painter.drawLine(0, y, rect.width(), y)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(0, y - 2, rect.width() - 1, 4)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.update_hue(event.position().y())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.update_hue(event.position().y())

    def update_hue(self, y):
        self.hue = max(0, min(1, y / self.height()))
        self.update()
        self.color_changed.emit(self.hue)


class BrightnessSlider(QWidget):
    value_changed = Signal(float)

    def __init__(self, value=1.0):
        super().__init__()
        self.value = value
        self.setFixedWidth(18)
        self.setMinimumHeight(220)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        gradient = QLinearGradient(0, 0, 0, rect.height())

        gradient.setColorAt(0, QColor(255, 255, 255))
        gradient.setColorAt(1, QColor(0, 0, 0))
        painter.fillRect(rect, gradient)

        y = int((1.0 - self.value) * rect.height())
        painter.setPen(QPen(Qt.white, 2))
        painter.drawLine(0, y, rect.width(), y)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(0, y - 2, rect.width() - 1, 4)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.update_value(event.position().y())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.update_value(event.position().y())

    def update_value(self, y):
        self.value = max(0.0, min(1.0, 1.0 - (y / self.height())))
        self.update()
        self.value_changed.emit(self.value)


class OpacitySlider(QWidget):
    value_changed = Signal(float)

    def __init__(self, value=1.0):
        super().__init__()
        self.value = value
        self.setFixedWidth(18)
        self.setMinimumHeight(220)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()

        square = 6
        for y in range(0, rect.height(), square):
            for x in range(0, rect.width(), square):
                color = QColor(230, 230, 230) if ((x // square) + (y // square)) % 2 == 0 else QColor(255, 255, 255)
                painter.fillRect(x, y, square, square, color)

        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 255))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(rect, gradient)

        y = int((1.0 - self.value) * rect.height())
        painter.setPen(QPen(Qt.white, 2))
        painter.drawLine(0, y, rect.width(), y)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(0, y - 2, rect.width() - 1, 4)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.update_value(event.position().y())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.update_value(event.position().y())

    def update_value(self, y):
        self.value = max(0.0, min(1.0, 1.0 - (y / self.height())))
        self.update()
        self.value_changed.emit(self.value)


# ============================================================
# Окно выбора цвета (с исправленной прозрачностью)
# ============================================================

class CustomColorDialog(QDialog):
    def __init__(self, initial_color="#FFFFFF", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор цвета")
        self.setModal(True)
        self.resize(470, 350)

        initial_color = initial_color.strip()
        if not initial_color.startswith("#"):
            initial_color = "#" + initial_color
            
        color = QColor(255, 255, 255, 255)
        sub = initial_color[1:]
        if len(sub) == 8:
            try:
                r = int(sub[0:2], 16)
                g = int(sub[2:4], 16)
                b = int(sub[4:6], 16)
                a = int(sub[6:8], 16)
                color = QColor(r, g, b, a)
            except ValueError:
                color = QColor(initial_color)
        else:
            color = QColor(initial_color)

        if not color.isValid():
            color = QColor("#FFFFFF")

        self.updating_hex = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        picker_layout = QHBoxLayout()
        picker_layout.setSpacing(8)

        self.color_area = ColorArea(color)
        picker_layout.addWidget(self.color_area, 1)

        self.hue_slider = HueSlider()
        picker_layout.addWidget(self.hue_slider)

        self.brightness_slider = BrightnessSlider()
        picker_layout.addWidget(self.brightness_slider)

        self.opacity_slider = OpacitySlider(color.alphaF())
        picker_layout.addWidget(self.opacity_slider)

        main_layout.addLayout(picker_layout)

        self.preview = QFrame()
        self.preview.setFixedHeight(35)
        main_layout.addWidget(self.preview)

        # Редактируемое поле ввода HEX-кода
        hex_container = QHBoxLayout()
        hex_container.addStretch()
        
        self.hex_input = QLineEdit()
        self.hex_input.setAlignment(Qt.AlignCenter)
        self.hex_input.setFixedWidth(120)
        self.hex_input.textChanged.connect(self.on_hex_text_edited)
        
        hex_container.addWidget(self.hex_input)
        hex_container.addStretch()
        main_layout.addLayout(hex_container)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        self.color_area.color_changed.connect(self.on_color_changed)
        self.hue_slider.color_changed.connect(self.on_hue_changed)
        self.brightness_slider.value_changed.connect(self.on_brightness_changed)
        self.opacity_slider.value_changed.connect(self.on_opacity_changed)

        h, s, v, _ = color.getHsvF()
        if h < 0:
            h = 0

        self.hue_slider.hue = h
        self.brightness_slider.value = v
        self.update_all()

    def on_hex_text_edited(self, text):
        if self.updating_hex:
            return

        cleaned = text.strip()
        if not cleaned.startswith("#"):
            cleaned = "#" + cleaned

        sub = cleaned[1:]
        color = QColor()
        
        if len(sub) == 8:
            try:
                r = int(sub[0:2], 16)
                g = int(sub[2:4], 16)
                b = int(sub[4:6], 16)
                a = int(sub[6:8], 16)
                color = QColor(r, g, b, a)
            except ValueError:
                pass
        else:
            color = QColor(cleaned)

        if color.isValid():
            self.updating_hex = True
            
            h, s, v, _ = color.getHsvF()
            if h < 0:
                h = 0
            
            self.color_area.setColor(color)
            self.hue_slider.hue = h
            self.brightness_slider.value = v
            self.opacity_slider.value = color.alphaF()
            
            self.color_area.update()
            self.hue_slider.update()
            self.brightness_slider.update()
            self.opacity_slider.update()
            self.update_preview_only_style()
            
            self.updating_hex = False

    def on_hue_changed(self, hue):
        self.hue_slider.hue = hue
        self.color_area.hue = hue
        self.update_all()

    def on_brightness_changed(self, value):
        self.color_area.value = value
        self.update_all()

    def on_opacity_changed(self, value):
        self.opacity_slider.value = value
        self.update_all()

    def on_color_changed(self, color):
        h, s, v, _ = color.getHsvF()
        if h < 0:
            h = 0
        self.hue_slider.hue = h
        self.brightness_slider.value = v
        self.update_all()

    def update_all(self):
        self.color_area.update()
        self.hue_slider.update()
        self.brightness_slider.update()
        self.opacity_slider.update()
        self.update_preview()

    def get_color(self):
        color = self.color_area.getColor()
        alpha = int(self.opacity_slider.value * 255)
        color.setAlpha(alpha)
        return color

    def update_preview(self):
        color = self.get_color()
        self.update_preview_only_style()
        
        if not self.updating_hex:
            self.updating_hex = True
            if color.alpha() == 255:
                hex_str = f"#{color.red():02X}{color.green():02X}{color.blue():02X}"
            else:
                hex_str = f"#{color.red():02X}{color.green():02X}{color.blue():02X}{color.alpha():02X}"
            self.hex_input.setText(hex_str)
            self.updating_hex = False

    def update_preview_only_style(self):
        color = self.get_color()
        rgba = f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha() / 255:.2f})"
        self.preview.setStyleSheet(
            f"QFrame {{ background-color: {rgba}; border: 1px solid #888888; border-radius: 5px; }}"
        )

    def get_result(self):
        color = self.get_color()
        if color.alpha() == 255:
            return f"#{color.red():02X}{color.green():02X}{color.blue():02X}"
        return f"#{color.red():02X}{color.green():02X}{color.blue():02X}{color.alpha():02X}"


# ============================================================
# Основное окно настроек
# ============================================================

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.config = load_config()
        self.listening = False
        self._key_threads = []

        self.qss_path = resource_path("style.qss")
        self.qss_last_modified = (
            os.path.getmtime(self.qss_path)
            if os.path.exists(self.qss_path)
            else 0
        )

        self.setWindowTitle("Input Overlay - Settings")

        icon_path = resource_path("settings.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1100, 520)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # КОЛОНКА 1: КЛАВИШИ
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        left_col.addWidget(QLabel("Клавиша overlay:"))
        self.key_input, self.key_button = self.create_key_row(left_col, self.config["key"])
        self.key_button.clicked.connect(lambda: self.start_key_capture(self.key_input, self.key_button))

        left_col.addWidget(QLabel("Клавиша закрытия overlay:"))
        self.close_key_input, self.close_key_button = self.create_key_row(left_col, self.config["close_key"])
        self.close_key_button.clicked.connect(lambda: self.start_key_capture(self.close_key_input, self.close_key_button))

        left_col.addWidget(QLabel("Клавиша закрытия настроек:"))
        self.settings_close_key_input, self.settings_close_key_button = self.create_key_row(left_col, self.config["settings_close_key"])
        self.settings_close_key_button.clicked.connect(lambda: self.start_key_capture(self.settings_close_key_input, self.settings_close_key_button))

        left_col.addWidget(QLabel("Текст на кнопке:"))
        self.text_input = QLineEdit()
        self.text_input.setText(self.config["text"])
        left_col.addWidget(self.text_input)
        left_col.addStretch()

        # КОЛОНКА 2: ПОЛЗУНКИ
        mid_col = QVBoxLayout()
        mid_col.setSpacing(10)

        self.width_slider = self.create_slider(mid_col, "Ширина", 30, 500, self.config["width"])
        self.height_slider = self.create_slider(mid_col, "Высота", 30, 500, self.config["height"])
        self.radius_slider = self.create_slider(mid_col, "Скругление", 0, 250, self.config["corner_radius"])
        self.border_slider = self.create_slider(mid_col, "Толщина рамки", 0, 30, self.config["border_width"])
        self.font_slider = self.create_slider(mid_col, "Размер символа", 10, 200, self.config["font_size"])
        self.cps_font_slider = self.create_slider(mid_col, "Размер числа CPS", 5, 150, self.config["cps_font_size"])
        mid_col.addStretch()

        # КОЛОНКА 3: ЦВЕТА
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        right_col.addWidget(QLabel("Цвета:"))
        self.normal_color_swatch, self.normal_hex_input = self.create_color_row(
            right_col, "Обычный цвет", "normal_color", self.choose_normal_color
        )
        self.pressed_color_swatch, self.pressed_hex_input = self.create_color_row(
            right_col, "Цвет при нажатии", "pressed_color", self.choose_pressed_color
        )
        self.border_color_swatch, self.border_hex_input = self.create_color_row(
            right_col, "Цвет рамки", "border_color", self.choose_border_color
        )
        self.pressed_border_color_swatch, self.pressed_border_hex_input = self.create_color_row(
            right_col, "Цвет рамки при нажатии", "pressed_border_color", self.choose_pressed_border_color
        )
        self.text_color_swatch, self.text_hex_input = self.create_color_row(
            right_col, "Цвет текста", "text_color", self.choose_text_color
        )
        self.pressed_text_color_swatch, self.pressed_text_hex_input = self.create_color_row(
            right_col, "Цвет текста при нажатии", "pressed_text_color", self.choose_pressed_text_color
        )

        right_col.addSpacing(10)

        right_col.addStretch()

        self.save_button = QPushButton("Сохранить настройки")
        self.save_button.setMinimumHeight(40)
        self.save_button.clicked.connect(self.save_settings)
        right_col.addWidget(self.save_button)

# Сборка
        main_layout.addLayout(left_col)
        main_layout.addLayout(mid_col)
        main_layout.addLayout(right_col)

        self.setLayout(main_layout)

        for widget in self.findChildren(QPushButton):
            widget.setCursor(Qt.PointingHandCursor)

        for widget in self.findChildren(QSlider):
            widget.setCursor(Qt.PointingHandCursor)

        for widget in self.findChildren(QSpinBox):
            widget.setCursor(Qt.PointingHandCursor)

        self.center_window()

    def check_qss(self):
        try:
            if not os.path.exists(self.qss_path):
                return

            modified = os.path.getmtime(self.qss_path)

            if modified != self.qss_last_modified:
                self.qss_last_modified = modified

                with open(self.qss_path, "r", encoding="utf-8") as file:
                    stylesheet = file.read()

                QApplication.instance().setStyleSheet(stylesheet)

                print("QSS обновлён")

        except Exception as error:
            print("Ошибка QSS:", error)

        # Закрытие
        self.close_timer = QTimer()
        self.close_timer.timeout.connect(self.check_close_key)
        self.close_timer.start(50)

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def check_close_key(self):
        if self.listening:
            return

        target_key = self.config.get("settings_close_key", "").strip()
        if not target_key or target_key == "...":
            return

        try:
            if keyboard.is_pressed(target_key):
                self.close_timer.stop()
                self.close()
        except Exception:
            pass

    def create_key_row(self, layout, value):
        row = QHBoxLayout()
        key_input = QLineEdit()
        key_input.setText(value)
        key_input.setPlaceholderText("Например: up, down, a, space")

        button = QPushButton("Назначить")
        button.setFixedWidth(100)

        row.addWidget(key_input)
        row.addWidget(button)
        layout.addLayout(row)
        return key_input, button

    def start_key_capture(self, line_edit, button):
        if self.listening:
            return

        self.listening = True
        button.setEnabled(False)

        line_edit.setText("...")
        line_edit.setFocus()
        line_edit.selectAll()

        thread = KeyListenerThread()
        thread.key_captured.connect(
            lambda key: self.on_key_captured(key, line_edit, button, thread)
        )
        self._key_threads.append(thread)
        thread.start()

    def on_key_captured(self, key, line_edit, button, thread):
        line_edit.setText(key)
        line_edit.deselect()
        button.setEnabled(True)
        self.listening = False

        if thread in self._key_threads:
            self._key_threads.remove(thread)

        thread.quit()
        thread.wait()
        thread.deleteLater()

    def create_slider(self, layout, name, minimum, maximum, value):
        layout.addWidget(QLabel(name))
        row = QHBoxLayout()

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(value)

        spin = QSpinBox()
        spin.setMinimum(minimum)
        spin.setMaximum(maximum)
        spin.setValue(value)
        spin.setFixedWidth(70)

        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)

        row.addWidget(slider)
        row.addWidget(spin)
        layout.addLayout(row)
        return slider

    def create_color_row(self, layout, name, config_key, on_click):
        row = QHBoxLayout()

        name_label = QLabel(name)
        name_label.setObjectName("colorName")
        name_label.setFixedWidth(210)

        initial_val = self.config.get(config_key, "#FFFFFF")

        hex_input = QLineEdit()
        hex_input.setText(initial_val)
        hex_input.setFixedWidth(85)

        swatch = QPushButton()
        swatch.setFixedSize(28, 28)
        swatch.setCursor(Qt.PointingHandCursor)
        swatch.setStyleSheet(self.swatch_style(initial_val))
        swatch.clicked.connect(on_click)

        hex_input.textChanged.connect(
            lambda text, k=config_key, s=swatch, inp=hex_input:
            self.on_hex_text_changed(text, k, s, inp)
        )

        row.addWidget(name_label)
        row.addWidget(hex_input)
        row.addStretch()
        row.addWidget(swatch)

        layout.addLayout(row)

        return swatch, hex_input

    def on_hex_text_changed(self, text, config_key, swatch, hex_input):
        cleaned = text.strip()
        if not cleaned.startswith("#"):
            cleaned = "#" + cleaned

        sub = cleaned[1:]
        color = QColor()
        if len(sub) == 8:
            try:
                r = int(sub[0:2], 16)
                g = int(sub[2:4], 16)
                b = int(sub[4:6], 16)
                a = int(sub[6:8], 16)
                color = QColor(r, g, b, a)
            except ValueError:
                pass
        else:
            color = QColor(cleaned)

        if color.isValid():
            formatted = normalize_hex_color(cleaned)
            self.config[config_key] = formatted
            swatch.setStyleSheet(self.swatch_style(formatted))

    def swatch_style(self, color):
        sub = color.strip()[1:]
        qcolor = QColor()
        if len(sub) == 8:
            try:
                r = int(sub[0:2], 16)
                g = int(sub[2:4], 16)
                b = int(sub[4:6], 16)
                a = int(sub[6:8], 16)
                qcolor = QColor(r, g, b, a)
            except ValueError:
                qcolor = QColor(color)
        else:
            qcolor = QColor(color)

        if not qcolor.isValid():
            qcolor = QColor("#FFFFFF")

        if qcolor.alpha() < 255:
            alpha = qcolor.alpha() / 255
            return f"""
                QPushButton {{
                    background-color: rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {alpha:.3f});
                    border: 1px solid #888888;
                    border-radius: 5px;
                }}
                QPushButton:hover {{ border: 1px solid #444444; }}
            """

        return f"""
            QPushButton {{
                background-color: {qcolor.name()};
                border: 1px solid #888888;
                border-radius: 5px;
            }}
            QPushButton:hover {{ border: 1px solid #444444; }}
        """

    def update_color_row(self, swatch, hex_input, color):
        formatted = normalize_hex_color(color)
        hex_input.blockSignals(True)
        hex_input.setText(formatted)
        hex_input.blockSignals(False)
        swatch.setStyleSheet(self.swatch_style(formatted))

    def choose_color(self, config_key, swatch, hex_input):
        current = self.config.get(config_key, "#FFFFFF")
        dialog = CustomColorDialog(current, self)

        if dialog.exec() == QDialog.Accepted:
            val = dialog.get_result()
            self.config[config_key] = val
            self.update_color_row(swatch, hex_input, val)

    def choose_normal_color(self):
        self.choose_color("normal_color", self.normal_color_swatch, self.normal_hex_input)

    def choose_pressed_color(self):
        self.choose_color("pressed_color", self.pressed_color_swatch, self.pressed_hex_input)

    def choose_border_color(self):
        self.choose_color("border_color", self.border_color_swatch, self.border_hex_input)

    def choose_pressed_border_color(self):
        self.choose_color("pressed_border_color", self.pressed_border_color_swatch, self.pressed_border_hex_input)

    def choose_text_color(self):
        self.choose_color("text_color", self.text_color_swatch, self.text_hex_input)

    def choose_pressed_text_color(self):
        self.choose_color("pressed_text_color", self.pressed_text_color_swatch, self.pressed_text_hex_input)

    def save_settings(self):
        key = self.key_input.text().strip()
        close_key = self.close_key_input.text().strip()
        settings_close_key = self.settings_close_key_input.text().strip()
        text = self.text_input.text()

        if not key or key == "...":
            QMessageBox.warning(self, "Ошибка", "Клавиша overlay не может быть пустой.")
            return

        if not close_key or close_key == "...":
            QMessageBox.warning(self, "Ошибка", "Клавиша закрытия overlay не может быть пустой.")
            return

        if not settings_close_key or settings_close_key == "...":
            QMessageBox.warning(self, "Ошибка", "Клавиша закрытия настроек не может быть пустой.")
            return

        if not text:
            QMessageBox.warning(self, "Ошибка", "Текст кнопки не может быть пустым.")
            return

        self.config["key"] = key
        self.config["close_key"] = close_key
        self.config["settings_close_key"] = settings_close_key
        self.config["text"] = text
        self.config["width"] = self.width_slider.value()
        self.config["height"] = self.height_slider.value()
        self.config["corner_radius"] = self.radius_slider.value()
        self.config["border_width"] = self.border_slider.value()
        self.config["font_size"] = self.font_slider.value()
        self.config["cps_font_size"] = self.cps_font_slider.value()

        self.config["normal_color"] = normalize_hex_color(self.normal_hex_input.text())
        self.config["pressed_color"] = normalize_hex_color(self.pressed_hex_input.text())
        self.config["border_color"] = normalize_hex_color(self.border_hex_input.text())
        self.config["pressed_border_color"] = normalize_hex_color(self.pressed_border_hex_input.text())
        self.config["text_color"] = normalize_hex_color(self.text_hex_input.text())
        self.config["pressed_text_color"] = normalize_hex_color(self.pressed_text_hex_input.text())

        if save_config(self.config):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.NoIcon)
            msg.setWindowTitle("Готово")
            msg.setText("Настройки сохранены!")
            msg.exec()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить config.json.")


# ============================================================
# Запуск
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Иконка приложения
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    icon_path = os.path.join(base_dir, "settings.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Загружаем стиль ДО создания окна
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Создаём окно только после загрузки стиля
    window = SettingsWindow()

    # Применяем стиль непосредственно к окну
    if stylesheet:
        window.setStyleSheet(stylesheet)

    window.show()

    sys.exit(app.exec())