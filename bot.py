"""
Telegram Verification Bot - точка входа.

Бот для автоматической проверки возраста пользователей
перед допуском в Telegram-группу.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ChatPermissions

from config import BOT_TOKEN, GROUP_ID, LOG_LEVEL, LOG_FILE, AUTO_KICK_TIME
from database.db import init_db, db
from handlers import group_router, private_router, admin_router

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def check_auto_kick(bot: Bot) -> None:
    """
    Проверка пользователей на авто-кик.
    
    Удаляет пользователей, которые не начали проверку
    в течение AUTO_KICK_TIME секунд.
    """
    try:
        users = await db.get_all_users()
        now = datetime.now()
        
        for user in users:
            if user["status"] != "pending":
                continue
            
            # Парсим время создания (упрощенно)
            created_at_str = user.get("created_at", "")
            if not created_at_str:
                continue
            
            try:
                # Формат: YYYY-MM-DD HH:MM:SS
                created_at = datetime.strptime(created_at_str[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            
            # Проверяем, прошло ли больше AUTO_KICK_TIME
            if (now - created_at).total_seconds() > AUTO_KICK_TIME:
                try:
                    # Удаляем пользователя из группы
                    await bot.ban_chat_member(
                        chat_id=GROUP_ID,
                        user_id=user["telegram_id"]
                    )
                    
                    # Обновляем статус
                    await db.update_user_status(
                        telegram_id=user["telegram_id"],
                        status="kicked"
                    )
                    
                    logger.info(
                        f"Пользователь {user['telegram_id']} удалён по таймауту"
                    )
                    
                except Exception as e:
                    logger.warning(
                        f"Не удалось удалить пользователя {user['telegram_id']}: {e}"
                    )
                    
    except Exception as e:
        logger.error(f"Ошибка при проверке авто-кика: {e}")


async def periodic_auto_kick(bot: Bot) -> None:
    """
    Периодическая проверка авто-кика каждые 5 минут.
    """
    while True:
        await asyncio.sleep(300)  # 5 минут
        await check_auto_kick(bot)


async def on_startup(bot: Bot) -> None:
    """
    Действия при запуске бота.
    """
    logger.info("Бот запускается...")
    
    # Проверяем подключение к БД
    await init_db()
    logger.info("База данных инициализирована")
    
    # Запускаем периодическую проверку авто-кика
    asyncio.create_task(periodic_auto_kick(bot))
    
    # Одноразовая проверка при старте
    await check_auto_kick(bot)
    
    logger.info("Бот готов к работе")


async def on_shutdown(bot: Bot) -> None:
    """
    Действия при остановке бота.
    """
    logger.info("Бот останавливается...")
    await db.close()
    logger.info("Соединение с БД закрыто")


def register_routers(dp: Dispatcher) -> None:
    """
    Регистрация всех роутеров.
    """
    dp.include_router(admin_router)      # Админские команды (ЛС)
    dp.include_router(private_router)    # Верификация (ЛС)
    dp.include_router(group_router)      # Группа


async def main() -> None:
    """
    Основная функция запуска бота.
    """
    # Создаем бота и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем роутеры
    register_routers(dp)
    
    # Регистрируем хуки старта/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем polling
    try:
        logger.info("Запуск polling...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Остановка по Ctrl+C")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
