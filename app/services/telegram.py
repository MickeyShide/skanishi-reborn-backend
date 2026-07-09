import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self):
        self.bot_token = settings.BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        if not self.bot_token or self.bot_token == "DUMMY_TOKEN":
            logger.debug(f"Push notification skipped (no BOT_TOKEN): to={chat_id}, text={text}")
            return False

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.api_url, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"Telegram push sent to {chat_id}")
                    return True
                else:
                    logger.warning(f"Telegram API error {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            return False
