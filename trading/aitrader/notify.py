"""텔레그램 알림. TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 환경변수가 없으면 콘솔에만 출력한다."""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    def send(self, text: str) -> None:
        print(text)
        if not (self.token and self.chat_id):
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text},
                timeout=10,
            ).raise_for_status()
        except requests.RequestException as e:
            # 알림 실패가 매매 루프를 멈추게 해서는 안 된다
            log.warning("텔레그램 전송 실패: %s", e)
