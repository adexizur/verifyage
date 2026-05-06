"""
Клавиатуры.
"""

from .inline import (
    get_start_verification_keyboard,
    get_age_confirmation_keyboard,
    get_review_keyboard,
    get_pending_applications_keyboard
)

__all__ = [
    "get_start_verification_keyboard",
    "get_age_confirmation_keyboard",
    "get_review_keyboard",
    "get_pending_applications_keyboard"
]
