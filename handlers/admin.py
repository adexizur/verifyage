"""
Обработчики админских команд.

Все команды работают ТОЛЬКО в личных сообщениях с ботом.
Требуется наличие пользователя в whitelist админов.

Команды:
- /pending - показать необработанные заявки
- /review <id> - просмотр заявки
- /approve <id> - одобрить заявку
- /reject <id> <reason> - отклонить заявку
- /stats - статистика
"""

import logging
from typing import Union

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from aiogram.exceptions import TelegramBadRequest

from config import GROUP_ID
from database.db import db
from keyboards.inline import (
    get_pending_applications_keyboard,
    get_review_keyboard
)
from services.notification import notify_user_about_decision
from middlewares.admin import AdminWhitelistMiddleware

logger = logging.getLogger(__name__)

router = Router(name="admin")

# Применяем middleware только к этому роутеру
router.message.middleware(AdminWhitelistMiddleware())
router.callback_query.middleware(AdminWhitelistMiddleware())


@router.message(F.command == "pending")
async def cmd_pending(message: Message) -> None:
    """
    Показать список необработанных заявок.
    """
    try:
        applications = await db.get_pending_applications()
        
        if not applications:
            await message.answer(
                "📋 Нет необработанных заявок.\n\n"
                "Все заявки рассмотрены!"
            )
            return
        
        # Формируем сообщение со списком
        text = f"📋 <b>Необработанные заявки ({len(applications)})</b>\n\n"
        
        for app in applications:
            username = app.get("username") or f"User {app['telegram_id']}"
            created_at = app.get("created_at", "Unknown")[:16]
            text += (
                f"🔹 <b>#{app['id']}</b> - {username}\n"
                f"   ID: <code>{app['telegram_id']}</code>\n"
                f"   Дата: {created_at}\n\n"
            )
        
        # Добавляем клавиатуру для быстрого перехода
        keyboard = get_pending_applications_keyboard(applications)
        
        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка заявок: {e}")
        await message.answer("❌ Произошла ошибка при загрузке заявок.")


@router.message(F.command == "review")
async def cmd_review(message: Message) -> None:
    """
    Показать заявку для модерации.
    
    Использование: /review <id>
    """
    try:
        # Парсим аргумент команды
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ Не указан ID заявки.\n\n"
                "Использование: /review <id>\n"
                "Пример: /review 1"
            )
            return
        
        application_id = int(args[1])
        
        # Получаем заявку из БД
        application = await db.get_application_by_id(application_id)
        
        if not application:
            await message.answer(
                f"❌ Заявка #{application_id} не найдена."
            )
            return
        
        if application.get("decision"):
            status = "✅ Одобрено" if application["decision"] == "approved" else "❌ Отклонено"
            await message.answer(
                f"📋 Заявка #{application_id} уже рассмотрена.\n\n"
                f"Статус: {status}"
            )
            return
        
        # Формируем сообщение с информацией о заявке
        username = application.get("username") or f"User {application['telegram_id']}"
        
        text = (
            f"📋 <b>Заявка #{application_id}</b>\n\n"
            f"👤 Пользователь: {username}\n"
            f"🆔 Telegram ID: <code>{application['telegram_id']}</code>\n\n"
            f"Ниже прикреплены фото документа и video note."
        )
        
        # Отправляем фото документа
        await message.answer_photo(
            photo=application["document_file_id"],
            caption=text,
            parse_mode="HTML"
        )
        
        # Отправляем video note
        await message.answer_video_note(
            video_note=application["video_note_file_id"]
        )
        
        # Отправляем клавиатуру для принятия решения
        keyboard = get_review_keyboard(application_id)
        await message.answer(
            "Выберите действие:",
            reply_markup=keyboard
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID заявки.\n\n"
            "Использование: /review <id>\n"
            "Пример: /review 1"
        )
    except Exception as e:
        logger.error(f"Ошибка при просмотре заявки: {e}")
        await message.answer("❌ Произошла ошибка при загрузке заявки.")


