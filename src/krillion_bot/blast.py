"""Send one-off notifications to the bot's configured Krillion channels."""

import argparse
import asyncio
import json
import logging
import os
import subprocess
from importlib.resources import files
from pathlib import Path
from typing import Any

import discord
from dotenv import load_dotenv

from krillion_bot.services.database import DatabaseHandler

LOGGER = logging.getLogger(__name__)


def load_canned_messages() -> dict[str, str]:
    """Load predefined messages bundled with the package."""
    try:
        with files("krillion_bot.data").joinpath("canned_blasts.json").open(
            encoding="utf-8"
        ) as canned_file:
            messages: Any = json.load(canned_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Unable to load canned messages: {error}") from error

    if not isinstance(messages, dict) or not all(
        isinstance(key, str)
        and isinstance(message, str)
        and message.strip()
        for key, message in messages.items()
    ):
        raise ValueError(
            "Canned messages must be a JSON object mapping keys to non-empty strings."
        )
    return messages


def build_changelog(since: str, repository: Path | None = None) -> str:
    """Build a changelog from commit subjects after a given commit through HEAD."""
    repository = repository or Path(__file__).resolve().parents[2]
    revision = f"{since}^{{commit}}"
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "--end-of-options", revision],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            ["git", "log", "--reverse", "--format=%s", f"{revision}..HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise ValueError("Git must be installed to generate a changelog.") from error
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or "unknown git error"
        raise ValueError(f"Unable to read git history: {details}") from error

    messages = load_canned_messages()
    subjects = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    changelog = messages["changelog"]
    if subjects:
        changelog += "\n" + "\n".join(f"- {subject}" for subject in subjects)
    else:
        changelog += "\nNo commits since the specified commit."
    return changelog


async def send_notification_blast(
    client: discord.Client,
    message: str,
) -> tuple[int, int]:
    """Send a message to every configured channel and return success/failure counts."""
    channel_ids = await DatabaseHandler.get_configured_krillion_channels()
    if not channel_ids:
        LOGGER.error("No configured Krillion channels found; no messages were sent.")
        return 0, 1

    sent = 0
    failed = 0
    for channel_id in channel_ids:
        try:
            channel = await client.fetch_channel(channel_id)
            if not isinstance(channel, discord.abc.Messageable):
                LOGGER.error("Configured channel %s cannot receive messages.", channel_id)
                failed += 1
                continue
            await channel.send(message)
            sent += 1
            LOGGER.info("Sent notification to channel %s.", channel_id)
        except (discord.DiscordException, OSError):
            LOGGER.exception("Failed to send notification to channel %s.", channel_id)
            failed += 1

    LOGGER.info("Notification blast complete: %s sent, %s failed.", sent, failed)
    return sent, failed


async def _run(message: str, token: str, database_path: str) -> int:
    DatabaseHandler.initial_setup(database_path)
    client = discord.Client(intents=discord.Intents.none())
    try:
        await client.login(token)
        _, failed = await send_notification_blast(client, message)
        return 1 if failed else 0
    finally:
        await client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Send a notification to every configured Krillion channel."
    )
    message_source = parser.add_mutually_exclusive_group(required=True)
    message_source.add_argument(
        "--message",
        help="The notification text to send.",
    )
    message_source.add_argument(
        "--canned",
        metavar="KEY",
        help="Send a predefined message by key (see canned_blasts.json).",
    )
    parser.add_argument(
        "--since",
        metavar="COMMIT",
        help="For --canned changelog, include commits after this commit through HEAD.",
    )
    args = parser.parse_args(argv)

    if args.canned is not None:
        try:
            canned_messages = load_canned_messages()
        except ValueError as error:
            parser.error(str(error))
        if args.canned not in canned_messages:
            keys = ", ".join(sorted(canned_messages)) or "(none)"
            parser.error(f"Unknown canned message {args.canned!r}. Available keys: {keys}")
        if args.canned == "changelog":
            if not args.since:
                parser.error("--canned changelog requires --since COMMIT.")
            try:
                message = build_changelog(args.since)
            except ValueError as error:
                parser.error(str(error))
        else:
            if args.since:
                parser.error("--since is only valid with --canned changelog.")
            message = canned_messages[args.canned]
    else:
        if args.since:
            parser.error("--since is only valid with --canned changelog.")
        message = args.message

    if not message.strip():
        parser.error("The message must not be empty.")
    if len(message) > 2000:
        parser.error("The message must be 2000 characters or fewer.")

    load_dotenv()
    try:
        token = os.environ["DISCORD_TOKEN"]
        database_path = os.environ["DB_FILE_LOCATION"]
    except KeyError as error:
        parser.error(f"Required environment variable {error.args[0]} is not set.")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    return asyncio.run(_run(message, token, database_path))


if __name__ == "__main__":
    raise SystemExit(main())
