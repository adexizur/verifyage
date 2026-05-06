"""
Services.
"""

from .notification import (
    notify_admins_about_new_application,
    notify_user_about_decision
)

__all__ = [
    "notify_admins_about_new_application",
    "notify_user_about_decision"
]
