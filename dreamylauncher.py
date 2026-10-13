# -*- coding: utf-8 -*-
# DreamyLauncherMega v9.0.5 — DreamUX Edition
# ============================================================
# АДАПТАЦИЯ ПОД DreamUX:
#  1. Рабочая папка берётся из DREAMY_HOME (vfs/disk1.vhd.data/home/dreamylauncher/)
#  2. Все пути (.minecraft, accounts.db, plugins/) — внутри DREAMY_HOME
#  3. Плагины лаунчера копируются из app-папки в home/plugins/
#  4. Логи пишутся в DREAMY_HOME/launcher_debug.log
# ============================================================

import sys
import os

# === DreamUX integration: рабочая папка ===
_LAUNCHER_HOME = os.environ.get("DREAMY_HOME")
if _LAUNCHER_HOME:
    os.makedirs(_LAUNCHER_HOME, exist_ok=True)
    os.chdir(_LAUNCHER_HOME)
# ==========================================

import time
import json
import zipfile
import shutil
import sqlite3
import urllib.request
import subprocess
import hashlib
import uuid as uuidlib
import re
import importlib.util
import traceback
from urllib.parse import urlencode
from pathlib import Path
import requests

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QGroupBox,
    QMessageBox, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QDialog, QDialogButtonBox, QFormLayout, QProgressBar,
    QSplashScreen, QFileDialog, QRadioButton, QButtonGroup,
    QSystemTrayIcon, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QPixmap, QColor, QFont, QPainter, QIcon, QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineDownloadRequest,
)

import minecraft_launcher_lib
from cryptography.fernet import Fernet


# ============================================================
# КОНСТАНТЫ
# ============================================================
PLUGIN_LOADER_URL = "https://raw.githubusercontent.com/dream-companyx/_plugin_loader.py/main/_plugin_loader.py"
BRIDGE_FILENAME = "_plugin_loader.py"
BRIDGE_API_VERSION = "1.0"

CURSEFORGE_LOADER_IDS = {
    "forge":    "1",
    "fabric":   "4",
    "quilt":    "5",
    "neoforge": "6",
}


# ============================================================
# ПУТИ (DreamUX Edition)
# ============================================================
if _LAUNCHER_HOME:
    HOME_DIR = Path(_LAUNCHER_HOME)
else:
    HOME_DIR = Path(__file__).parent

SCRIPT_DIR = Path(__file__).parent        # где лежит сам лаунчер (app-папка)
MINECRAFT_DIR = HOME_DIR / ".minecraft"   # игровые данные
ASSETS_DIR = HOME_DIR / "assets"
PLUGINS_DIR = HOME_DIR / "plugins"
BROWSER_DATA = HOME_DIR / "browser_data"
BROWSER_CACHE = HOME_DIR / "browser_cache"
MODLISTS_DIR = HOME_DIR / "modlists"
SNAPSHOTS_DIR = HOME_DIR / "snapshots"

