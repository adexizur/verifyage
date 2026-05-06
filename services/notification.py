"""
Сервис уведомлений для админов.
"""

import logging
from typing import List

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from config import ADMINS

logger = logging.getLogger(__name__)


async def notify_admins_about_new_application(
    bot: Bot,
    application_id: int,
    username: str,
    telegram_id: int
) -> None:
    """
    Отправить уведомление всем админам о новой заявке.
    
    Args:
        bot: Экземпляр бота
        application_id: ID заявки
        username: Имя пользователя
        telegram_id: Telegram ID пользователя
    """
    message = (
        f"🔔 <b>Новая заявка на верификацию!</b>\n\n"
        f"👤 Пользователь: {username or f'User {telegram_id}'}\n"
        f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
        f"📋 ID заявки: <code>{application_id}</code>\n\n"
        f"Используйте /review {application_id} для просмотра."
    )

    for admin_id in ADMINS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(
                f"Не удалось отправить уведомление админу {admin_id}: {e}"
            )


async def notify_user_about_decision(
    bot: Bot,
    chat_id: int,
    approved: bool,
    reason: str = None
) -> None:
    """
    Уведомить пользователя о решении по заявке.
    
    Args:
        bot: Экземпляр бота
        chat_id: Chat ID пользователя
        approved: True если одобрено, False если отклонено
        reason: Причина отклонения (если есть)
    """
    if approved:
        message = (
            "✅ <b>Ваша заявка одобрена!</b>\n\n"
            "Теперь вы можете полноценно участвовать в жизни группы.\n"
            "Ограничения сняты."
        )
    else:
        message = (
            "❌ <b>Ваша заявка отклонена.</b>\n\n"
        )
        if reason:
            message += f"Причина: {reason}\n\n"
        message += "Ограничения остаются в силе."

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {chat_id}: {e}")
