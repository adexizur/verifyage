"""
Конфигурация бота.
"""

import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID группы для проверки пользователей
GROUP_ID = os.getenv("GROUP_ID")

# Whitelist админов (замените на ваши Telegram ID)
ADMINS = {123456789, 987654321}

# Время до авто-кика в секундах (30 минут)
AUTO_KICK_TIME = 30 * 60

# Путь к базе данных
DATABASE_PATH = "verification_bot.db"

# Логирование
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"
