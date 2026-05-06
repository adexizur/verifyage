"""
Обработчики событий в группе.

Бот реагирует только на:
- Новых участников (welcome + restrict)
- Кнопку перехода в ЛС

Никакие команды в группе не обрабатываются.
"""

import logging
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import (
    ChatMemberUpdated,
    ChatMemberMember,
    Message,
    CallbackQuery,
    InlineKeyboardMarkup
)
from aiogram.exceptions import TelegramBadRequest

from config import GROUP_ID, AUTO_KICK_TIME
from database.db import db
from keyboards.inline import get_start_verification_keyboard

logger = logging.getLogger(__name__)

router = Router(name="group")


@router.chat_member()
async def handle_new_member(event: ChatMemberUpdated, bot: Bot) -> None:
    """
    Обработка новых участников группы.
    
    Ограничивает права нового участника и отправляет сообщение
    с кнопкой прохождения верификации.
    """
    # Проверяем, что это изменение статуса участника
    if event.old_chat_member.status != event.new_chat_member.status:
        new_status = event.new_chat_member
        old_status = event.old_chat_member
        
        # Проверяем, что пользователь стал участником (был left или kicked)
        if (isinstance(new_status, ChatMemberMember) and 
            old_status.status in ["left", "kicked"]):
            
            user = event.from_user
            chat_id = event.chat.id
            
            # Проверяем, что это наша группа
            if str(chat_id) != str(GROUP_ID):
                return
            
            logger.info(f"Новый участник в группе: {user.username} ({user.id})")
            
            try:
                # Ограничиваем права пользователя
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user.id,
                    permissions=new_status.permissions.__class__(
                        can_send_messages=False,
                        can_send_audios=False,
                        can_send_documents=False,
                        can_send_photos=False,
                        can_send_videos=False,
                        can_send_video_notes=False,
                        can_send_voice_notes=False,
                        can_send_polls=False,
                        can_add_web_page_previews=False,
                        can_change_info=False,
                        can_invite_users=False,
                        can_pin_messages=False
                    ),
                    until_date=None  # Бессрочное ограничение
                )
                
                # Создаем или получаем пользователя из БД
                await db.get_or_create_user(
                    telegram_id=user.id,
                    username=user.username
                )
                
                # Отправляем приветственное сообщение с кнопкой
                welcome_text = (
                    f"👋 Привет, {user.username or user.first_name}!\n\n"
                    "Для доступа к группе необходимо пройти проверку возраста.\n"
                    "Нажмите кнопку ниже, чтобы начать."
                )
                
                await bot.send_message(
                    chat_id=user.id,
                    text=welcome_text,
                    reply_markup=get_start_verification_keyboard()
                )
                
                # Планируем авто-кик через 30 минут
                # (реализуется через проверку при старте бота или фоновую задачу)
                
            except TelegramBadRequest as e:
                logger.error(f"Ошибка при ограничении пользователя {user.id}: {e}")
            except Exception as e:
                logger.error(f"Неожиданная ошибка при обработке нового участника: {e}")


@router.callback_query(F.data == "start_verification")
async def handle_start_verification(callback: CallbackQuery, bot: Bot) -> None:
    """
    Обработка кнопки начала верификации.
    
    Перенаправляет пользователя в ЛС для начала процесса.
    """
    user = callback.from_user
    
    # Отвечаем на callback
    await callback.answer("Переходите в личные сообщения для верификации.")
    
    # Отправляем сообщение в ЛС с инструкцией
    instruction_text = (
        "🔐 <b>Процесс верификации</b>\n\n"
        "Для подтверждения возраста выполните следующие шаги:\n\n"
        "1️⃣ Нажмите кнопку «Мне есть 18 лет»\n"
        "2️⃣ Отправьте фото документа (замажьте номер, серию, адрес и подпись)\n"
        "3️⃣ Отправьте video note (кружок) для подтверждения личности\n\n"
        "<b>Важно:</b> На документе должны быть видны ваше лицо и дата рождения."
    )
    
    from keyboards.inline import get_age_confirmation_keyboard
    
    await bot.send_message(
        chat_id=user.id,
        text=instruction_text,
        reply_markup=get_age_confirmation_keyboard(),
        parse_mode="HTML"
    )
    
    # Удаляем сообщение с кнопкой в группе (если возможно)
    try:
        await callback.message.delete()
    except Exception:
        pass
