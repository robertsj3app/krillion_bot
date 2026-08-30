import sqlite3
import aiosqlite
import functools
from typing import Self, Optional, Literal
from krillion_bot.services.parser import KrillionResult


class DatabaseHandler:

    DEFAULT_DB_FILE_LOCATION = ""
    db_file_location: str

    def __init__(self: Self, guild_id: int, channel_id: str) -> None:
        self.guild_id = guild_id
        self.channel_id = channel_id

    @classmethod
    def initial_setup(cls, db_file_location: str):
        db = sqlite3.connect(db_file_location)
        cls.db_file_location = db_file_location

        db.execute("""
            CREATE TABLE IF NOT EXISTS krillionResults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                author_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                game_number INTEGER NOT NULL,
                score INTEGER NOT NULL,
                krillions INTEGER NOT NULL,
                deep_cuts INTEGER NOT NULL,
                rares INTEGER NOT NULL,
                schoolers INTEGER NOT NULL,
                clevers INTEGER NOT NULL,
                planktons INTEGER NOT NULL,
                blanks INTEGER NOT NULL,
                result_order TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        db.commit()

    async def wipe(self: Self):
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("DELETE FROM krillionResults;")
            await db.commit()

    
    async def check_user_submitted_today(self: Self, author_id: int):
        async with aiosqlite.connect(self.db_file_location) as db:
            cursor = await db.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM krillionResults
                    WHERE guild_id = ?
                    AND author_id = ?
                    AND created_at >= datetime('now', 'start of day', '+4 hours')
                    AND created_at < datetime('now', '+1 day', 'start of day', '+4 hours')
                )
                """,
                (self.guild_id, author_id),
            )
            result = await cursor.fetchone()
        return result is not None and bool(result[0])


    async def log_result(self: Self, author_id: int, author_name: str, result: KrillionResult):
        async with aiosqlite.connect(self.db_file_location) as db:

            if await self.check_user_submitted_today(author_id):
                raise Exception(f"Cannot submit a second Krillion result for user {author_name} on the same day!")
            
            await db.execute(
                """
                INSERT INTO krillionResults (
                    guild_id,
                    author_id,
                    author_name,
                    game_number,
                    score,
                    krillions,
                    deep_cuts,
                    rares,
                    schoolers,
                    clevers,
                    planktons,
                    blanks,
                    result_order,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    self.guild_id,
                    author_id,
                    author_name,
                    result.game_number,
                    result.score,
                    result.krillions,
                    result.deep_cuts,
                    result.rares,
                    result.schoolers,
                    result.clevers,
                    result.planktons,
                    result.empties,
                    ''.join(c.category[0] for c in result.answers),
                ),
            )

            await db.commit()

    async def scoreboard(self: Self, style: Literal['daily', 'all_time'] = 'all_time', count: Optional[int] = None):
        async with aiosqlite.connect(self.db_file_location) as db:
            date_filter = '''
                WHERE created_at >= datetime('now', 'start of day', '+4 hours')
                AND created_at < datetime('now', '+1 day', 'start of day', '+4 hours')
            '''
            cursor_text = f"""
                SELECT * FROM krillionResults
                {date_filter if style == 'daily' else ''}
                ORDER BY score DESC, krillions DESC, deep_cuts DESC, rares DESC, schoolers DESC, clevers DESC, planktons DESC, blanks DESC
            """
            cursor = await db.execute(
                cursor_text
            )
            if count:
                return await cursor.fetchmany(count)
            return await cursor.fetchall()

    async def best_game(self: Self, user_id: int):
        async with aiosqlite.connect(self.db_file_location) as db:
            cursor = await db.execute(
                """
                SELECT * FROM krillionResults
                WHERE author_id = ?
                ORDER BY score DESC, krillions DESC, deep_cuts DESC, rares DESC, schoolers DESC, clevers DESC, planktons DESC, blanks DESC
                LIMIT 1
                """,
                (user_id,)
            )
            return await cursor.fetchone()

    async def aggregate_stats(self: Self, user_id: int):
        async with aiosqlite.connect(self.db_file_location) as db:
            cursor = await db.execute(
                """
                SELECT 
                    SUM(score),
                    SUM(krillions),
                    SUM(deep_cuts),
                    SUM(rares),
                    SUM(schoolers),
                    SUM(clevers),
                    SUM(planktons),
                    SUM(blanks)
                FROM krillionResults
                WHERE author_id = ?
                """,
                (user_id,)
            )
            return await cursor.fetchone()