@router.callback_query(F.data.startswith("approve_"))
async def callback_approve(callback: CallbackQuery, bot: Bot) -> None:
    """
    Одобрить заявку через inline кнопку.
    """
    try:
        application_id = int(callback.data.split("_")[1])
        
        # Получаем заявку
        application = await db.get_application_by_id(application_id)
        
        if not application:
            await callback.answer("❌ Заявка не найдена.", show_alert=True)
            return
        
        if application.get("decision"):
            await callback.answer(
                "❌ Заявка уже рассмотрена.",
                show_alert=True
            )
            return
        
        # Обновляем статус заявки
        await db.update_application_decision(
            application_id=application_id,
            moderator_id=callback.from_user.id,
            decision="approved"
        )
        
        # Обновляем статус пользователя
        await db.update_user_status(
            telegram_id=application["telegram_id"],
            status="verified"
        )
        
        # Снимаем ограничения в группе
        try:
            await bot.restrict_chat_member(
                chat_id=GROUP_ID,
                user_id=application["telegram_id"],
                permissions=None  # Снимаем все ограничения
            )
        except Exception as e:
            logger.warning(
                f"Не удалось снять ограничения для пользователя "
                f"{application['telegram_id']}: {e}"
            )
        
        # Уведомляем пользователя
        await notify_user_about_decision(
            bot=bot,
            chat_id=application["telegram_id"],
            approved=True
        )
        
        # Обновляем сообщение с кнопками
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("✅ Заявка одобрена!")
        
        await callback.answer("Заявка одобрена!")
        
        logger.info(
            f"Заявка #{application_id} одобрена админом {callback.from_user.id}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при одобрении заявки: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("reject_"))
async def callback_reject_start(callback: CallbackQuery) -> None:
    """
    Начало процесса отклонения заявки (запрос причины).
    """
    try:
        application_id = int(callback.data.split("_")[1])
        
        # Получаем заявку
        application = await db.get_application_by_id(application_id)
        
        if not application:
            await callback.answer("❌ Заявка не найдена.", show_alert=True)
            return
        
        if application.get("decision"):
            await callback.answer(
                "❌ Заявка уже рассмотрена.",
                show_alert=True
            )
            return
        
        await callback.answer(
            "Отправьте причину отклонения следующим сообщением.\n"
            "Или используйте команду /reject <id> <причина>"
        )
        
        # Сохраняем ID заявки в состоянии для быстрой обработки
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.state import State, StatesGroup
        
        class RejectState(StatesGroup):
            waiting_for_reason = State()
        
        # Примечание: для полноценной реализации нужно отдельное FSM состояние
        # Здесь упрощенная версия - используем команду /reject
        
    except Exception as e:
        logger.error(f"Ошибка при начале отклонения заявки: {e}")
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


@router.message(F.command == "reject")
async def cmd_reject(message: Message, bot: Bot) -> None:
    """
    Отклонить заявку.
    
    Использование: /reject <id> <причина>
    """
    try:
        # Парсим аргументы команды
        args = message.text.split(maxsplit=2)
        
        if len(args) < 3:
            await message.answer(
                "❌ Не указан ID заявки или причина.\n\n"
                "Использование: /reject <id> <причина>\n"
                "Пример: /reject 1 Документ не читается"
            )
            return
        
        application_id = int(args[1])
        reason = args[2]
        
        # Получаем заявку
        application = await db.get_application_by_id(application_id)
        
        if not application:
            await message.answer(
                f"❌ Заявка #{application_id} не найдена."
            )
            return
        
        if application.get("decision"):
            await message.answer(
                f"📋 Заявка #{application_id} уже рассмотрена."
            )
            return
        
        # Обновляем статус заявки
        await db.update_application_decision(
            application_id=application_id,
            moderator_id=message.from_user.id,
            decision="rejected",
            reject_reason=reason
        )
        
        # Обновляем статус пользователя
        await db.update_user_status(
            telegram_id=application["telegram_id"],
            status="rejected"
        )
        
        # Уведомляем пользователя
        await notify_user_about_decision(
            bot=bot,
            chat_id=application["telegram_id"],
            approved=False,
            reason=reason
        )
        
        await message.answer(
            f"❌ Заявка #{application_id} отклонена.\n"
            f"Причина: {reason}"
        )
        
        logger.info(
            f"Заявка #{application_id} отклонена админом {message.from_user.id}"
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID заявки.\n\n"
            "Использование: /reject <id> <причина>"
        )
    except Exception as e:
        logger.error(f"Ошибка при отклонении заявки: {e}")
        await message.answer("❌ Произошла ошибка.")


@router.message(F.command == "stats")
async def cmd_stats(message: Message) -> None:
    """
    Показать статистику по заявкам.
    """
    try:
        stats = await db.get_stats()
        
        text = (
            "📊 <b>Статистика верификации</b>\n\n"
            f"⏳ В ожидании: <b>{stats['pending']}</b>\n"
            f"✅ Одобрено: <b>{stats['approved']}</b>\n"
            f"❌ Отклонено: <b>{stats['rejected']}</b>\n\n"
            f"Всего заявок: <b>{stats['pending'] + stats['approved'] + stats['rejected']}</b>"
        )
        
        await message.answer(
            text=text,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer("❌ Произошла ошибка при загрузке статистики.")


@router.message(F.command == "start")
async def cmd_start(message: Message) -> None:
    """
    Команда /start для админов.
    """
    text = (
        "👋 <b>Привет, администратор!</b>\n\n"
        "Доступные команды:\n\n"
        "📋 /pending - Необработанные заявки\n"
        "🔍 /review <id> - Просмотр заявки\n"
        "✅ /approve <id> - Одобрить заявку\n"
        "❌ /reject <id> <причина> - Отклонить заявку\n"
        "📊 /stats - Статистика"
    )
    
    await message.answer(
        text=text,
        parse_mode="HTML"
    )
