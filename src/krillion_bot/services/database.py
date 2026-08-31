import sqlite3
import aiosqlite
import functools
from typing import Self, Optional, Literal
from krillion_bot.services.parser import KrillionResult
from krillion_bot.utils import current_game_number

class DoubleSubmissionException(Exception):
    ...

class DatabaseHandler:

    DEFAULT_DB_FILE_LOCATION = ""
    db_file_location: str

    def __init__(self: Self, guild_id: int) -> None:
        self.guild_id = guild_id

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

        db.execute("""
            CREATE TABLE IF NOT EXISTS guildSettings (
                guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
                krillion_channel_id INTEGER
            )
        """)

        db.commit()

    async def setup_guild(self: Self) -> None:
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("INSERT INTO guildSettings (guild_id, krillion_channel_id) VALUES (?, ?)", (self.guild_id, None))
            await db.commit()

    async def remove_guild(self: Self) -> None:
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("DELETE FROM guildSettings WHERE guild_id = ?", (self.guild_id,))
            await db.commit()
            await self.wipe()

    async def set_krillion_channel(self: Self, channel_id: int) -> None:
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("INSERT OR REPLACE INTO guildSettings (guild_id, krillion_channel_id) VALUES (?, ?)", (self.guild_id, channel_id))
            await db.commit()

    async def get_krillion_channel(self: Self) -> Optional[int]:
        async with aiosqlite.connect(self.db_file_location) as db:
            cursor = await db.execute("SELECT krillion_channel_id FROM guildSettings WHERE guild_id = ?", (self.guild_id,))
            result = await cursor.fetchone()

        if result is not None:
            if result[0] is None:
                return None
            return int(result[0])

    async def wipe(self: Self):
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("DELETE FROM krillionResults WHERE guild_id = ?", (self.guild_id,))
            await db.commit()

    async def wipe_all(self: Self):
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("DELETE FROM krillionResults;")
            await db.commit()

    async def check_user_submitted_today(self: Self, author_id: int):
        return await self.check_user_submitted_game(author_id, current_game_number())

    async def check_user_submitted_game(self: Self, author_id: int, game_number: int):
        async with aiosqlite.connect(self.db_file_location) as db:
            cursor = await db.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM krillionResults
                    WHERE guild_id = ?
                    AND author_id = ?
                    AND game_number = ?
                )
                """,
                (self.guild_id, author_id, game_number),
            )
            result = await cursor.fetchone()
        return result is not None and bool(result[0])

    async def log_result(self: Self, author_id: int, author_name: str, result: KrillionResult, force: bool = False):
        async with aiosqlite.connect(self.db_file_location) as db:

            if await self.check_user_submitted_game(author_id, result.game_number):
                raise DoubleSubmissionException(f"Cannot submit a second Krillion result for user {author_name} on the same day!")

            if not force and result.game_number != current_game_number():
                raise DoubleSubmissionException(f"Cannot log a result for a game other than today's current!")
            
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

    async def scoreboard(
        self: Self,
        style: Literal["daily", "all_time"] | int = "all_time",
        count: Optional[int] = None,
    ):
        if not isinstance(style, (str, int)) or (
            isinstance(style, str) and style not in {"daily", "all_time"}
        ):
            raise ValueError(
                "style must be 'daily', 'all_time', or an integer game number"
            )

        if isinstance(style, int) and style < 0:
            raise ValueError("game number must be non-negative")

        if count is not None and (not isinstance(count, int) or count <= 0):
            raise ValueError("count must be a positive integer")

        async with aiosqlite.connect(self.db_file_location) as db:
            params = ()

            if style == "daily":
                where_clause = "WHERE game_number = ?"
                params = (current_game_number(),)
            elif isinstance(style, int):
                where_clause = "WHERE game_number = ?"
                params = (style,)
            else:
                where_clause = ""

            cursor = await db.execute(
                f"""
                SELECT * FROM krillionResults
                {where_clause}
                ORDER BY
                    score DESC,
                    krillions DESC,
                    deep_cuts DESC,
                    rares DESC,
                    schoolers DESC,
                    clevers DESC,
                    planktons DESC,
                    blanks DESC
                """,
                params,
            )

            if count is not None:
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

    async def latest_game(self: Self, user_id: int):
            async with aiosqlite.connect(self.db_file_location) as db:
                cursor = await db.execute(
                    """
                    SELECT * FROM krillionResults
                    WHERE author_id = ?
                    ORDER BY game_number DESC
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
                    MAX(id),
                    guild_id,
                    author_id,
                    author_name,
                    MAX(game_number),
                    SUM(score),
                    SUM(krillions),
                    SUM(deep_cuts),
                    SUM(rares),
                    SUM(schoolers),
                    SUM(clevers),
                    SUM(planktons),
                    SUM(blanks),
                    MAX(result_order),
                    MAX(created_at)
                FROM krillionResults
                WHERE author_id = ?
                GROUP BY guild_id, author_id, author_name
                """,
                (user_id,)
            )
            return await cursor.fetchone()