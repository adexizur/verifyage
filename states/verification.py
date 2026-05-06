"""
FSM состояния для верификации.
"""

from aiogram.fsm.state import State, StatesGroup


class VerificationStates(StatesGroup):
    """Состояния процесса верификации."""

    # Ожидание подтверждения возраста
    waiting_for_age_confirmation = State()

    # Ожидание фото документа
    waiting_for_document = State()

    # Ожидание video note (кружка)
    waiting_for_video_note = State()
