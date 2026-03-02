"""Notificação ao detectar novo item no feed (webhook ou desktop)."""

from __future__ import annotations

import platform
import subprocess
import sys


def send_notification(title: str, message: str = "") -> None:
    """
    Envia notificação conforme config (NOTIFY_WEBHOOK_URL e/ou NOTIFY_DESKTOP).
    Não levanta exceção; falhas são silenciosas.
    """
    from .config import get_settings

    s = get_settings()
    if not getattr(s, "notify_enabled", False):
        return
    sent = False
    if getattr(s, "notify_webhook_url", "").strip():
        _notify_webhook(s.notify_webhook_url.strip(), title, message)
        sent = True
    if getattr(s, "notify_desktop", False):
        _notify_desktop(title, message)
        sent = True
    # Sem config de notificação ativa, não faz nada
    return None if sent else None


def _notify_webhook(url: str, title: str, message: str) -> None:
    try:
        import requests
        body = {"title": title, "message": message, "text": f"{title}\n{message}".strip()}
        requests.post(url, json=body, timeout=5)
    except Exception:
        pass


def _notify_desktop(title: str, message: str) -> None:
    if platform.system() == "Windows":
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title[:64], (message or title)[:128], duration=5, threaded=True)
        except ImportError:
            pass
    else:
        try:
            subprocess.run(
                ["notify-send", title[:64], (message or title)[:128]],
                timeout=2,
                capture_output=True,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
