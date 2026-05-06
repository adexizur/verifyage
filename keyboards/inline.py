"""
Inline клавиатуры для бота.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_verification_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой начала верификации."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Пройти проверку",
                    callback_data="start_verification"
                )
            ]
        ]
    )


def get_age_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения возраста."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Мне есть 18 лет",
                    callback_data="age_confirmed"
                )
            ]
        ]
    )


def get_review_keyboard(application_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для модерации заявки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_{application_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{application_id}"
                )
            ]
        ]
    )


def get_pending_applications_keyboard(
    applications: list
) -> InlineKeyboardMarkup:
    """Клавиатура со списком заявок."""
    keyboard = []
    for app in applications:
        username = app.get("username") or f"User {app['telegram_id']}"
        keyboard.append([
            InlineKeyboardButton(
                text=f"📋 #{app['id']} - {username}",
                callback_data=f"review_{app['id']}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