for _d in (HOME_DIR, MINECRAFT_DIR, ASSETS_DIR, PLUGINS_DIR,
           BROWSER_DATA, BROWSER_CACHE, MODLISTS_DIR, SNAPSHOTS_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


# ============================================================
# ОТЛАДКА
# ============================================================
try:
    _DEBUG_LOG_PATH = HOME_DIR / "launcher_debug.log"
    _DEBUG_FILE = open(_DEBUG_LOG_PATH, "a", encoding="utf-8")
except Exception:
    _DEBUG_FILE = None


def _dlog(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    if _DEBUG_FILE:
        try:
            _DEBUG_FILE.write(line + "\n")
            _DEBUG_FILE.flush()
        except Exception:
            pass


def _install_excepthook():
    def _hook(t, v, tb):
        _dlog("===== UNHANDLED EXCEPTION =====")
        _dlog("".join(traceback.format_exception(t, v, tb)))
        sys.__excepthook__(t, v, tb)
    sys.excepthook = _hook


_install_excepthook()
_dlog("===== LAUNCHER START v9.0.5 (DreamUX Edition) =====")
_dlog(f"HOME_DIR = {HOME_DIR}")
_dlog(f"MINECRAFT_DIR = {MINECRAFT_DIR}")
_dlog(f"PLUGINS_DIR = {PLUGINS_DIR}")


# ============================================================
# СПИСКИ ВЕРСИЙ
# ============================================================
ALL_VANILLA_VERSIONS = [
    "1.0", "1.1", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5",
    "1.3.1", "1.3.2", "1.4.2", "1.4.4", "1.4.5", "1.4.6", "1.4.7",
    "1.5.1", "1.5.2", "1.6.1", "1.6.2", "1.6.4",
    "1.7.2", "1.7.3", "1.7.4", "1.7.5", "1.7.6", "1.7.7", "1.7.8", "1.7.9", "1.7.10",
    "1.8", "1.8.1", "1.8.2", "1.8.3", "1.8.4", "1.8.5", "1.8.6", "1.8.7", "1.8.8", "1.8.9",
    "1.9", "1.9.1", "1.9.2", "1.9.3", "1.9.4",
    "1.10", "1.10.1", "1.10.2", "1.11", "1.11.1", "1.11.2",
    "1.12", "1.12.1", "1.12.2", "1.13", "1.13.1", "1.13.2",
    "1.14", "1.14.1", "1.14.2", "1.14.3", "1.14.4",
    "1.15", "1.15.1", "1.15.2", "1.16", "1.16.1", "1.16.2", "1.16.3", "1.16.4", "1.16.5",
    "1.17", "1.17.1", "1.18", "1.18.1", "1.18.2",
    "1.19", "1.19.1", "1.19.2", "1.19.3", "1.19.4",
    "1.20", "1.20.1", "1.20.2", "1.20.3", "1.20.4", "1.20.5", "1.20.6",
    "1.21", "1.21.1", "1.21.2", "1.21.3", "1.21.4",
]

ALL_FORGE_VERSIONS = [
    "1.12.2-14.23.5.2859", "1.13.2-25.0.223", "1.14.4-28.2.26",
    "1.15.2-31.2.57", "1.16.1-32.0.108", "1.16.2-33.0.61",
    "1.16.3-34.1.42", "1.16.4-35.1.37", "1.16.5-36.2.39",
    "1.17.1-37.1.1", "1.18-38.0.17", "1.18.1-39.1.2", "1.18.2-40.2.21",
    "1.19-41.1.0", "1.19.1-42.0.9", "1.19.2-43.3.13", "1.19.3-44.1.23",
    "1.19.4-45.2.16", "1.20-46.0.14", "1.20.1-47.4.5", "1.20.2-48.1.0",
    "1.20.3-49.0.30", "1.20.4-49.0.30", "1.20.5-50.1.0", "1.20.6-50.1.0",
    "1.21-51.0.33", "1.21.1-52.1.3",
]

ALL_NEOFORGE_VERSIONS = [
    "1.20.2-20.2.88", "1.20.3-20.3.10", "1.20.4-20.4.237",
    "1.20.5-20.5.22", "1.20.6-20.6.119", "1.21-21.0.143", "1.21.1-21.1.115",
]


# ============================================================
# ХЕЛПЕРЫ
# ============================================================
def sanitize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "unnamed"


def parse_manifest(zip_path: Path) -> dict:
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            manifest_name = None
            for n in names:
                if n == "manifest.json" or n.endswith("/manifest.json"):
                    manifest_name = n
                    break
            if not manifest_name:
                return {"error": "manifest.json не найден"}
            data = json.loads(z.read(manifest_name).decode("utf-8"))
            if data.get("manifestType") != "minecraftModpack":
                return {"error": "Это не сборка Minecraft"}
            return data
    except zipfile.BadZipFile:
        return {"error": "Не ZIP-архив"}
    except Exception as e:
        return {"error": f"Ошибка чтения: {e}"}


# ============================================================
# БАЗА ДАННЫХ АККАУНТОВ
# ============================================================
class AccountDatabase:
    def __init__(self, db_path, key_path):
        self.db_path = Path(db_path)
        self.key_path = Path(key_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = self._load_or_create_key()
        self._init_db()

    def _load_or_create_key(self):
        if self.key_path.exists():
            with open(self.key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as f:
                f.write(key)
        return Fernet(key)

    def _encrypt(self, text):
        if text is None:
            return b""
        return self._fernet.encrypt(text.encode("utf-8"))

    def _decrypt(self, blob):
        if not blob:
            return ""
        try:
            return self._fernet.decrypt(blob).decode("utf-8")
        except Exception:
            return ""

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login_enc BLOB NOT NULL,
                password_enc BLOB,
                username TEXT,
                uuid TEXT,
                access_token BLOB,
                client_token BLOB,
                acc_type TEXT DEFAULT 'ely',
                last_used INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def add_account(self, login, password, username, uuid, access_token,
                    client_token, acc_type="ely"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        try:
            existing_id = None
            cur.execute("SELECT id, login_enc, acc_type FROM accounts")
            for row_id, login_enc, acc_t in cur.fetchall():
                if self._decrypt(login_enc) == login and (acc_t or "ely") == acc_type:
                    existing_id = row_id
                    break
            if existing_id:
                cur.execute("""
                    UPDATE accounts SET password_enc=?, username=?, uuid=?,
                        access_token=?, client_token=?, last_used=?
                    WHERE id=?
                """, (self._encrypt(password), username, uuid,
                      self._encrypt(access_token), self._encrypt(client_token),
                      int(time.time()), existing_id))
            else:
                cur.execute("""
                    INSERT INTO accounts
                    (login_enc, password_enc, username, uuid, access_token,
                     client_token, acc_type, last_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (self._encrypt(login), self._encrypt(password),
                      username, uuid, self._encrypt(access_token),
                      self._encrypt(client_token), acc_type, int(time.time())))
            conn.commit()
            return True
        except Exception as e:
            _dlog(f"[DB] {e}")
            return False
        finally:
            conn.close()

    def list_accounts(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, login_enc, username, acc_type FROM accounts ORDER BY last_used DESC")
        rows = cur.fetchall()
        conn.close()
        return [(r[0], self._decrypt(r[1]), r[2], r[3] or "ely") for r in rows]

    def get_account(self, login, acc_type="ely"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT login_enc, password_enc, username, uuid,
                   access_token, client_token, acc_type
            FROM accounts
        """)
        for row in cur.fetchall():
            if self._decrypt(row[0]) == login and (row[6] or "ely") == acc_type:
                conn.close()
                return {
                    "login": login,
                    "password": self._decrypt(row[1]),
                    "username": row[2],
                    "uuid": row[3],
                    "access_token": self._decrypt(row[4]),
                    "client_token": self._decrypt(row[5]),
                    "type": row[6] or "ely",
                }
        conn.close()
        return None

    def delete_account(self, login, acc_type="ely"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, login_enc, acc_type FROM accounts")
        for row_id, login_enc, acc_t in cur.fetchall():
            if self._decrypt(login_enc) == login and (acc_t or "ely") == acc_type:
                cur.execute("DELETE FROM accounts WHERE id=?", (row_id,))
                break
        conn.commit()
        conn.close()

    def touch_account(self, login, acc_type="ely"):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, login_enc, acc_type FROM accounts")
        for row_id, login_enc, acc_t in cur.fetchall():
            if self._decrypt(login_enc) == login and (acc_t or "ely") == acc_type:
                cur.execute("UPDATE accounts SET last_used=? WHERE id=?",
                            (int(time.time()), row_id))
                break
        conn.commit()
        conn.close()


# ============================================================
# ELY.BY
# ============================================================
def elyby_authenticate(login, password):
    r = requests.post(
        "https://authserver.ely.by/auth/authenticate",
        json={"username": login, "password": password,
              "clientToken": "DreamyLauncherMega", "requestUser": True},
        timeout=15
    )
    data = r.json()
    if r.status_code != 200:
        raise Exception(data.get("errorMessage", "Ошибка"))
    return {
        "username": data.get("selectedProfile", {}).get("name"),
        "uuid": data.get("selectedProfile", {}).get("id"),
        "access_token": data.get("accessToken"),
        "client_token": data.get("clientToken"),
    }


def elyby_refresh(access_token, client_token):
    r = requests.post(
        "https://authserver.ely.by/auth/refresh",
        json={"accessToken": access_token, "clientToken": client_token, "requestUser": True},
        timeout=15
    )
    data = r.json()
    if r.status_code != 200:
        raise Exception(data.get("errorMessage", "Ошибка обновления"))
    return {
        "username": data.get("selectedProfile", {}).get("name"),
        "uuid": data.get("selectedProfile", {}).get("id"),
        "access_token": data.get("accessToken"),
        "client_token": data.get("clientToken"),
    }


def tl_uuid_from_nickname(nickname: str) -> str:
    data = ("OfflinePlayer:" + nickname).encode("utf-8")
    digest = bytearray(hashlib.md5(data).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(uuidlib.UUID(bytes=bytes(digest)))


# ============================================================
# ВОРКЕРЫ
# ============================================================
class AuthlibSetupWorker(QThread):
    progress = pyqtSignal(str)
    done = pyqtSignal(bool)

    def __init__(self, minecraft_dir, parent=None):
        super().__init__(parent)
        self.minecraft_dir = Path(minecraft_dir)

    def run(self):
        authlib_path = self.minecraft_dir / "authlib-injector.jar"
        if authlib_path.exists():
            self.progress.emit("authlib-injector.jar уже установлен")
            self.done.emit(True)
            return
        self.progress.emit("Скачивание authlib-injector.jar...")
        try:
            api_url = "https://api.github.com/repos/yushijinhun/authlib-injector/releases/latest"
            req = urllib.request.Request(api_url,
                                          headers={"Accept": "application/vnd.github.v3+json"})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
            download_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(".jar"):
                    download_url = asset["browser_download_url"]
                    break
            if not download_url:
                self.done.emit(False)
                return
            urllib.request.urlretrieve(download_url, authlib_path)
            self.progress.emit("✅ authlib-injector.jar установлен")
            self.done.emit(True)
        except Exception as e:
            self.progress.emit(f"❌ {e}")
            self.done.emit(False)


class InstallWorker(QThread):
    done = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, target_dir, version_type, version_id, parent=None):
        super().__init__(parent)
        self.target_dir = str(target_dir)
        self.version_type = version_type
        self.version_id = version_id
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            callback = {
                "setStatus": lambda s: self.progress.emit(-1, s),
                "setProgress": lambda cur, total: self.progress.emit(
                    int(cur * 100 / total) if total else 0, ""
                ),
                "setMax": lambda m: None,
            }
            if self.version_type in ("forge", "neoforge"):
                minecraft_launcher_lib.forge.install_forge_version(
                    self.version_id, self.target_dir, callback=callback
                )
            elif self.version_type == "fabric":
                try:
                    minecraft_launcher_lib.fabric.install_fabric(
                        self.version_id, self.target_dir, callback=callback
                    )
                except Exception:
                    minecraft_launcher_lib.install.install_minecraft_version(
                        self.version_id, self.target_dir, callback=callback
                    )
            else:
                minecraft_launcher_lib.install.install_minecraft_version(
                    self.version_id, self.target_dir, callback=callback
                )
            if self._cancelled:
                self.error.emit("Отменено")
                return
            self.progress.emit(100, "Готово")
            self.done.emit(self.version_id)
        except PermissionError as pe:
            msg = str(pe)
            if "installer.jar" in msg and ("WinError 32" in msg or "не может получить доступ" in msg):
                time.sleep(2)
                self.done.emit(self.version_id)
            else:
                self.error.emit(str(pe))
        except Exception as e:
            self.error.emit(str(e))


class OverridesExtractWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, zip_path, out_dir, parent=None):
        super().__init__(parent)
        self.zip_path = Path(zip_path)
        self.out_dir = Path(out_dir)

    def run(self):
        try:
            with zipfile.ZipFile(self.zip_path, "r") as z:
                prefix = None
                for n in z.namelist():
                    if n.startswith("overrides/"):
                        prefix = "overrides/"
                        break
                    if "/overrides/" in n:
                        prefix = n.split("overrides/")[0] + "overrides/"
                        break
                if not prefix:
                    self.done.emit(True, "Нет папки overrides")
                    return
                self.out_dir.mkdir(parents=True, exist_ok=True)
                for n in z.namelist():
                    if not n.startswith(prefix):
                        continue
                    rel = n[len(prefix):]
                    if not rel:
                        continue
                    target = self.out_dir / rel
                    if n.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(n) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                self.done.emit(True, f"Overrides → {self.out_dir}")
        except Exception as e:
            _dlog(f"OverridesExtractWorker: {e}\n{traceback.format_exc()}")
            self.done.emit(False, f"Ошибка overrides: {e}")


class MinecraftLogReader(QThread):
    line_received = pyqtSignal(str)
    process_exited = pyqtSignal(int, bool, list)

    CRASH_MARKERS = (
        "exception in thread", "fatal", "a fatal error has occurred",
        "failed to start", "java.lang.", "net.minecraftforge.fml",
        "the game crashed", "minecraft has crashed", "outofmemoryerror",
        "modloadingexception", "mixin apply failed", "an exception was thrown",
    )

    def __init__(self, process, parent=None):
        super().__init__(parent)
        self._process = process
        self._log_lines = []
        self._stop = False

    def stop(self):
        self._stop = True

    def _decode(self, raw):
        for enc in ("utf-8", "cp1251", "latin-1"):
            try:
                return raw.decode(enc).rstrip("\r\n")
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace").rstrip("\r\n")

    def run(self):
        stream = self._process.stdout
        if stream is None:
            rc = self._process.wait()
            self.process_exited.emit(rc, False, [])
            return
        try:
            for raw in iter(stream.readline, b""):
                if self._stop:
                    break
                if not raw:
                    break
                line = self._decode(raw)
                self._log_lines.append(line)
                self.line_received.emit(line)
        finally:
            try:
                stream.close()
            except Exception:
                pass
        rc = self._process.wait()
        full_text = "\n".join(self._log_lines).lower()
        is_crash = rc != 0 or any(m in full_text for m in self.CRASH_MARKERS)
        self.process_exited.emit(rc, is_crash, list(self._log_lines))


class DownloadFileWorker(QThread):
    done = pyqtSignal(bool, str)
    progress = pyqtSignal(int, str)

    def __init__(self, url, dest_path, parent=None):
        super().__init__(parent)
        self.url = url
        self.dest_path = Path(dest_path)

    def run(self):
        try:
            self.dest_path.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "DreamyLauncherMega/9.0.5"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                chunk = 65536
                got = 0
                with open(self.dest_path, "wb") as f:
                    while True:
                        data = resp.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        got += len(data)
                        if total:
                            self.progress.emit(int(got * 100 / total),
                                                f"{got // 1024} КБ")
            self.done.emit(True, str(self.dest_path))
        except Exception as e:
            self.done.emit(False, str(e))


# ============================================================
# ДИАЛОГИ
# ============================================================
class InstallProgressDialog(QDialog):
    cancel_requested = pyqtSignal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Установка")
        self.setFixedSize(500, 180)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        self.title_label = QLabel(f"<b>{title}</b>")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        self.status_label = QLabel("Подготовка...")
        self.status_label.setStyleSheet("color: #a0b0c0; font-size: 12px;")
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        layout.addStretch()
        row = QHBoxLayout()
        row.addStretch()
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self._on_cancel)
        row.addWidget(self.cancel_btn)
        layout.addLayout(row)
        self._finished = False

    def _on_cancel(self):
        self.cancel_requested.emit()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Отмена...")

    def update_progress(self, value, status=""):
        if self._finished:
            return
        self.progress.setValue(max(0, min(100, value)))
        if status:
            self.status_label.setText(status)

    def mark_finished(self, success=True, error=""):
        self._finished = True
        if success:
            self.progress.setValue(100)
            self.status_label.setText("✅ Готово")
        else:
            self.status_label.setText(f"❌ {error[:200]}")
        QTimer.singleShot(600, self.accept)


class CreatePackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание сборки")
        self.setFixedSize(500, 380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("<b>Создать новую сборку</b>")
        title.setStyleSheet("font-size: 16px; color: #4a9eff;")
        layout.addWidget(title)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: MyForge1.20.1")
        form.addRow("Название:", self.name_input)

        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["Forge", "NeoForge", "Vanilla"])
        self.loader_combo.currentTextChanged.connect(self._on_loader_changed)
        form.addRow("Загрузчик:", self.loader_combo)

        self.mc_combo = QComboBox()
        self.mc_combo.currentTextChanged.connect(self._on_mc_changed)
        form.addRow("Версия игры:", self.mc_combo)

        self.loader_ver_combo = QComboBox()
        form.addRow("Версия загрузчика:", self.loader_ver_combo)

        layout.addLayout(form)

        info = QLabel(
            "Сборка создастся в .minecraft/versions/<Имя>/mods/\n"
            "Версия игры кэшируется в assets/versions/"
        )
        info.setStyleSheet("color: #8a9aaa; font-size: 11px; padding: 8px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("📥 Создать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_loader_changed("Forge")

    def _on_loader_changed(self, loader):
        self.mc_combo.clear()
        if loader == "Vanilla":
            self.mc_combo.addItems(reversed(ALL_VANILLA_VERSIONS))
        else:
            seen = set()
            for v in ALL_FORGE_VERSIONS:
                mc = v.split("-")[0]
                if mc not in seen:
                    seen.add(mc)
            self.mc_combo.addItems(sorted(seen, reverse=True))
        self._on_mc_changed(self.mc_combo.currentText())

    def _on_mc_changed(self, mc):
        self.loader_ver_combo.clear()
        loader = self.loader_combo.currentText()
        if loader == "Forge":
            for v in ALL_FORGE_VERSIONS:
                if v.startswith(mc + "-"):
                    self.loader_ver_combo.addItem(v)
        elif loader == "NeoForge":
            for v in ALL_NEOFORGE_VERSIONS:
                if v.startswith(mc + "-"):
                    self.loader_ver_combo.addItem(v)
        else:
            self.loader_ver_combo.addItem("—")

    def get_data(self):
        return {
            "name": sanitize_name(self.name_input.text()),
            "loader": self.loader_combo.currentText().lower(),
            "mc": self.mc_combo.currentText(),
            "loader_ver": self.loader_ver_combo.currentText(),
        }


class PluginWarningDialog(QDialog):
    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ Внимание: обнаружены плагины")
        self.setFixedSize(600, 500)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("⚠️  Внимание: обнаружены плагины")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffcc66;")
        layout.addWidget(title)

        desc = QLabel(
            "Плагины — это сторонний код, который выполняется внутри лаунчера.\n"
            "Он может:\n"
            "   • сломать лаунчер\n"
            "   • украсть ваши данные (аккаунты, токены)\n"
            "   • заразить компьютер\n\n"
            "Загружайте плагины только из доверенных источников."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #e0e8f0; padding: 10px; "
                           "background-color: #2f1e1e; border-radius: 6px;")
        layout.addWidget(desc)

        layout.addWidget(QLabel("<b>Активные плагины:</b>"))
        plugins_list = QListWidget()
        for p in plugins:
            plugins_list.addItem(f"• {p.get('file','?')} — {p.get('title','?')} "
                                 f"({p.get('author','?')})")
        plugins_list.setMaximumHeight(150)
        layout.addWidget(plugins_list)

        self.ack_cb = QCheckBox("Я понимаю риск и принимаю ответственность")
        self.ack_cb.stateChanged.connect(self._update_buttons)
        layout.addWidget(self.ack_cb)

        layout.addStretch()

        row = QHBoxLayout()
        row.addStretch()
        self.continue_btn = QPushButton("✅ Продолжить")
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.accept)
        row.addWidget(self.continue_btn)

        self.exit_btn = QPushButton("❌ Выход")
        self.exit_btn.clicked.connect(self.reject)
        row.addWidget(self.exit_btn)
        layout.addLayout(row)

    def _update_buttons(self):
        self.continue_btn.setEnabled(self.ack_cb.isChecked())


class ElyAuthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить аккаунт Ely.by")
        self.setFixedSize(420, 300)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Email или имя пользователя")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Пароль")
        form.addRow("Логин:", self.login_input)
        form.addRow("Пароль:", self.password_input)
        layout.addLayout(form)
        info = QLabel("🔒 Логин и пароль шифруются (Fernet/AES).\nUUID из Ely.by.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #8a9aaa; font-size: 11px; padding: 8px;")
        layout.addWidget(info)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_credentials(self):
        return self.login_input.text().strip(), self.password_input.text()


class DreamySplashScreen(QSplashScreen):
    def __init__(self):
        pm = QPixmap(600, 350)
        pm.fill(QColor("#4a9eff"))
        p = QPainter(pm)
        p.setPen(QColor("white"))
        p.setFont(QFont("Segoe UI", 42, QFont.Weight.Bold))
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "🌙\nDreamyLauncherMega")
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(pm.rect().adjusted(0, 180, 0, 0),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    "ЛАУНЧЕР ДЛЯ MINECRAFT")
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(pm.rect().adjusted(0, 0, -15, -15),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                    "v9.0.5 (DreamUX)")
        p.end()
        super().__init__(pm)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)


# ============================================================
# ГЛАВНОЕ ОКНО
# ============================================================
class DreamyLauncherMega(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DreamyLauncherMega v9.0.5 — DreamUX")
        self.setGeometry(100, 60, 1350, 850)
        self.setMinimumSize(1150, 750)

        self.script_dir = SCRIPT_DIR
        self.minecraft_dir = str(MINECRAFT_DIR)
        self.assets_dir = str(ASSETS_DIR)
        self.assets_versions_dir = ASSETS_DIR / "versions"

        self.mods_dir = MINECRAFT_DIR / "mods"
        self.mods_dir.mkdir(exist_ok=True)
        self.resourcepacks_dir = MINECRAFT_DIR / "resourcepacks"
        self.resourcepacks_dir.mkdir(exist_ok=True)
        self.shaderpacks_dir = MINECRAFT_DIR / "shaderpacks"
        self.shaderpacks_dir.mkdir(exist_ok=True)

        self.modlists_dir = MODLISTS_DIR
        self.markers_dir = self.modlists_dir / "installed"
        self.markers_dir.mkdir(exist_ok=True)
        self.archived_dir = self.modlists_dir / "archived"
        self.archived_dir.mkdir(exist_ok=True)
        self.modsets_file = self.modlists_dir / "modsets.json"
        self.last_version_file = self.modlists_dir / "last_version.json"

        self.plugins_dir = PLUGINS_DIR

        self.db = AccountDatabase(HOME_DIR / "accounts.db",
                                   HOME_DIR / "secret.key")

        self.ely_access_token = None
        self.ely_client_token = None
        self.ely_username = None
        self.ely_uuid = None
        self.current_acc_type = None

        self.mc_process = None
        self.mc_reader = None
        self.mc_log_buffer = []

        self._minimized_to_tray = False
        self.tray_icon = None
        self.sidebar_frame = None
        self._current_target_url = ""

        self.plugin_bridge = None
        self.plugins_available = False
        self._plugin_versions = []

        self.modsets = self._load_modsets()

        self.current_pack_zip = None
        self.current_pack_manifest = None
        self.pack_install_active = False
        self.pack_mods_queue = []
        self.pack_index = 0
        self.pack_installed_count = 0
        self.pack_skip_count = 0
        self.pack_folder_name = ""
        self.pack_mc_version = ""
        self.pack_modloader_id = ""

        self.pages = {}
        self.apply_styles()
        self._load_plugins()
        self._show_plugin_warning_if_needed()
        self.init_ui()
        self.refresh_accounts_combo()
        self.refresh_versions_combo()
        self._restore_last_version()
        self.refresh_modpacks_list()
        self.refresh_my_packs()
        self._setup_tray()

        self.pack_timer = QTimer(self)
        self.pack_timer.setSingleShot(True)
        self.pack_timer.timeout.connect(self._on_pack_mod_timeout)

    # ---------- API плагинов ----------
    def log(self, msg):
        if hasattr(self, "log_output"):
            self.log_output.append(msg)
        _dlog(msg)

    def get_minecraft_dir(self):
        return self.minecraft_dir

    def get_assets_dir(self):
        return self.assets_dir

    def get_script_dir(self):
        return str(self.script_dir)

    def get_current_account(self):
        if not self.current_acc_type:
            return None
        return {
            "login": self.current_acc_type,
            "username": self.ely_username,
            "uuid": self.ely_uuid,
            "type": self.current_acc_type,
        }

    def set_plugin_progress(self, value, status=""):
        if hasattr(self, "pack_progress") and self.pack_progress.isVisible():
            self.pack_progress.setValue(max(0, min(100, int(value))))
        if hasattr(self, "pack_status") and status:
            self.pack_status.setText(f"[Plugin] {status}")

    # ---------- Модсеты ----------
    def _load_modsets(self):
        if self.modsets_file.exists():
            try:
                with open(self.modsets_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                _dlog(f"modsets load: {e}")
        return {}

    def _save_modsets(self):
        try:
            with open(self.modsets_file, "w", encoding="utf-8") as f:
                json.dump(self.modsets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _dlog(f"modsets save: {e}")

    def _save_last_version(self, kind, vid, display):
        try:
            with open(self.last_version_file, "w", encoding="utf-8") as f:
                json.dump({
                    "kind": kind, "id": vid, "display": display,
                    "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _dlog(f"_save_last_version: {e}")

    def _restore_last_version(self):
        if not self.last_version_file.exists():
            return
        try:
            with open(self.last_version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        kind = data.get("kind"); vid = data.get("id")
        if not kind or not vid:
            return
        for i in range(self.version_combo.count()):
            if self.version_combo.itemData(i) == (kind, vid):
                self.version_combo.setCurrentIndex(i)
                return

    # ---------- Плагины ----------
    def _load_plugins(self):
        bridge_path = self.plugins_dir / BRIDGE_FILENAME
        if not bridge_path.exists():
            self.plugins_available = False
            return
        try:
            spec = importlib.util.spec_from_file_location("dreamy_plugin_loader", bridge_path)
            bridge = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bridge)
            if getattr(bridge, "BRIDGE_API_VERSION", None) != BRIDGE_API_VERSION:
                self.plugins_available = False
                return
            bridge.register(self)
            self.plugin_bridge = bridge
            self.plugins_available = True
            self._plugin_versions = bridge.get_all_versions()
            self.log(f"✅ Bridge загружен. Плагинов: {len(bridge.list_plugins())}")
        except Exception as e:
            _dlog(f"Bridge load: {e}\n{traceback.format_exc()}")
            self.plugins_available = False

    def _show_plugin_warning_if_needed(self):
        if not self.plugins_available:
            return
        ack = self.plugins_dir / ".acknowledged"
        if ack.exists():
            return
        plugins = self.plugin_bridge.list_plugins()
        if not plugins:
            return
        dlg = PluginWarningDialog(plugins, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        try:
            ack.write_text("acknowledged\n", encoding="utf-8")
        except Exception:
            pass

    # ---------- Стили ----------
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #1e2a3a; color: #e0e8f0;
                font-family: 'Segoe UI', 'Segoe UI Emoji', Arial, sans-serif; }
            QGroupBox { background-color: #243447; border: 1px solid #2f4157;
                border-radius: 6px; margin-top: 12px; padding: 10px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px;
                padding: 0 5px; color: #4a9eff; }
            QPushButton { background-color: #4a9eff; color: white;
                border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #5aaeff; }
            QPushButton:disabled { background-color: #3a4a5a; color: #7a8a9a; }
            QPushButton#SideButton { background-color: transparent; color: #c0d0e0;
                text-align: left; padding: 12px 20px; border-radius: 0;
                font-weight: normal; font-size: 13px; }
            QPushButton#SideButton:hover { background-color: #2f4157; color: white; }
            QPushButton#PlayButton { background-color: #f5a623; font-size: 16px;
                padding: 12px 40px; border-radius: 6px; }
            QPushButton#PlayButton:hover { background-color: #ffb733; }
            QComboBox, QLineEdit { background-color: #1a2634; border: 1px solid #2f4157;
                border-radius: 4px; padding: 6px 10px; color: #e0e8f0; }
            QComboBox:hover, QLineEdit:hover { border: 1px solid #4a9eff; }
            QListWidget { background-color: #1a2634; border: 1px solid #2f4157;
                border-radius: 4px; padding: 5px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2f4157;
                font-size: 13px; }
            QListWidget::item:selected { background-color: #4a9eff; color: white; }
            QTextEdit { background-color: #1a2634; border: 1px solid #2f4157;
                border-radius: 4px; padding: 8px; color: #a0b0c0;
                font-family: Consolas, monospace; font-size: 12px; }
            QLabel#Header { font-size: 20px; font-weight: bold; color: #4a9eff;
                padding: 5px 0; }
            QLabel#SubHeader { font-size: 13px; color: #8a9aaa; }
            QLabel#Logo { font-size: 26px; font-weight: bold; color: #f5a623; }
            QFrame#Sidebar { background-color: #1a2634; border-right: 1px solid #2f4157; }
            QFrame#BottomBar { background-color: #243447; border-top: 1px solid #2f4157; }
            QProgressBar { background-color: #1a2634; border: 1px solid #2f4157;
                border-radius: 4px; text-align: center; color: #e0e8f0;
                font-weight: bold; height: 22px; }
            QProgressBar::chunk { background-color: #4a9eff; border-radius: 3px; }
            QCheckBox { color: #e0e8f0; padding: 4px; }
        """)

    # ---------- UI ----------
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("background-color: #243447; border-bottom: 1px solid #2f4157;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(15, 0, 15, 0)

        self.sidebar_toggle_btn = QPushButton("☰")
        self.sidebar_toggle_btn.setFixedSize(40, 36)
        self.sidebar_toggle_btn.setStyleSheet(
            "background-color: transparent; color: #c0d0e0; "
            "font-size: 18px; border-radius: 4px;")
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        top_layout.addWidget(self.sidebar_toggle_btn)

        logo = QLabel("🌙 DreamyLauncherMega")
        logo.setObjectName("Logo")
        top_layout.addWidget(logo)
        top_layout.addStretch()

        tabs = [
            ("🏠", "Главная"), ("🧩", "Моды"), ("📦", "Сборки"),
            ("🎮", "Версии"), ("⚙", "Настройки")
        ]
        self.tab_buttons = {}
        for icon, name in tabs:
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            if name == "Главная":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, n=name: self.switch_tab(n))
            self.tab_buttons[name] = btn
            top_layout.addWidget(btn)

        main_layout.addWidget(top_bar)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        self.sidebar_frame = sidebar
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 20, 0, 20)
        sl.setSpacing(0)
        for icon, name in [("🏠","Главная"), ("🧩","Моды"), ("📦","Сборки"),
                            ("🎮","Версии"), ("⚙","Настройки"), ("❓","Помощь")]:
            btn = QPushButton(f"  {icon}   {name}")
            btn.setObjectName("SideButton")
            btn.clicked.connect(lambda checked, n=name: self.sidebar_action(n))
            sl.addWidget(btn)
        sl.addStretch()
        content_layout.addWidget(sidebar)

        self.page_container = QWidget()
        self.page_container_layout = QVBoxLayout(self.page_container)
        self.page_container_layout.setContentsMargins(20, 20, 20, 20)
        self.page_container_layout.setSpacing(15)

        self.pages["Главная"] = self.create_home_page()
        self.pages["Моды"] = self.create_mods_page()
        self.pages["Сборки"] = self.create_packs_page()
        self.pages["Версии"] = self.create_versions_page()
        self.pages["Настройки"] = self.create_settings_page()
        self.pages["Помощь"] = self.create_help_page()
        for page in self.pages.values():
            self.page_container_layout.addWidget(page)
        self.show_page("Главная")

        content_layout.addWidget(self.page_container, 1)
        main_layout.addLayout(content_layout, 1)

        bottom_bar = QFrame()
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(80)
        bl = QHBoxLayout(bottom_bar)
        bl.setContentsMargins(20, 8, 20, 8)

        acc_layout = QVBoxLayout()
        acc_layout.setSpacing(2)
        acc_layout.addWidget(QLabel("Аккаунт:"))
        self.account_combo = QComboBox()
        self.account_combo.setFixedWidth(180)
        self.account_combo.setFixedHeight(28)
        self.account_combo.currentIndexChanged.connect(self.on_account_switched)
        acc_layout.addWidget(self.account_combo)
        bl.addLayout(acc_layout)

        self.account_label = QLabel("🔴 Не авторизован")
        self.account_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        bl.addWidget(self.account_label)

        ver_layout = QVBoxLayout()
        ver_layout.setSpacing(2)
        ver_layout.addWidget(QLabel("Версия / Сборка:"))
        self.version_combo = QComboBox()
        self.version_combo.setFixedWidth(260)
        self.version_combo.setFixedHeight(28)
        self.version_combo.setMaxVisibleItems(30)
        ver_layout.addWidget(self.version_combo)
        bl.addLayout(ver_layout)

        bl.addStretch()

        self.play_btn = QPushButton("▶  Войти в игру")
        self.play_btn.setObjectName("PlayButton")
        self.play_btn.clicked.connect(self.launch_game)
        bl.addWidget(self.play_btn)

        main_layout.addWidget(bottom_bar)

        # ---------- БРАУЗЕР ----------
        self.browser_overlay = QWidget(self)
        self.browser_overlay.setStyleSheet("background-color: #1e2a3a;")
        self.browser_overlay.setVisible(False)
        ol = QVBoxLayout(self.browser_overlay)
        ol.setContentsMargins(8, 8, 8, 8)
        ol.setSpacing(6)
        nav = QHBoxLayout()
        nav.setSpacing(6)

        for label, slot in [("◀", lambda: self.browser.back()),
                             ("▶", lambda: self.browser.forward()),
                             ("⟳", lambda: self.browser.reload())]:
            b = QPushButton(label)
            b.setFixedSize(36, 30)
            b.clicked.connect(slot)
            nav.addWidget(b)

        self.btn_home_app = QPushButton("🏠 Домой")
        self.btn_home_app.setFixedHeight(30)
        self.btn_home_app.setStyleSheet(
            "background-color: #f5a623; color: white; border: none; "
            "border-radius: 4px; padding: 8px 16px; font-weight: bold;")
        self.btn_home_app.clicked.connect(self.close_browser_overlay)
        nav.addWidget(self.btn_home_app)

        self.btn_by_version = QPushButton("🎯 По выбранной версии")
        self.btn_by_version.setFixedHeight(30)
        self.btn_by_version.clicked.connect(self.open_browser_overlay)
        nav.addWidget(self.btn_by_version)

        nav.addStretch()
        self.download_status = QLabel("Загрузки → .minecraft")
        self.download_status.setStyleSheet("color: #8a9aaa; font-size: 12px;")
        nav.addWidget(self.download_status)
        ol.addLayout(nav)

        self.browser = QWebEngineView()
        try:
            profile = QWebEngineProfile("DreamyProfile", self.browser)
            profile.setPersistentStoragePath(str(BROWSER_DATA))
            profile.setCachePath(str(BROWSER_CACHE))
            profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            profile.setDownloadPath(str(self.mods_dir))
            profile.downloadRequested.connect(self.on_download_requested)
        except Exception as e:
            _dlog(f"Browser profile: {e}")
            profile = self.browser.page().profile()
            profile.setDownloadPath(str(self.mods_dir))
            profile.downloadRequested.connect(self.on_download_requested)

        self.browser.setUrl(QUrl("about:blank"))
        ol.addWidget(self.browser, 1)

        self.browser_overlay.setParent(self.centralWidget())
        self.browser_overlay.hide()

    def _toggle_sidebar(self):
        if self.sidebar_frame:
            self.sidebar_frame.setVisible(not self.sidebar_frame.isVisible())

    def switch_tab(self, name):
        for tn, btn in self.tab_buttons.items():
            btn.setChecked(tn == name)
        self.show_page(name)

    def sidebar_action(self, name):
        self.show_page(name)

    def show_page(self, name):
        if name not in self.pages:
            return
        for pn, p in self.pages.items():
            p.setVisible(pn == name)

    # ============================================================
    # СТРАНИЦЫ
    # ============================================================
    def create_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("🏠 Главная")
        header.setObjectName("Header")
        layout.addWidget(header)
        sub = QLabel("DreamyLauncherMega v9.0.5 (DreamUX) — Ely.by, Сборки, Плагины")
        sub.setObjectName("SubHeader")
        layout.addWidget(sub)
        layout.addSpacing(10)

        log_group = QGroupBox("📜 Журнал")
        ll = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        ll.addWidget(self.log_output)
        row = QHBoxLayout()
        b1 = QPushButton("🧹 Очистить")
        b1.clicked.connect(self.log_output.clear)
        row.addWidget(b1)
        b2 = QPushButton("💾 Сохранить")
        b2.clicked.connect(self.save_launcher_log)
        row.addWidget(b2)
        row.addStretch()
        ll.addLayout(row)
        log_group.setLayout(ll)
        layout.addWidget(log_group)

        console_group = QGroupBox("🖥 Консоль Minecraft")
        cl = QVBoxLayout()
        self.mc_console_view = QTextEdit()
        self.mc_console_view.setReadOnly(True)
        self.mc_console_view.setStyleSheet(
            "background-color:#0d1117; color:#c9d1d9; "
            "font-family: Consolas, monospace; font-size: 11px;")
        cl.addWidget(self.mc_console_view, 1)
        row = QHBoxLayout()
        b1 = QPushButton("🧹 Очистить")
        b1.clicked.connect(self.mc_console_view.clear)
        row.addWidget(b1)
        b2 = QPushButton("💾 Сохранить лог")
        b2.clicked.connect(self.save_mc_log)
        row.addWidget(b2)
        row.addStretch()
        cl.addLayout(row)
        console_group.setLayout(cl)
        layout.addWidget(console_group, 1)

        self.log("DreamyLauncherMega v9.0.5 (DreamUX Edition) готов.")
        return page

    def save_launcher_log(self):
        text = self.log_output.toPlainText() if hasattr(self, "log_output") else ""
        if not text.strip():
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить",
                                               "launcher.log", "Log (*.log *.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    def create_mods_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("🧩 Моды")
        header.setObjectName("Header")
        layout.addWidget(header)
        sub = QLabel("Браузер CurseForge. Скачанные вручную моды → .minecraft/mods/")
        sub.setObjectName("SubHeader")
        layout.addWidget(sub)
        layout.addSpacing(10)

        g = QGroupBox("Магазин модов")
        gl = QVBoxLayout()
        btn = QPushButton("🌐 Открыть браузер CurseForge")
        btn.setStyleSheet("background-color: #f5a623; font-size: 14px; "
                          "padding: 12px 24px; border-radius: 6px;")
        btn.clicked.connect(self.open_browser_overlay)
        gl.addWidget(btn)

        row = QHBoxLayout()
        b1 = QPushButton("📁 Открыть mods")
        b1.clicked.connect(lambda: self._open_folder(self.mods_dir))
        row.addWidget(b1)
        b2 = QPushButton("📁 Открыть resourcepacks")
        b2.clicked.connect(lambda: self._open_folder(self.resourcepacks_dir))
        row.addWidget(b2)
        gl.addLayout(row)
        g.setLayout(gl)
        layout.addWidget(g)
        layout.addStretch()
        return page

    def _open_folder(self, path):
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def create_packs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("📦 Сборки")
        header.setObjectName("Header")
        layout.addWidget(header)
        sub = QLabel("Создание сборок + установка ZIP (mods → versions/<Сборка>/mods/)")
        sub.setObjectName("SubHeader")
        layout.addWidget(sub)
        layout.addSpacing(6)

        g1 = QGroupBox("🎮 Мои сборки")
        g1l = QVBoxLayout()
        self.my_packs_widget = QListWidget()
        self.my_packs_widget.setMaximumHeight(130)
        g1l.addWidget(self.my_packs_widget)

        row = QHBoxLayout()
        btn_create = QPushButton("➕ Создать сборку")
        btn_create.setStyleSheet(
            "background-color: #f5a623; color: white; font-size: 13px; "
            "padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        btn_create.clicked.connect(self.create_pack_dialog)
        row.addWidget(btn_create)
        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.clicked.connect(self.refresh_my_packs)
        row.addWidget(btn_refresh)
        row.addStretch()
        g1l.addLayout(row)
        g1.setLayout(g1l)
        layout.addWidget(g1)

        g2 = QGroupBox("📥 Установка из ZIP (manifest.json)")
        g2l = QVBoxLayout()

        row = QHBoxLayout()
        b1 = QPushButton("🔄 Обновить ZIP")
        b1.clicked.connect(self.refresh_modpacks_list)
        row.addWidget(b1)
        b2 = QPushButton("📁 .minecraft")
        b2.clicked.connect(lambda: self._open_folder(self.minecraft_dir))
        row.addWidget(b2)
        row.addStretch()
        g2l.addLayout(row)

        self.packs_widget = QListWidget()
        self.packs_widget.setMaximumHeight(110)
        self.packs_widget.itemClicked.connect(self.on_pack_selected)
        g2l.addWidget(self.packs_widget)

        self.pack_info = QTextEdit()
        self.pack_info.setReadOnly(True)
        self.pack_info.setMaximumHeight(100)
        self.pack_info.setStyleSheet("background-color:#141b26; color:#a0b0c0;")
        self.pack_info.setPlainText("Выберите ZIP-сборку ↑")
        g2l.addWidget(self.pack_info)

        self.pack_mods_widget = QListWidget()
        self.pack_mods_widget.setMaximumHeight(110)
        g2l.addWidget(self.pack_mods_widget)

        row2 = QHBoxLayout()
        self.install_pack_btn = QPushButton("📥 Установить сборку")
        self.install_pack_btn.setStyleSheet(
            "background-color: #f5a623; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold;")
        self.install_pack_btn.setEnabled(False)
        self.install_pack_btn.clicked.connect(self.start_pack_install)
        row2.addWidget(self.install_pack_btn)

        self.delete_zip_btn = QPushButton("🗑 Удалить ZIP")
        self.delete_zip_btn.setEnabled(False)
        self.delete_zip_btn.clicked.connect(self.delete_selected_zip)
        row2.addWidget(self.delete_zip_btn)
        row2.addStretch()
        g2l.addLayout(row2)

        self.pack_progress = QProgressBar()
        self.pack_progress.setVisible(False)
        g2l.addWidget(self.pack_progress)

        self.pack_status = QLabel("")
        self.pack_status.setStyleSheet("color: #8a9aaa; font-size: 12px;")
        g2l.addWidget(self.pack_status)

        g2.setLayout(g2l)
        layout.addWidget(g2)

        return page

    # ---------- Мои сборки ----------
    def refresh_my_packs(self):
        self.my_packs_widget.clear()
        if not self.modsets:
            it = QListWidgetItem("(нет созданных сборок)")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.my_packs_widget.addItem(it)
            return
        for slug, meta in self.modsets.items():
            name = meta.get("name", slug)
            loader = meta.get("loader", "?")
            mc = meta.get("mc", "?")
            mods_dir = MINECRAFT_DIR / "versions" / slug / "mods"
            mods_count = len(list(mods_dir.glob("*.jar"))) if mods_dir.exists() else 0
            it = QListWidgetItem(f"🎮 {name}  |  {loader} {mc}  |  модов: {mods_count}")
            it.setData(Qt.ItemDataRole.UserRole, slug)
            self.my_packs_widget.addItem(it)

    def create_pack_dialog(self):
        dlg = CreatePackDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        name = data["name"]
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя сборки!")
            return
        if name in self.modsets:
            QMessageBox.warning(self, "Ошибка", "Сборка с таким именем уже существует!")
            return

        self.log(f"🎮 Создаю сборку: {name} ({data['loader']} {data['mc']})")

        if data["loader"] == "vanilla":
            ref_id = data["mc"]
            vtype = "vanilla"
        elif data["loader"] in ("forge", "neoforge"):
            ref_id = data["loader_ver"]
            vtype = data["loader"]
        else:
            QMessageBox.warning(self, "Ошибка", "Неизвестный загрузчик")
            return

        assets_ver_dir = self._find_assets_version_dir(ref_id)
        target_ver_dir = MINECRAFT_DIR / "versions" / name

        if target_ver_dir.exists():
            QMessageBox.warning(self, "Ошибка", f"Папка {target_ver_dir} уже существует!")
            return

        self.install_dialog = InstallProgressDialog(f"Создание сборки: {name}", self)

        if not assets_ver_dir.exists():
            self.log(f"⬇ Качаю {ref_id} в assets/...")
            self.install_worker = InstallWorker(self.assets_dir, vtype, ref_id, parent=self)
            self.install_worker.progress.connect(
                lambda v, s: self.install_dialog.update_progress(
                    v if v >= 0 else self.install_dialog.progress.value(), s))
            self.install_worker.done.connect(
                lambda r, t=target_ver_dir, n=name, d=data:
                    self._after_assets_install(t, n, d))
            self.install_worker.error.connect(self._on_pack_create_error)
            self.install_dialog.cancel_requested.connect(self.install_worker.cancel)
            self.install_worker.start()
            self.install_dialog.exec()
        else:
            self.log(f"✅ {ref_id} уже в assets/, копирую")
            self._after_assets_install(target_ver_dir, name, data)

    def _find_assets_version_dir(self, ref_id):
        avdir = self.assets_versions_dir
        if not avdir.exists():
            return avdir / ref_id

        exact = avdir / ref_id
        if exact.exists():
            return exact

        mc_ver = ref_id.split("-")[0]
        rest = ref_id[len(mc_ver)+1:] if len(ref_id) > len(mc_ver) else ""

        candidates = [
            f"{mc_ver}-forge-{rest}",
            f"forge-{mc_ver}-{rest}",
            f"{mc_ver}-neoforge-{rest}",
            f"neoforge-{mc_ver}-{rest}",
            f"{mc_ver}-{rest}",
        ]
        for c in candidates:
            p = avdir / c
            if p.exists():
                return p

        for p in avdir.iterdir():
            if not p.is_dir():
                continue
            n = p.name.lower()
            if mc_ver in n and rest and rest in n:
                return p
            if "forge" in n and mc_ver in n:
                return p

        return avdir / ref_id

    def _after_assets_install(self, target_ver_dir, name, data):
        try:
            if self.install_dialog:
                self.install_dialog.update_progress(80, "Копирую...")

            ref_id = data.get("loader_ver", data.get("mc", ""))
            source_dir = self._find_assets_version_dir(ref_id)
            if not source_dir.exists():
                raise Exception(f"Не найдена папка {source_dir} в assets/")

            if target_ver_dir.exists():
                raise Exception(f"Папка {target_ver_dir} уже существует")

            shutil.copytree(str(source_dir), str(target_ver_dir))

            for f in list(target_ver_dir.iterdir()):
                if f.is_file() and f.suffix == ".json":
                    self._rewrite_json_id(f, name)
                    new_path = target_ver_dir / f"{name}.json"
                    if f.exists() and f != new_path:
                        f.rename(new_path)
                elif f.is_file() and f.suffix == ".jar":
                    new_path = target_ver_dir / f"{name}.jar"
                    if f.exists() and f != new_path:
                        f.rename(new_path)

            (target_ver_dir / "mods").mkdir(exist_ok=True)

            self.modsets[name] = {
                "name": name,
                "loader": data["loader"],
                "loader_ver": data["loader_ver"],
                "mc": data["mc"],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "type": "custom",
            }
            self._save_modsets()

            self.refresh_my_packs()
            self.refresh_versions_combo()

            if self.install_dialog:
                self.install_dialog.update_progress(100, "Готово")
                self.install_dialog.mark_finished(success=True)

            self.log(f"✅ Сборка создана: {name}")
            QMessageBox.information(self, "Готово",
                                     f"Сборка «{name}» создана!\n\n"
                                     f"Моды кладите в:\n.minecraft/versions/{name}/mods/")
        except Exception as e:
            _dlog(f"_after_assets_install: {e}\n{traceback.format_exc()}")
            if self.install_dialog:
                self.install_dialog.mark_finished(success=False, error=str(e))
            QMessageBox.critical(self, "Ошибка", str(e))

    def _rewrite_json_id(self, json_path, new_id):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["id"] = new_id
            if "inheritsFrom" in data:
                parent = data["inheritsFrom"]
                if "forge" in parent.lower():
                    parts = parent.split("-")
                    if parts:
                        data["inheritsFrom"] = parts[0]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _dlog(f"rewrite_json_id: {e}")

    def _on_pack_create_error(self, error_msg):
        if self.install_dialog:
            self.install_dialog.mark_finished(success=False, error=error_msg)
        QMessageBox.critical(self, "Ошибка", error_msg)

    # ---------- ZIP ----------
    def refresh_modpacks_list(self):
        self.packs_widget.clear()
        try:
            zips = sorted(MINECRAFT_DIR.glob("*.zip"))
        except Exception:
            zips = []
        if not zips:
            it = QListWidgetItem("(нет ZIP-сборок в .minecraft/)")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.packs_widget.addItem(it)
            return
        for z in zips:
            size_mb = z.stat().st_size / (1024 * 1024)
            it = QListWidgetItem(f"📦 {z.name}  ({size_mb:.1f} МБ)")
            it.setData(Qt.ItemDataRole.UserRole, str(z))
            self.packs_widget.addItem(it)

    def on_pack_selected(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        self.current_pack_zip = Path(path)
        data = parse_manifest(self.current_pack_zip)
        if "error" in data:
            self.pack_info.setPlainText(f"❌ {data['error']}")
            self.pack_mods_widget.clear()
            self.install_pack_btn.setEnabled(False)
            self.delete_zip_btn.setEnabled(True)
            self.current_pack_manifest = None
            return
        self.current_pack_manifest = data
        mc = data.get("minecraft", {}).get("version", "?")
        ml_list = data.get("minecraft", {}).get("modLoaders", [])
        ml_id = ""
        for ml in ml_list:
            if ml.get("primary"):
                ml_id = ml.get("id", "")
                break
        if not ml_id and ml_list:
            ml_id = ml_list[0].get("id", "")
        files = data.get("files", [])
        name = data.get("name", self.current_pack_zip.stem)
        ver = data.get("version", "?")
        self.pack_info.setHtml(
            f"<b>Название:</b> {name}<br>"
            f"<b>Версия:</b> {ver}<br>"
            f"<b>MC:</b> {mc}<br>"
            f"<b>Загрузчик:</b> {ml_id or '—'}<br>"
            f"<b>Модов:</b> {len(files)}")
        self.pack_mods_widget.clear()
        for f in files:
            self.pack_mods_widget.addItem(
                f"📦 {f.get('projectID','?')}/{f.get('fileID','?')}")
        self.install_pack_btn.setEnabled(True)
        self.delete_zip_btn.setEnabled(True)

    def delete_selected_zip(self):
        if not self.current_pack_zip:
            return
        r = QMessageBox.question(self, "Удаление",
                                  f"Удалить {self.current_pack_zip.name}?",
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            self.current_pack_zip.unlink()
            self.current_pack_zip = None
            self.current_pack_manifest = None
            self.pack_info.setPlainText("ZIP удалён.")
            self.pack_mods_widget.clear()
            self.install_pack_btn.setEnabled(False)
            self.delete_zip_btn.setEnabled(False)
            self.refresh_modpacks_list()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    # ============================================================
    # УСТАНОВКА ZIP-СБОРКИ
    # ============================================================
    def start_pack_install(self):
        _dlog("start_pack_install: entered")
        try:
            if not self.current_pack_zip or not self.current_pack_manifest:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите ZIP-сборку.")
                return
            if self.pack_install_active:
                return

            m = self.current_pack_manifest
            name_raw = m.get("name", self.current_pack_zip.stem)
            ver = m.get("version", "")

            folder_name = sanitize_name(
                f"{name_raw}-{ver}" if ver else name_raw
            )
            if not folder_name:
                folder_name = sanitize_name(self.current_pack_zip.stem)
            self.pack_folder_name = folder_name

            mc = m.get("minecraft", {}).get("version", "")
            ml_list = m.get("minecraft", {}).get("modLoaders", [])
            ml_id = ""
            for ml in ml_list:
                if ml.get("primary"):
                    ml_id = ml.get("id", "")
                    break
            if not ml_id and ml_list:
                ml_id = ml_list[0].get("id", "")

            self.pack_mc_version = mc
            self.pack_modloader_id = ml_id

            loader = "vanilla"
            ref_id = mc
            vtype = "vanilla"
            if ml_id.startswith("forge-"):
                loader = "forge"
                ref_id = f"{mc}-{ml_id[len('forge-'):]}"
                vtype = "forge"
            elif ml_id.startswith("neoforge-"):
                loader = "neoforge"
                ref_id = f"{mc}-{ml_id[len('neoforge-'):]}"
                vtype = "neoforge"

            self.pack_install_active = True
            self.install_pack_btn.setEnabled(False)
            self.pack_progress.setVisible(True)
            self.pack_progress.setRange(0, 100)
            self.pack_progress.setValue(0)

            self.pack_mods_queue = [
                (f.get("projectID"), f.get("fileID"))
                for f in m.get("files", [])
            ]
            self.pack_index = 0
            self.pack_installed_count = 0
            self.pack_skip_count = 0

            self.log(f"📥 Установка: {folder_name}")
            self.log(f"   MC={mc}, loader={ref_id}, модов={len(self.pack_mods_queue)}")

            version_dir = MINECRAFT_DIR / "versions" / folder_name
            version_dir.mkdir(parents=True, exist_ok=True)
            (version_dir / "mods").mkdir(exist_ok=True)

            self._pack_current = {
                "folder_name": folder_name,
                "name_raw": name_raw,
                "ver": ver,
                "mc": mc,
                "loader": loader,
                "loader_ver": ref_id,
                "ref_id": ref_id,
                "vtype": vtype,
                "target_ver_dir": version_dir,
            }

            assets_ver_dir = self._find_assets_version_dir(ref_id)
            if not assets_ver_dir.exists():
                self.log(f"⬇ Качаю {ref_id} в assets/...")
                self.pack_dialog = InstallProgressDialog(f"Установка базы: {ref_id}", self)
                self.pack_worker = InstallWorker(self.assets_dir, vtype, ref_id, parent=self)
                self.pack_worker.progress.connect(
                    lambda v, s: self.pack_dialog.update_progress(
                        v if v >= 0 else self.pack_dialog.progress.value(), s))
                self.pack_worker.done.connect(self._after_assets_for_zip)
                self.pack_worker.error.connect(self._on_pack_error)
                self.pack_dialog.cancel_requested.connect(self.pack_worker.cancel)
                self.pack_worker.start()
                self.pack_dialog.exec()
            else:
                self._after_assets_for_zip(ref_id)
        except Exception as e:
            _dlog(f"start_pack_install FATAL: {e}\n{traceback.format_exc()}")
            self.pack_install_active = False
            self.install_pack_btn.setEnabled(True)
            QMessageBox.critical(self, "Ошибка установки", f"{e}")

    def _after_assets_for_zip(self, ref_id):
        try:
            cur = self._pack_current
            assets = self._find_assets_version_dir(ref_id)
            target = cur["target_ver_dir"]
            folder_name = cur["folder_name"]

            if not assets.exists():
                raise Exception(f"{assets} не существует")

            if not (target / f"{folder_name}.json").exists():
                for f in list(assets.iterdir()):
                    if f.is_file():
                        if f.suffix == ".json":
                            self._rewrite_json_id(f, folder_name)
                            shutil.copy2(str(f), str(target / f"{folder_name}.json"))
                        elif f.suffix == ".jar":
                            shutil.copy2(str(f), str(target / f"{folder_name}.jar"))
                        else:
                            shutil.copy2(str(f), str(target / f.name))
                    elif f.is_dir() and f.name not in ("mods", "resourcepacks", "shaderpacks", "saves"):
                        dst = target / f.name
                        if not dst.exists():
                            shutil.copytree(str(f), str(dst))

            self.pack_status.setText("Распаковка overrides...")
            self._extract_overrides_sync(self.current_pack_zip, target)

            self.modsets[folder_name] = {
                "name": cur["name_raw"],
                "version": cur["ver"],
                "mc": cur["mc"],
                "loader": cur["loader"],
                "loader_ver": ref_id,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "type": "zip",
            }
            self._save_modsets()
            self.refresh_my_packs()
            self.refresh_versions_combo()

            total = len(self.pack_mods_queue)
            self.pack_progress.setRange(0, total)
            self.pack_progress.setValue(0)
            self.log(f"▶ Скачивание модов: {total}")
            QTimer.singleShot(300, self._process_next_pack_mod)
        except Exception as e:
            _dlog(f"_after_assets_for_zip: {e}\n{traceback.format_exc()}")
            self._on_pack_error(str(e))

    def _extract_overrides_sync(self, zip_path, target_dir):
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                prefix = None
                for n in z.namelist():
                    if n.startswith("overrides/"):
                        prefix = "overrides/"
                        break
                    if "/overrides/" in n:
                        prefix = n.split("overrides/")[0] + "overrides/"
                        break
                if not prefix:
                    self.log("⚠️ Нет overrides в ZIP")
                    return
                target_dir.mkdir(parents=True, exist_ok=True)
                for n in z.namelist():
                    if not n.startswith(prefix):
                        continue
                    rel = n[len(prefix):]
                    if not rel:
                        continue
                    target = target_dir / rel
                    if n.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(n) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                self.log(f"✅ Overrides → {target_dir}")
        except Exception as e:
            _dlog(f"Overrides: {e}")

    def _process_next_pack_mod(self):
        try:
            if not self.pack_install_active:
                return
            if self.pack_index >= len(self.pack_mods_queue):
                self._finish_pack_install()
                return

            try:
                self.browser.stop()
                self.browser.setUrl(QUrl("about:blank"))
            except Exception:
                pass

            pid, fid = self.pack_mods_queue[self.pack_index]
            total = len(self.pack_mods_queue)
            self.pack_status.setText(f"→ {self.pack_index + 1}/{total}: {pid}/{fid}")

            url = f"https://www.curseforge.com/projects/{pid}/files/{fid}"
            self._current_target_url = url
            self.log(f"→ [{self.pack_index + 1}/{total}] {url}")

            self.browser.setUrl(QUrl(url))
            self._show_overlay_for_pack()

            QTimer.singleShot(3000, self._auto_click_download)
        except Exception as e:
            _dlog(f"queue: {e}\n{traceback.format_exc()}")

    def _show_overlay_for_pack(self):
        try:
            self.browser_overlay.setGeometry(self.centralWidget().rect())
            self.browser_overlay.raise_()
            self.browser_overlay.show()
        except Exception:
            pass

    def _auto_click_download(self):
        try:
            if not self.pack_install_active:
                return
            js = """
            (function() {
                let all = document.querySelectorAll('a, button');
                for (let b of all) {
                    let t = (b.textContent || '').trim().toLowerCase();
                    if (t === 'download' || t.startsWith('download ')) {
                        b.click();
                        return 'clicked:' + t;
                    }
                }
                let links = document.querySelectorAll('a[href*="/download/"]');
                if (links.length > 0) {
                    links[0].click();
                    return 'clicked-link';
                }
                return 'not-found';
            })();
            """
            self.browser.page().runJavaScript(js, self._on_auto_click_result)
        except Exception as e:
            _dlog(f"_auto_click_download: {e}")

    def _on_auto_click_result(self, result):
        _dlog(f"auto_click: {result}")
        if result and "clicked" in str(result):
            self.log(f"✅ Автоклик: {result}")
            if self.pack_timer:
                self.pack_timer.stop()
                self.pack_timer.start(15000)
        else:
            self.log(f"⚠️ Кнопка Download не найдена, ждём 8 сек")
            if self.pack_timer:
                self.pack_timer.stop()
                self.pack_timer.start(8000)

    def _on_download_finished_for_pack(self, target):
        try:
            if self.pack_install_active:
                if self.pack_timer:
                    self.pack_timer.stop()
                self.pack_index += 1
                self.pack_installed_count += 1
                self.pack_progress.setValue(self.pack_index)
                self.log(f"✅ Скачано: {target.name}")
                QTimer.singleShot(500, self._process_next_pack_mod)
        except Exception as e:
            _dlog(f"pack_dl_finished: {e}")

    def _on_pack_mod_timeout(self):
        try:
            if not self.pack_install_active:
                return
            if self.pack_index >= len(self.pack_mods_queue):
                return
            pid, fid = self.pack_mods_queue[self.pack_index]
            self.log(f"⏱ Таймаут: {pid}/{fid} — пропуск")
            self.pack_index += 1
            self.pack_skip_count += 1
            self.pack_progress.setValue(self.pack_index)
            QTimer.singleShot(500, self._process_next_pack_mod)
        except Exception as e:
            _dlog(f"timeout: {e}")

    def _finish_pack_install(self, aborted=False):
        if self.pack_timer:
            self.pack_timer.stop()
        if not self.pack_install_active:
            return
        self.pack_install_active = False
        self.install_pack_btn.setEnabled(True)

        try:
            self.browser.stop()
            self.browser.setUrl(QUrl("about:blank"))
            self.browser_overlay.hide()
        except Exception:
            pass

        if aborted:
            self.pack_status.setText("⏹ Остановлено")
            return

        try:
            slug = self.pack_folder_name or "pack"
            marker = {
                "pack_slug": slug,
                "pack_name": (self.current_pack_manifest or {}).get("name", slug),
                "pack_version": (self.current_pack_manifest or {}).get("version", ""),
                "mc_version": self.pack_mc_version,
                "modloader": self.pack_modloader_id,
                "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "mods_total": len(self.pack_mods_queue),
                "mods_installed": self.pack_installed_count,
                "mods_skipped": self.pack_skip_count,
            }
            marker_path = self.markers_dir / f"{slug}.json"
            with open(marker_path, "w", encoding="utf-8") as f:
                json.dump(marker, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"⚠️ Маркер: {e}")

        self.pack_progress.setValue(self.pack_progress.maximum())
        self.pack_status.setText(
            f"✅ Готово: модов {self.pack_installed_count}, пропущено {self.pack_skip_count}")
        self.log(f"✅ Установлено. Модов: {self.pack_installed_count}, "
                 f"пропущено: {self.pack_skip_count}")

        QMessageBox.information(
            self, "Готово",
            f"Сборка установлена!\n\n"
            f"Модов: {self.pack_installed_count}\n"
            f"Пропущено: {self.pack_skip_count}\n"
            f"Папка: versions/{self.pack_folder_name}/")

        self.install_pack_btn.setEnabled(False)
        self.delete_zip_btn.setEnabled(False)
        self.refresh_modpacks_list()

    def stop_pack_install(self):
        r = QMessageBox.question(self, "Остановить?",
                                  "Прервать установку?",
                                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self._finish_pack_install(aborted=True)

    def _on_pack_error(self, error_msg):
        if hasattr(self, "pack_dialog") and self.pack_dialog:
            self.pack_dialog.mark_finished(success=False, error=error_msg)
        self.pack_install_active = False
        self.install_pack_btn.setEnabled(True)
        QMessageBox.critical(self, "Ошибка", error_msg)

    # ---------- Версии ----------
    def create_versions_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("🎮 Версии Minecraft")
        header.setObjectName("Header")
        layout.addWidget(header)
        sub = QLabel("Установка в .minecraft/versions/ напрямую.")
        sub.setObjectName("SubHeader")
        layout.addWidget(sub)
        layout.addSpacing(15)

        g = QGroupBox("Доступные версии")
        gl = QVBoxLayout()
        row = QHBoxLayout()
        self.radio_vanilla = QRadioButton("Vanilla")
        self.radio_forge = QRadioButton("Forge")
        self.radio_neoforge = QRadioButton("NeoForge")
        self.radio_vanilla.setChecked(True)
        grp = QButtonGroup(self)
        for b in [self.radio_vanilla, self.radio_forge, self.radio_neoforge]:
            grp.addButton(b)
            row.addWidget(b)
        row.addStretch()
        gl.addLayout(row)

        self.vv_combo = QComboBox()
        self.vv_combo.setMaxVisibleItems(30)
        gl.addWidget(QLabel("Выберите версию:"))
        gl.addWidget(self.vv_combo)
        self._fill_versions("vanilla")

        self.radio_vanilla.toggled.connect(lambda c: self._fill_versions("vanilla") if c else None)
        self.radio_forge.toggled.connect(lambda c: self._fill_versions("forge") if c else None)
        self.radio_neoforge.toggled.connect(lambda c: self._fill_versions("neoforge") if c else None)

        btn = QPushButton("📥 Скачать / установить")
        btn.clicked.connect(self.install_selected_version)
        gl.addWidget(btn)
        g.setLayout(gl)
        layout.addWidget(g)
        layout.addStretch()
        return page

    def _fill_versions(self, mode):
        self.vv_combo.clear()
        if mode == "vanilla":
            self.vv_combo.addItems([f"Vanilla {v}" for v in reversed(ALL_VANILLA_VERSIONS)])
        elif mode == "forge":
            self.vv_combo.addItems([f"Forge {v}" for v in reversed(ALL_FORGE_VERSIONS)])
        else:
            self.vv_combo.addItems([f"NeoForge {v}" for v in reversed(ALL_NEOFORGE_VERSIONS)])

    def install_selected_version(self):
        selected = self.vv_combo.currentText()
        if selected.startswith("Forge "):
            vid = selected[len("Forge "):].strip()
            vtype = "forge"
        elif selected.startswith("NeoForge "):
            vid = selected[len("NeoForge "):].strip()
            vtype = "neoforge"
        elif selected.startswith("Vanilla "):
            vid = selected[len("Vanilla "):].strip()
            vtype = "vanilla"
        else:
            return
        self.log(f"Установка {vid} ({vtype})")
        self.v_dialog = InstallProgressDialog(f"{selected}", self)
        self.v_worker = InstallWorker(self.minecraft_dir, vtype, vid, parent=self)
        self.v_worker.progress.connect(
            lambda v, s: self.v_dialog.update_progress(
                v if v >= 0 else self.v_dialog.progress.value(), s))
        self.v_worker.done.connect(self._on_version_installed)
        self.v_worker.error.connect(self._on_version_error)
        self.v_dialog.cancel_requested.connect(self.v_worker.cancel)
        self.v_worker.start()
        self.v_dialog.exec()

    def _on_version_installed(self, result):
        if self.v_dialog:
            self.v_dialog.mark_finished(success=True)
        self.log(f"✅ Установлено: {result}")
        self.refresh_versions_combo()

    def _on_version_error(self, error_msg):
        if self.v_dialog:
            self.v_dialog.mark_finished(success=False, error=error_msg)
        QMessageBox.critical(self, "Ошибка", error_msg)

    # ---------- Комбобокс версий ----------
    def refresh_versions_combo(self):
        self.version_combo.clear()

        versions_dir = MINECRAFT_DIR / "versions"
        for slug, meta in self.modsets.items():
            if (versions_dir / slug).exists():
                self.version_combo.addItem(f"🎮 {meta.get('name', slug)}", ("modset", slug))

        for v in self._plugin_versions:
            vid = v.get("id", "")
            self.version_combo.addItem(f"[PLUGIN] {v.get('name', vid)}", ("plugin", vid))

        installed = []
        if versions_dir.exists():
            installed = sorted([p.name for p in versions_dir.iterdir() if p.is_dir()])
        seen = set()
        for name in installed:
            if name in self.modsets:
                continue
            low = name.lower()
            if "forge" in low and "neoforge" not in low:
                if name not in seen:
                    self.version_combo.addItem(f"Forge {name}", ("forge", name))
                    seen.add(name)
            elif "neoforge" in low:
                if name not in seen:
                    self.version_combo.addItem(f"NeoForge {name}", ("neoforge", name))
                    seen.add(name)
            elif "fabric" in low:
                if name not in seen:
                    self.version_combo.addItem(f"Fabric {name}", ("fabric", name))
                    seen.add(name)
            else:
                if name not in seen:
                    self.version_combo.addItem(f"Vanilla {name}", ("vanilla", name))
                    seen.add(name)

        if self.version_combo.count() == 0:
            self.version_combo.addItem("(нет версий)", None)

    # ---------- Настройки ----------
    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("⚙ Настройки")
        header.setObjectName("Header")
        layout.addWidget(header)
        layout.addSpacing(10)

        acc_group = QGroupBox("👤 Аккаунты Ely.by")
        al = QVBoxLayout()
        row = QHBoxLayout()
        b1 = QPushButton("➕ Добавить")
        b1.clicked.connect(self.add_account)
        row.addWidget(b1)
        row.addStretch()
        al.addLayout(row)
        acc_group.setLayout(al)
        layout.addWidget(acc_group)

        mem_group = QGroupBox("💾 Память")
        ml = QVBoxLayout()
        ml.addWidget(QLabel("Xmx:"))
        self.ram_input = QLineEdit("4G")
        ml.addWidget(self.ram_input)
        ml.addWidget(QLabel("Xms:"))
        self.ram_min_input = QLineEdit("1G")
        ml.addWidget(self.ram_min_input)
        mem_group.setLayout(ml)
        layout.addWidget(mem_group)

        plugin_group = QGroupBox("🧩 Плагины")
        pl = QVBoxLayout()
        if self.plugins_available:
            info = QLabel(f"Bridge активен. Плагинов: "
                          f"{len(self.plugin_bridge.list_plugins())}")
            info.setStyleSheet("color: #6bff6b;")
            pl.addWidget(info)
            self.plugin_list_widget = QListWidget()
            self._refresh_plugins_list()
            pl.addWidget(self.plugin_list_widget)

            row = QHBoxLayout()
            b_reload = QPushButton("♻️ Перезагрузить")
            b_reload.clicked.connect(self._reload_plugins)
            row.addWidget(b_reload)
            b_folder = QPushButton("📁 Открыть plugins")
            b_folder.clicked.connect(lambda: self._open_folder(self.plugins_dir))
            row.addWidget(b_folder)
            b_reset = QPushButton("♻️ Сбросить подтверждение")
            b_reset.clicked.connect(self._reset_plugin_ack)
            row.addWidget(b_reset)
            row.addStretch()
            pl.addLayout(row)
        else:
            info = QLabel("Плагины не активированы.")
            info.setStyleSheet("color: #8a9aaa;")
            pl.addWidget(info)
            b_dl = QPushButton("📥 Скачать загрузчик плагинов")
            b_dl.setStyleSheet(
                "background-color: #f5a623; color: white; font-weight: bold; "
                "padding: 10px 16px; border-radius: 4px;")
            b_dl.clicked.connect(self.download_plugin_bridge)
            pl.addWidget(b_dl)

        plugin_group.setLayout(pl)
        layout.addWidget(plugin_group)

        layout.addStretch()
        return page

    def _refresh_plugins_list(self):
        if not hasattr(self, "plugin_list_widget"):
            return
        self.plugin_list_widget.clear()
        if not self.plugins_available:
            return
        for p in self.plugin_bridge.list_plugins():
            status = "☑" if p.get("enabled") else "☐"
            it = QListWidgetItem(
                f"{status} {p.get('file','?')} — {p.get('title','?')}")
            self.plugin_list_widget.addItem(it)

    def _reload_plugins(self):
        self._load_plugins()
        self._refresh_plugins_list()
        self.refresh_versions_combo()

    def _reset_plugin_ack(self):
        ack = self.plugins_dir / ".acknowledged"
        if ack.exists():
            ack.unlink()

    def download_plugin_bridge(self):
        target = self.plugins_dir / BRIDGE_FILENAME
        self.dl_dialog = InstallProgressDialog("Загрузка bridge", self)
        self.dl_worker = DownloadFileWorker(PLUGIN_LOADER_URL, target, parent=self)
        self.dl_worker.progress.connect(
            lambda v, s: self.dl_dialog.update_progress(v, s))
        self.dl_worker.done.connect(self._on_bridge_downloaded)
        self.dl_worker.start()
        self.dl_dialog.exec()

    def _on_bridge_downloaded(self, ok, result):
        if self.dl_dialog:
            self.dl_dialog.mark_finished(success=ok, error=result if not ok else "")
        if ok:
            QMessageBox.information(self, "OK", "Bridge скачан. Перезапустите лаунчер.")

    def create_help_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        header = QLabel("❓ Помощь")
        header.setObjectName("Header")
        layout.addWidget(header)
        layout.addSpacing(15)
        t = QLabel(
            "DreamyLauncherMega v9.0.5 (DreamUX Edition)\n\n"
            "• Рабочая папка: DREAMY_HOME\n"
            "• Моды ZIP-сборки → versions/<Сборка>/mods/\n"
            "• Overrides → versions/<Сборка>/\n"
            "• Ручные моды → .minecraft/mods/\n"
            "• Создание своих сборок\n"
            "• Плагины через bridge\n"
        )
        t.setWordWrap(True)
        t.setStyleSheet("color: #a0b0c0; padding: 10px;")
        layout.addWidget(t)
        layout.addStretch()
        return page

    # ---------- Аккаунты ----------
    def refresh_accounts_combo(self):
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        self.account_combo.addItem("— Нет —", None)
        for acc_id, login, username, acc_type in self.db.list_accounts():
            self.account_combo.addItem(f"🟢 {username or login}", (login, acc_type))
        self.account_combo.blockSignals(False)

    def on_account_switched(self, index):
        data = self.account_combo.currentData()
        if not data:
            self.account_label.setText("🔴 Не авторизован")
            self.account_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
            self.ely_access_token = None
            self.current_acc_type = None
            return
        login, acc_type = data
        acc = self.db.get_account(login, acc_type)
        if not acc:
            return
        self.current_acc_type = "ely"
        try:
            r = elyby_refresh(acc["access_token"], acc["client_token"])
            self.ely_access_token = r["access_token"]
            self.ely_client_token = r["client_token"]
            self.db.add_account(login, acc["password"], r["username"], r["uuid"],
                                r["access_token"], r["client_token"], acc_type="ely")
            self.ely_username = r["username"]
            self.ely_uuid = r["uuid"]
        except Exception:
            try:
                d = elyby_authenticate(login, acc["password"])
                self.ely_access_token = d["access_token"]
                self.ely_client_token = d["client_token"]
                self.ely_username = d["username"]
                self.ely_uuid = d["uuid"]
                self.db.add_account(login, acc["password"], d["username"], d["uuid"],
                                    d["access_token"], d["client_token"], acc_type="ely")
            except Exception as e:
                self.account_label.setText("🔴 Ошибка")
                return
        self.db.touch_account(login, "ely")
        self.account_label.setText(f"🟢 {self.ely_username}")
        self.account_label.setStyleSheet("color: #6bff6b; font-weight: bold;")

    def add_account(self):
        dlg = ElyAuthDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        login, password = dlg.get_credentials()
        if not login or not password:
            return
        try:
            data = elyby_authenticate(login, password)
            self.db.add_account(login, password, data["username"], data["uuid"],
                                data["access_token"], data["client_token"], acc_type="ely")
            self.refresh_accounts_combo()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка Ely.by", str(e))

    # ---------- Браузер ----------
    def _build_cf_url(self, ver_display):
        base = "https://www.curseforge.com/minecraft/search"
        params = [("class","mc-mods"),("page","1"),("pageSize","20"),("sortBy","relevancy")]
        kind, ver = ver_display
        if kind == "vanilla":
            params.append(("version", ver))
        elif kind == "forge":
            mc = ver.split("-")[0]
            params.append(("version", mc))
            params.append(("gameVersionTypeId", CURSEFORGE_LOADER_IDS["forge"]))
        elif kind == "neoforge":
            mc = ver.split("-")[0]
            params.append(("version", mc))
            params.append(("gameVersionTypeId", CURSEFORGE_LOADER_IDS["neoforge"]))
        elif kind == "modset":
            meta = self.modsets.get(ver, {})
            mc = meta.get("mc", "")
            loader = meta.get("loader", "vanilla")
            if mc:
                params.append(("version", mc))
            if loader in CURSEFORGE_LOADER_IDS:
                params.append(("gameVersionTypeId", CURSEFORGE_LOADER_IDS[loader]))
        return f"{base}?{urlencode(params)}"

    def open_browser_overlay(self):
        data = self.version_combo.currentData()
        if not data:
            QMessageBox.warning(self, "Ошибка", "Выберите версию")
            return
        url = self._build_cf_url(data)
        self._current_target_url = url
        self.browser.setUrl(QUrl(url))
        self.browser_overlay.setGeometry(self.centralWidget().rect())
        self.browser_overlay.raise_()
        self.browser_overlay.show()

    def close_browser_overlay(self):
        self.browser_overlay.hide()
        self.switch_tab("Главная")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "browser_overlay") and self.browser_overlay.isVisible():
            self.browser_overlay.setGeometry(self.centralWidget().rect())

    def on_download_requested(self, item: QWebEngineDownloadRequest):
        try:
            cur_url = self._current_target_url or self.browser.url().toString()
            fname = item.downloadFileName()
            fname_low = fname.lower()

            is_shader = "shader" in fname_low or "shader" in cur_url.lower()
            is_rp = ("resourcepack" in fname_low or "resource_pack" in fname_low
                     or "/texture-packs/" in cur_url.lower()
                     or "/resourcepacks/" in cur_url.lower())

            if self.pack_install_active and hasattr(self, "_pack_current"):
                folder_name = self._pack_current["folder_name"]
                version_dir = MINECRAFT_DIR / "versions" / folder_name
                if is_shader:
                    target_dir = version_dir / "shaderpacks"
                    category = "shaderpack (pack)"
                elif is_rp:
                    target_dir = version_dir / "resourcepacks"
                    category = "resourcepack (pack)"
                else:
                    target_dir = version_dir / "mods"
                    category = "mod (pack)"
                target_dir.mkdir(parents=True, exist_ok=True)
            elif is_shader:
                item.cancel()
                self.log(f"⏭ Шейдер пропущен: {fname}")
                return
            elif is_rp:
                target_dir = self.resourcepacks_dir
                category = "resourcepack"
            else:
                target_dir = self.mods_dir
                category = "mod"

            target = target_dir / fname
            item.setDownloadDirectory(str(target.parent))
            item.setDownloadFileName(target.name)
            item.accept()
            self.download_status.setText(f"⬇ {category}: {fname}")
            self.log(f"⬇ {category}: {fname}")

            item.isFinishedChanged.connect(
                lambda it=item, tgt=target, c=category:
                    self._on_dl_finished(it, tgt, c))
        except Exception as e:
            _dlog(f"on_download_requested: {e}\n{traceback.format_exc()}")

    def _on_dl_finished(self, item, target, category):
        try:
            state = item.state()
            if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                self.log(f"✅ {category}: {target.name}")
                if "mod (pack)" in category or "resourcepack (pack)" in category:
                    self._on_download_finished_for_pack(target)
            else:
                self.log(f"❌ Загрузка не удалась: {target}")
        except Exception as e:
            _dlog(f"on_dl_finished: {e}")

    # ---------- Запуск игры ----------
    def launch_game(self):
        if not self.current_acc_type or not self.ely_access_token:
            QMessageBox.warning(self, "Нет аккаунта", "Выберите Ely.by аккаунт!")
            return
        data = self.version_combo.currentData()
        if not data:
            QMessageBox.warning(self, "Ошибка", "Выберите версию или сборку")
            return
        kind, vid = data

        self._save_last_version(kind, vid, self.version_combo.currentText())

        if kind == "plugin":
            if not self.plugins_available:
                QMessageBox.warning(self, "Плагины", "Bridge не загружен.")
                return
            self.log(f"🧩 Запуск плагина: {vid}")
            self.plugin_bridge.install_version(vid)
            return

        if kind == "modset":
            version_id = vid
            version_dir = MINECRAFT_DIR / "versions" / version_id
            if not version_dir.exists():
                QMessageBox.warning(self, "Не найдено", f"Папка {version_id} не найдена")
                return
        else:
            version_id = self._find_installed_version(kind, vid)
            if not version_id:
                QMessageBox.warning(self, "Не найдено", f"«{vid}» не установлена.")
                return

        ram_max = self.ram_input.text().strip() or "4G"
        ram_min = self.ram_min_input.text().strip() or "1G"
        jvm = [f"-Xmx{ram_max}", f"-Xms{ram_min}",
               "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8",
               "-Dstderr.encoding=UTF-8", "-Dlog4j2.formatMsgNoLookups=true"]

        authlib = MINECRAFT_DIR / "authlib-injector.jar"
        if authlib.exists():
            jvm.insert(2, f"-javaagent:{authlib}=ely.by")
        else:
            QMessageBox.warning(self, "Нет authlib", "authlib-injector.jar отсутствует.")
            return

        uuid_str = self.ely_uuid
        try:
            if uuid_str and "-" not in uuid_str and len(uuid_str) == 32:
                uuid_str = str(uuidlib.UUID(uuid_str))
        except Exception:
            pass

        options = {
            "username": self.ely_username,
            "uuid": uuid_str,
            "token": self.ely_access_token,
            "jvmArguments": jvm,
            "launcherName": "DreamyLauncherMega",
            "launcherVersion": "9.0.5",
            "gameDirectory": self.minecraft_dir,
        }
        try:
            cmd = minecraft_launcher_lib.command.get_minecraft_command(
                version_id, self.minecraft_dir, options)
            self.log(f"Запуск {version_id} RAM {ram_max}")
            cf = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self.mc_process = subprocess.Popen(
                cmd, cwd=self.minecraft_dir,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, bufsize=0, creationflags=cf)
            self.mc_log_buffer = []
            if hasattr(self, "mc_console_view"):
                self.mc_console_view.clear()
                self.mc_console_view.append(f"=== Запуск {version_id} ===\n")
            self.mc_reader = MinecraftLogReader(self.mc_process, parent=self)
            self.mc_reader.line_received.connect(self.on_mc_line)
            self.mc_reader.process_exited.connect(self.on_mc_exited)
            self.mc_reader.start()

            if self.plugins_available:
                self.plugin_bridge.call_event("on_game_start",
                                                version_id=version_id, mode=kind)
            self.log("✅ Minecraft запущен")
            QTimer.singleShot(1500, self._minimize_to_tray)
        except Exception as e:
            self.log(f"❌ {e}")
            _dlog(f"launch: {e}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Ошибка", str(e))

    def _find_installed_version(self, kind, vid):
        vdir = MINECRAFT_DIR / "versions"
        if not vdir.exists():
            return None
        installed = [p.name for p in vdir.iterdir() if p.is_dir()]
        if kind == "vanilla":
            if vid in installed:
                return vid
        elif kind == "forge":
            if vid in installed:
                return vid
            for n in installed:
                if "forge" in n.lower() and vid in n:
                    return n
        elif kind == "neoforge":
            if vid in installed:
                return vid
            for n in installed:
                if "neoforge" in n.lower() and vid in n:
                    return n
        elif kind == "fabric":
            if vid in installed:
                return vid
        return None

    def on_mc_line(self, line):
        self.mc_log_buffer.append(line)
        if hasattr(self, "mc_console_view"):
            self.mc_console_view.append(line)
            sb = self.mc_console_view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def on_mc_exited(self, rc, is_crash, full):
        if self._minimized_to_tray:
            self._restore_from_tray()
        self.log(f"{'💥 Вылет' if is_crash else '🎮 Закрыт'} (код {rc})")
        if self.plugins_available:
            try:
                self.plugin_bridge.call_event("on_game_exit",
                                                version_id="", code=rc, is_crash=is_crash)
            except Exception:
                pass

    def save_mc_log(self):
        if not self.mc_log_buffer:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", "minecraft.log",
                                                "Log (*.log *.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.mc_log_buffer))

    # ---------- Трей ----------
    def _setup_tray(self):
        icon = self.windowIcon()
        if icon.isNull():
            pm = QPixmap(64, 64)
            pm.fill(QColor("#4a9eff"))
            p = QPainter(pm)
            p.setPen(QColor("white"))
            p.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
            p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "🌙")
            p.end()
            icon = QIcon(pm)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("DreamyLauncherMega")
        menu = QMenu()
        a = QAction("🖥 Показать", self)
        a.triggered.connect(self._restore_from_tray)
        menu.addAction(a)
        menu.addSeparator()
        q = QAction("❌ Выход", self)
        q.triggered.connect(self._quit)
        menu.addAction(q)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(
            lambda r: self._restore_from_tray() if r in
            (QSystemTrayIcon.ActivationReason.DoubleClick,
             QSystemTrayIcon.ActivationReason.Trigger) else None)
        self.tray_icon.show()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._minimized_to_tray = False

    def _quit(self):
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.instance().quit()

    def _minimize_to_tray(self):
        self.hide()
        self._minimized_to_tray = True
        self.log("🖥 Свёрнут в трей.")

    def closeEvent(self, event):
        try:
            if self.mc_reader:
                self.mc_reader.stop()
        except Exception:
            pass
        if self.mc_process is not None and self.mc_process.poll() is None:
            event.ignore()
            self._minimize_to_tray()
            return
        if self.tray_icon:
            self.tray_icon.hide()
        event.accept()


# ============================================================
# ЗАПУСК
# ============================================================
def main():
    QApplication.setQuitOnLastWindowClosed(False)
    app = QApplication(sys.argv)
    app.setApplicationName("DreamyLauncherMega")
    splash = DreamySplashScreen()
    splash.show()
    app.processEvents()

    worker = AuthlibSetupWorker(str(MINECRAFT_DIR))

    def on_p(msg):
        splash.showMessage(msg,
                            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                            QColor("white"))
        app.processEvents()

    def on_done(ok):
        QTimer.singleShot(800, lambda: show_main(splash, ok))

    worker.progress.connect(on_p)
    worker.done.connect(on_done)
    worker.start()
    sys.exit(app.exec())


def show_main(splash, ok):
    win = DreamyLauncherMega()
    QApplication.instance().setProperty("main_window", win)
    QTimer.singleShot(500, lambda: (splash.finish(win), win.show()))


if __name__ == "__main__":
    main()