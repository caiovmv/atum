"""Testes do módulo de notificação (feed)."""

from __future__ import annotations

from unittest.mock import patch


class TestSendNotification:
    def test_notify_disabled_does_nothing(self) -> None:
        from app.notify import send_notification

        with patch("app.config.get_settings") as m:
            m.return_value.notify_enabled = False
            m.return_value.notify_webhook_url = "http://x.com"
            send_notification("Title", "Body")
            m.assert_called_once()

    def test_notify_enabled_webhook_calls_requests_post(self) -> None:
        from app.notify import send_notification

        with patch("app.config.get_settings") as m_settings:
            m_settings.return_value.notify_enabled = True
            m_settings.return_value.notify_webhook_url = "https://hooks.example.com/notify"
            m_settings.return_value.notify_desktop = False
            with patch("requests.post") as m_post:
                send_notification("dl-torrent: novo no feed", "Artist - Album [FLAC]")
                m_post.assert_called_once()
                call_args = m_post.call_args
                assert call_args[0][0] == "https://hooks.example.com/notify"
                assert call_args[1]["json"]["title"] == "dl-torrent: novo no feed"
                assert "Artist" in call_args[1]["json"]["text"]

    def test_notify_enabled_desktop_does_not_raise(self) -> None:
        from app.notify import send_notification

        with patch("app.config.get_settings") as m_settings:
            m_settings.return_value.notify_enabled = True
            m_settings.return_value.notify_webhook_url = ""
            m_settings.return_value.notify_desktop = True
            with patch("app.notify._notify_desktop"):
                send_notification("Title", "Body")
