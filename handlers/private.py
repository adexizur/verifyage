"""
Обработчики личных сообщений для верификации.

FSM сценарий:
1. Подтверждение возраста кнопкой
2. Отправка фото документа
3. Отправка video note (кружка)
4. Отправка заявки админам
"""

import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, PhotoSize

from states import VerificationStates
from database.db import db
from keyboards.inline import get_age_confirmation_keyboard
from services.notification import notify_admins_about_new_application

logger = logging.getLogger(__name__)

router = Router(name="private")


@router.callback_query(F.data == "age_confirmed")
async def handle_age_confirmation(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Обработка подтверждения возраста.
    
    Переводит пользователя в состояние ожидания фото документа.
    """
    user = callback.from_user
    
    # Устанавливаем состояние ожидания документа
    await state.set_state(VerificationStates.waiting_for_document)
    
    # Отправляем инструкцию по документу
    instruction_text = (
        "✅ Возраст подтвержден!\n\n"
        "📄 <b>Отправьте фото вашего документа</b>\n\n"
        "<b>Что нужно замазать:</b>\n"
        "• Номер документа\n"
        "• Серия документа\n"
        "• Адрес\n"
        "• Подпись\n\n"
        "<b>Что должно остаться видимым:</b>\n"
        "• Ваше лицо (фотография)\n"
        "• Дата рождения\n\n"
        "Отправьте фото одним сообщением."
    )
    
    await callback.message.edit_text(
        text=instruction_text,
        parse_mode="HTML"
    )
    
    logger.info(f"Пользователь {user.id} подтвердил возраст")


@router.message(
    VerificationStates.waiting_for_document,
    F.photo
)
async def handle_document_photo(
    message: Message,
    state: FSMContext
) -> None:
    """
    Обработка фото документа.
    
    Сохраняет file_id и переводит в состояние ожидания video note.
    """
    user = message.from_user
    
    # Получаем фото наилучшего качества (последнее в списке)
    photo: PhotoSize = message.photo[-1]
    document_file_id = photo.file_id
    
    # Сохраняем file_id документа во временное хранилище
    await state.update_data(document_file_id=document_file_id)
    
    # Переводим в состояние ожидания video note
    await state.set_state(VerificationStates.waiting_for_video_note)
    
    # Отправляем инструкцию для video note
    instruction_text = (
        "📸 Документ получен!\n\n"
        "🎥 <b>Теперь отправьте video note (кружок)</b>\n\n"
        "Запишите короткое видео для подтверждения вашей личности.\n"
        "Просто нажмите на значок кружка в поле ввода сообщения."
    )
    
    await message.answer(
        text=instruction_text,
        parse_mode="HTML"
    )
    
    logger.info(f"Пользователь {user.id} отправил фото документа")


@router.message(
    VerificationStates.waiting_for_document,
    ~F.photo
)
async def handle_invalid_document(
    message: Message,
    state: FSMContext
) -> None:
    """
    Обработка некорректного сообщения вместо фото.
    """
    await message.answer(
        "❌ Пожалуйста, отправьте фото документа.\n"
        "Используйте камеру или загрузите изображение."
    )


@router.message(
    VerificationStates.waiting_for_video_note,
    F.video_note
)
async def handle_video_note(
    message: Message,
    state: FSMContext,
    bot
) -> None:
    """
    Обработка video note (кружка).
    
    Завершает процесс верификации и создает заявку.
    """
    user = message.from_user
    
    # Получаем file_id video note
    video_note_file_id = message.video_note.file_id
    
    # Получаем сохраненный file_id документа
    data = await state.get_data()
    document_file_id = data.get("document_file_id")
    
    if not document_file_id:
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, начните заново."
        )
        await state.clear()
        return
    
    try:
        # Получаем или создаем пользователя в БД
        db_user = await db.get_or_create_user(
            telegram_id=user.id,
            username=user.username
        )
        
        # Создаем заявку
        application_id = await db.create_application(
            user_id=db_user["id"],
            document_file_id=document_file_id,
            video_note_file_id=video_note_file_id
        )
        
        # Очищаем состояние FSM
        await state.clear()
        
        # Отправляем пользователю подтверждение
        confirmation_text = (
            "✅ <b>Заявка отправлена на рассмотрение!</b>\n\n"
            "Администраторы проверят вашу заявку в ближайшее время.\n"
            "Вы получите уведомление о решении."
        )
        
        await message.answer(
            text=confirmation_text,
            parse_mode="HTML"
        )
        
        # Уведомляем админов
        await notify_admins_about_new_application(
            bot=bot,
            application_id=application_id,
            username=user.username,
            telegram_id=user.id
        )
        
        logger.info(
            f"Создана заявка #{application_id} от пользователя {user.id}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании заявки: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании заявки.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        await state.clear()


@router.message(
    VerificationStates.waiting_for_video_note,
    ~F.video_note
)
async def handle_invalid_video_note(
    message: Message,
    state: FSMContext
) -> None:
    """
    Обработка некорректного сообщения вместо video note.
    """
    await message.answer(
        "❌ Пожалуйста, отправьте video note (кружок).\n"
        "Нажмите на значок кружка в поле ввода сообщения."
    )
