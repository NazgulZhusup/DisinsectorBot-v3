import requests
import logging

logger = logging.getLogger('utils')

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Не удалось отправить сообщение через Telegram: {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения через Telegram: {e}")



