# -*- coding: utf-8 -*-
# Плагин: Console Viewer
# Показывает окно с логами лаунчера в реальном времени.

PLUGIN_NAME = "Console Viewer"
PLUGIN_AUTHOR = "DreamyLauncherMega"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Открывает отдельное окно с логами лаунчера"

import sys
import io
import threading
from collections import deque


# Состояние плагина
_state = {
    "buffer": deque(maxlen=5000),   # храним последние 5000 строк
    "window": None,
    "original_stdout": None,
    "original_stderr": None,
}


# ============================================================
# Потокобезопасный "приёмник" для stdout/stderr
# ============================================================
class _TeeWriter(io.TextIOBase):
    """Дублирует вывод: и в оригинальный stream, и в буфер."""
    def __init__(self, original):
        super().__init__()
        self._original = original
        self._lock = threading.Lock()

    def write(self, text):
        if not text:
            return 0

        # Оригинал
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass

        # Буфер
        with self._lock:
            for line in text.split("\n"):
                if line.strip() or line == "":
                    _state["buffer"].append(line)

        return len(text)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass


# ============================================================
# Окно консоли (создаётся лениво)
# ============================================================
def _create_window():
    """Создаёт QDialog с QTextEdit и запускает обновление."""
    try:
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
            QCheckBox, QLabel
        )
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QFont, QColor
    except Exception as e:
        print(f"[ConsoleViewer] PyQt6 не доступен: {e}")
        return None

    dlg = QDialog()
    dlg.setWindowTitle("DreamyLauncherMega — Консоль")
    dlg.resize(900, 600)

    layout = QVBoxLayout(dlg)

    # Верхняя панель
    top = QHBoxLayout()

    autoscroll_cb = QCheckBox("Автопрокрутка")
    autoscroll_cb.setChecked(True)
    top.addWidget(autoscroll_cb)

    clear_btn = QPushButton("🧹 Очистить")
    top.addWidget(clear_btn)

    save_btn = QPushButton("💾 Сохранить")
    top.addWidget(save_btn)

    top.addStretch()

    status = QLabel("● Live")
    status.setStyleSheet("color: #6bff6b; font-weight: bold;")
    top.addWidget(status)

    layout.addLayout(top)

    # Текстовое поле
    viewer = QTextEdit()
    viewer.setReadOnly(True)
    viewer.setStyleSheet(
        "background-color: #0d1117; color: #c9d1d9; "
        "font-family: Consolas, 'Courier New', monospace; font-size: 12px;"
    )
    layout.addWidget(viewer, 1)

    _state["last_shown"] = 0

    def refresh():
        buf = list(_state["buffer"])
        if len(buf) == _state["last_shown"]:
            return
        # Обновляем всё (простой способ — можно оптимизировать)
        viewer.setPlainText("\n".join(buf))
        if autoscroll_cb.isChecked():
            sb = viewer.verticalScrollBar()
            sb.setValue(sb.maximum())
        _state["last_shown"] = len(buf)

    timer = QTimer(dlg)
    timer.timeout.connect(refresh)
    timer.start(500)   # обновление 2 раза в секунду
    refresh()

    def on_clear():
        _state["buffer"].clear()
        viewer.clear()
        _state["last_shown"] = 0

    def on_save():
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getSaveFileName(
            dlg, "Сохранить лог", "launcher_console.log",
            "Log files (*.log *.txt);;All files (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(_state["buffer"]))
            QMessageBox.information(dlg, "Готово", f"Сохранено:\n{path}")

    clear_btn.clicked.connect(on_clear)
    save_btn.clicked.connect(on_save)

    _state["window"] = dlg
    return dlg


# ============================================================
# API плагина
# ============================================================
def get_versions():
    """Плагин не добавляет версий."""
    return []


def install_version(version_id, ctx):
    return False


def on_launcher_start(ctx=None):
    """Вызывается при старте лаунчера. Открывает окно консоли."""
    try:
        # Сохраняем оригинальные потоки
        _state["original_stdout"] = sys.stdout
        _state["original_stderr"] = sys.stderr

        # Перехватываем stdout/stderr
        sys.stdout = _TeeWriter(_state["original_stdout"])
        sys.stderr = _TeeWriter(_state["original_stderr"])

        # Добавляем стартовое сообщение
        _state["buffer"].append("=== Console Viewer запущен ===")
        _state["buffer"].append("Все логи лаунчера выводятся здесь.")

        # Открываем окно
        dlg = _create_window()
        if dlg is None:
            return
        dlg.show()

    except Exception as e:
        # Не ломаем лаунчер, если плагин упадёт
        try:
            if _state["original_stdout"]:
                _state["original_stdout"].write(f"[ConsoleViewer] Ошибка: {e}\n")
        except Exception:
            pass


def on_launcher_exit(ctx=None):
    """Восстанавливает оригинальные потоки."""
    try:
        if _state["original_stdout"] is not None:
            sys.stdout = _state["original_stdout"]
        if _state["original_stderr"] is not None:
            sys.stderr = _state["original_stderr"]
    except Exception:
        pass