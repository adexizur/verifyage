"""
Модуль работы с SQLite базой данных.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Any

import aiosqlite

from config import DATABASE_PATH


class Database:
    """Класс для работы с базой данных."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Подключение к базе данных."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._init_tables()

    async def close(self) -> None:
        """Закрытие подключения к базе данных."""
        if self._connection:
            await self._connection.close()

    async def _init_tables(self) -> None:
        """Инициализация таблиц базы данных."""
        async with self._connection.cursor() as cursor:
            # Таблица пользователей
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица заявок
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    document_file_id TEXT,
                    video_note_file_id TEXT,
                    moderator_id INTEGER,
                    decision TEXT,
                    reject_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            # Индексы для ускорения поиска
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_telegram_id 
                ON users (telegram_id)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_applications_user_id 
                ON applications (user_id)
            """)
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_applications_decision 
                ON applications (decision)
            """)

            await self._connection.commit()

    async def get_or_create_user(
        self, telegram_id: int, username: Optional[str] = None
    ) -> dict:
        """Получить или создать пользователя."""
        async with self._connection.cursor() as cursor:
            # Попытка получить существующего пользователя
            await cursor.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()

            if row:
                return dict(row)

            # Создание нового пользователя
            await cursor.execute(
                """
                INSERT INTO users (telegram_id, username, status)
                VALUES (?, ?, 'pending')
                """,
                (telegram_id, username)
            )
            await self._connection.commit()

            # Получение созданного пользователя
            await cursor.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return dict(row)

    async def update_user_status(
        self, telegram_id: int, status: str
    ) -> None:
        """Обновить статус пользователя."""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "UPDATE users SET status = ? WHERE telegram_id = ?",
                (status, telegram_id)
            )
            await self._connection.commit()

    async def get_user_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[dict]:
        """Получить пользователя по Telegram ID."""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_application(
        self,
        user_id: int,
        document_file_id: str,
        video_note_file_id: str
    ) -> int:
        """Создать новую заявку."""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO applications 
                (user_id, document_file_id, video_note_file_id)
                VALUES (?, ?, ?)
                """,
                (user_id, document_file_id, video_note_file_id)
            )
            await self._connection.commit()
            return cursor.lastrowid

    async def get_pending_applications(self) -> List[dict]:
        """Получить все необработанные заявки."""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                SELECT a.*, u.telegram_id, u.username
                FROM applications a
                JOIN users u ON a.user_id = u.id
                WHERE a.decision IS NULL
                ORDER BY a.created_at DESC
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_application_by_id(
        self, application_id: int
    ) -> Optional[dict]:
        """Получить заявку по ID."""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                SELECT a.*, u.telegram_id, u.username
                FROM applications a
                JOIN users u ON a.user_id = u.id
                WHERE a.id = ?
            """, (application_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_application_decision(
        self,
        application_id: int,
        moderator_id: int,
        decision: str,
        reject_reason: Optional[str] = None
    ) -> None:
        """Обновить решение по заявке."""
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE applications
                SET moderator_id = ?, decision = ?, reject_reason = ?
                WHERE id = ?
                """,
                (moderator_id, decision, reject_reason, application_id)
            )
            await self._connection.commit()

    async def get_stats(self) -> dict:
        """Получить статистику по заявкам."""
        async with self._connection.cursor() as cursor:
            # Pending
            await cursor.execute("""
                SELECT COUNT(*) FROM applications WHERE decision IS NULL
            """)
            pending = (await cursor.fetchone())[0]

            # Approved
            await cursor.execute("""
                SELECT COUNT(*) FROM applications WHERE decision = 'approved'
            """)
            approved = (await cursor.fetchone())[0]

            # Rejected
            await cursor.execute("""
                SELECT COUNT(*) FROM applications WHERE decision = 'rejected'
            """)
            rejected = (await cursor.fetchone())[0]

            return {
                "pending": pending,
                "approved": approved,
                "rejected": rejected
            }

    async def get_all_users(self) -> List[dict]:
        """Получить всех пользователей."""
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Глобальный экземпляр базы данных
db = Database()


async def init_db() -> None:
    """Инициализация базы данных."""
    await db.connect()
