import sqlite3
import aiosqlite
import functools
from typing import Self, Optional, Literal
from krillion_bot.services.parser import KrillionResult
from krillion_bot.utils import current_game_number

class DoubleSubmissionException(Exception):
    '''
    Special exception type just for database-related errors so I catch only these and correctly
    fail on others. No additional behavior
    '''
    ...

class DatabaseHandler:
    '''
    Handles all behavior related to database access and queries/views. Most bot commands
    will map 1:1 with a related query method here. Do not expose arbitrary sql access to the
    frontend, sanitize everything through python methods here instead.
    
    Attributes:
        db_file_location (str):
            Filepath to an existing SQLite database. Does not create on instantiation,
            creation setup should be done once via `DatabaseHandler.initial_setup()`
        guild_id (int):
            ID for a specific Discord server. Each `DatabaseHandler` is keyed to the server
            whose command calls created it to guard against cross-server data leaks.
    '''
    db_file_location: str
    guild_id: int

    def __init__(self: Self, guild_id: int) -> None:
        self.guild_id = guild_id

    @classmethod
    def initial_setup(cls, db_file_location: str) -> None:
        '''
        Global class level setup. All instances should point to the same
        database. Concurrent access is handled after the fact using aiosqlite.
        
        Args:
            db_file_location (str):
                Filepath to read/create the sqlite database
                
        Returns:
            None
        '''
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
        '''
        Run guild setup flow. Creates an entry for the server in the guildSettings table.
        '''
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("INSERT INTO guildSettings (guild_id, krillion_channel_id) VALUES (?, ?)", (self.guild_id, None))
            await db.commit()

    async def remove_guild(self: Self) -> None:
        '''
        Run guild removal flow. Deletes settings from guildSettings table, then
        removes all krillionResults associated wtih that server.
        '''
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("DELETE FROM guildSettings WHERE guild_id = ?", (self.guild_id,))
            await db.commit()
            await self.wipe()

    async def set_krillion_channel(self: Self, channel_id: int) -> None:
        '''
        Set the channel the bot should watch for Krillion results.
        
        Args:
            channel_id (int):
                The integer id of the channel to watch.
        
        Returns:
            None
        '''
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("INSERT OR REPLACE INTO guildSettings (guild_id, krillion_channel_id) VALUES (?, ?)", (self.guild_id, channel_id))
            await db.commit()

    async def get_krillion_channel(self: Self) -> Optional[int]:
        '''
        Get the channel the bot should watch for Krillion results.
        
        Returns:
            Integer channel id if one exists in database for `self.guild_id` else None
        '''
        async with aiosqlite.connect(self.db_file_location) as db:
            cursor = await db.execute("SELECT krillion_channel_id FROM guildSettings WHERE guild_id = ?", (self.guild_id,))
            result = await cursor.fetchone()

        if result is not None:
            if result[0] is None:
                return None
            return int(result[0])

    async def wipe(self: Self) -> None:
        '''
        Clear all krillionResults for this handler's guild.
        '''
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("DELETE FROM krillionResults WHERE guild_id = ?", (self.guild_id,))
            await db.commit()

    async def wipe_all(self: Self) -> None:
        '''
        Clear all krillionResults for all guilds. For debug/testing purposes;
        USE WITH CAUTION
        '''
        async with aiosqlite.connect(self.db_file_location) as db:
            await db.execute("DELETE FROM krillionResults;")
            await db.commit()

    async def check_user_submitted_game(self: Self, author_id: int, game_number: int):
        '''
        Check whether the selected user has submitted a Krillion result for the provided
        game number. Note that since the `DatabaseHandler` is keyed to a specific server, 
        this may return differently if called on the same user from different servers.
        
        Args:
            author_id (int): 
                The discord ID of the user to check.
            game_number (int):
                The game number to check for a submission for.
                
        Returns:
            True if a result for `author_id` for `game_number` exists in krillionResults,
            False otherwise
        '''
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

    async def check_user_submitted_today(self: Self, author_id: int) -> bool:
        '''
        Check whether the selected user has submitted a Krillion result for today's dive.
        Note that since the `DatabaseHandler` is keyed to a specific server, this may return 
        differently if called on the same user from different servers.
        
        Args:
            author_id (int): 
                The discord ID of the user to check.
                
        Returns:
            True if a result for `author_id` for `current_game_number()` exists in krillionResults,
            False otherwise
        '''
        return await self.check_user_submitted_game(author_id, current_game_number())

    async def log_result(self: Self, author_id: int, author_name: str, result: KrillionResult, force: bool = False) -> None:
        '''
        Log a Krillion result to the database for the provided user. Disallows multiple submissions for the same
        game number, and by default also disallows submissions for games other than today's current.
        
        Args:
            author_id (int):
                The Discord ID of the user submitting their result.
            author_name (str):
                The display name of the user submitting their result, or the user.mention string. The user.mention
                string is preferred here since it will adjust to the correct display name if names change. Bare names
                are fine for testing.
            result (KrillionResult):
                The parsed KrillionResult object created from the message contents.
            force (bool):
                If True, bypass the "today's-game-only" restriction for logging results. Can be used for testing or
                in the future to allow insertion of historical results by scanning message history.
                
        Returns:
            None
            
        Raises:
            DoubleSubmissionException:
                If a second result is posted for the same user on the same day.
            DoubleSubmissionException:
                If the result's game number does not match today's current game number and `force` is False.
                This should be a different exception type probably.
        '''
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
        '''
        Returns the data needed to populate a scoreboard for this handler's server as an Iterable of sqlite3 Rows.
        
        Args:
            style (Literal["daily", "all_time"] | int):
                Chooses the filtering mode to apply to the database to generate the scoreboard.
                "Daily" mode returns all results for the current game, "All Time" mode returns
                all rows, period, and an integer value returns all results for a specific game.
                
            count (Optional[int]):
                If provided, limits the number of Rows returned. Useful for "Top N" scoreboards.
                
        Returns:
            Iterable of sqlite3 Rows with columns matching the schema of krillionResults
        '''
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
                where_clause = "WHERE game_number = ? AND guild_id = ?"
                params = (current_game_number(), self.guild_id)
            elif isinstance(style, int):
                where_clause = "WHERE game_number = ? AND guild_id = ?"
                params = (style, self.guild_id)
            else:
                where_clause = "WHERE guild_id = ?"
                params = (self.guild_id,)

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
        '''
        Returns the chosen user's highest scoring game.
        
        Args:
            user_id (int):
                The Discord ID of the user to query games for.
        
        Returns:
            sqlite3 Row of the user's best game, or None if no results are found.
        '''
        async with aiosqlite.connect(self.db_file_location) as db:
            cursor = await db.execute(
                """
                SELECT * FROM krillionResults
                WHERE author_id = ? AND guild_id = ?
                ORDER BY score DESC, krillions DESC, deep_cuts DESC, rares DESC, schoolers DESC, clevers DESC, planktons DESC, blanks DESC
                LIMIT 1
                """,
                (user_id, self.guild_id)
            )
            return await cursor.fetchone()

    async def latest_game(self: Self, user_id: int):
            '''
            Returns the chosen user's most recent game.
            
            Args:
                user_id (int):
                    The Discord ID of the user to query games for.
            
            Returns:
                sqlite3 Row of the user's most recent game, or None if no results are found.
            '''
            async with aiosqlite.connect(self.db_file_location) as db:
                cursor = await db.execute(
                    """
                    SELECT * FROM krillionResults
                    WHERE author_id = ? AND guild_id = ?
                    ORDER BY game_number DESC
                    LIMIT 1
                    """,
                    (user_id, self.guild_id)
                )
                return await cursor.fetchone()

    async def aggregate_stats(self: Self, user_id: int):
        '''
        Returns an aggregate of the chosen user's lifetime stats for this server, 
        i.e. total points and total counts of each response category.
        
        Args:
            user_id (int):
                The Discord ID of the user to return lifetime stats for.
        
        Returns:
            sqlite3 Row of the aggregate, or None if no such user exists.
        '''
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
                WHERE author_id = ? AND guild_id = ?
                GROUP BY guild_id, author_id, author_name
                """,
                (user_id, self.guild_id)
            )
            return await cursor.fetchone()