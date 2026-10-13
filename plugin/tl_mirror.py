# -*- coding: utf-8 -*-
# Плагин: TL Mirror
# Имитирует TLauncher для запросов к его серверам.
# Автор: DreamyLauncherMega
# Версия: 1.0.0

PLUGIN_NAME = "TL Mirror"
PLUGIN_AUTHOR = "DreamyLauncherMega"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Имитирует TLauncher для запросов к зеркалу сборок"

import sys

_state = {"original_session": None, "original_request": None}


# ============================================================
# TL-заголовки (по найденным данным)
# ============================================================
TL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/610.1 (KHTML, like Gecko) "
        "JavaFX/8.0 Safari/610.1"
    ),
    "Referer": "https://tlauncher.org/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    # ⚠️ Раскомментируй, когда узнаешь значение:
    # "signature-agent": "...",
}


# ============================================================
# Патч requests.Session
# ============================================================
def _patch_requests():
    """Перехватывает requests.Session и request."""
    try:
        import requests
    except ImportError:
        print("[TL Mirror] requests не установлен")
        return False

    _state["original_session"] = requests.Session
    _state["original_request"] = requests.request

    # --- Патч Session.request ---
    original_session_request = requests.Session.request

    def tl_session_request(self, method, url, **kwargs):
        headers = kwargs.get("headers") or {}
        # Подменяем UA и Referer, только если запрос идёт на TL-домены
        if any(host in str(url) for host in (
            "tlauncher.org", "tlauncher.ru", "tlmods.org",
            "repo.tlauncher.org", "auth.tlauncher.org"
        )):
            for k, v in TL_HEADERS.items():
                if k not in headers:
                    headers[k] = v
            kwargs["headers"] = headers
            print(f"[TL Mirror] → {method} {url}")
            print(f"[TL Mirror]   Headers: {headers}")

        return original_session_request(self, method, url, **kwargs)

    requests.Session.request = tl_session_request

    # --- Патч requests.request ---
    def tl_request(method, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if any(host in str(url) for host in (
            "tlauncher.org", "tlauncher.ru", "tlmods.org",
            "repo.tlauncher.org", "auth.tlauncher.org"
        )):
            for k, v in TL_HEADERS.items():
                if k not in headers:
                    headers[k] = v
            kwargs["headers"] = headers
        return _state["original_request"](method, url, **kwargs)

    requests.request = tl_request

    print("[TL Mirror] ✅ Патч requests применён")
    return True


# ============================================================
# API плагина
# ============================================================
def get_versions():
    return []


def install_version(version_id, ctx):
    return False


def on_launcher_start(ctx=None):
    _patch_requests()


def on_launcher_exit(ctx=None):
    # Восстанавливаем
    try:
        import requests
        if _state["original_session"]:
            requests.Session = _state["original_session"]
        if _state["original_request"]:
            requests.request = _state["original_request"]
    except Exception:
        pass
