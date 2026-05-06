"""
Handlers.
"""

from .group import router as group_router
from .private import router as private_router
from .admin import router as admin_router

__all__ = ["group_router", "private_router", "admin_router"]
