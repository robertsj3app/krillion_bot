from unittest.mock import AsyncMock
import subprocess

import discord
import pytest

from krillion_bot.blast import (
    build_changelog,
    load_canned_messages,
    main,
    send_notification_blast,
)
from krillion_bot.services.database import DatabaseHandler


def test_load_canned_messages_contains_maintenance_notifications():
    messages = load_canned_messages()

    assert "maintenance_scheduled" in messages
    assert "maintenance_complete" in messages
    assert "changelog" in messages
    assert messages["maintenance_scheduled"]


def test_build_changelog_includes_commit_subjects_after_base_in_order(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")
    (tmp_path / "log.txt").write_text("base", encoding="utf-8")
    git("add", "log.txt")
    git("commit", "-m", "Base commit")
    base = git("rev-parse", "HEAD")

    (tmp_path / "log.txt").write_text("first", encoding="utf-8")
    git("commit", "-am", "First change")
    (tmp_path / "log.txt").write_text("second", encoding="utf-8")
    git("commit", "-am", "Second change")

    changelog = build_changelog(base, tmp_path)

    assert changelog.endswith("- First change\n- Second change")
    assert "Base commit" not in changelog


def test_build_changelog_excludes_merge_commits(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test User")
    (tmp_path / "log.txt").write_text("base", encoding="utf-8")
    git("add", "log.txt")
    git("commit", "-m", "Base commit")
    base = git("rev-parse", "HEAD")
    main_branch = git("branch", "--show-current")

    (tmp_path / "log.txt").write_text("main", encoding="utf-8")
    git("commit", "-am", "Main change")
    git("checkout", "-b", "feature")
    (tmp_path / "feature.txt").write_text("feature", encoding="utf-8")
    git("add", "feature.txt")
    git("commit", "-m", "Feature change")
    git("checkout", main_branch)
    git("merge", "--no-ff", "feature", "-m", "Merge feature branch")

    changelog = build_changelog(base, tmp_path)

    assert "Main change" in changelog
    assert "Feature change" in changelog
    assert "Merge feature branch" not in changelog


def test_build_changelog_rejects_an_invalid_commit(tmp_path):
    with pytest.raises(ValueError, match="Unable to read git history"):
        build_changelog("not-a-commit", tmp_path)


def test_unknown_canned_message_reports_available_keys(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--canned", "unknown"])

    assert error.value.code == 2
    assert "maintenance_scheduled" in capsys.readouterr().err


def test_changelog_requires_since_commit(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--canned", "changelog"])

    assert error.value.code == 2
    assert "--canned changelog requires --since COMMIT" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_notification_blast_sends_to_every_configured_channel(monkeypatch):
    channels = [AsyncMock(spec=discord.abc.Messageable) for _ in range(2)]
    client = AsyncMock()
    client.fetch_channel.side_effect = channels
    monkeypatch.setattr(
        DatabaseHandler,
        "get_configured_krillion_channels",
        AsyncMock(return_value=[101, 202]),
    )

    sent, failed = await send_notification_blast(client, "Maintenance notice")

    assert (sent, failed) == (2, 0)
    assert [call.args for call in client.fetch_channel.await_args_list] == [
        (101,),
        (202,),
    ]
    for channel in channels:
        channel.send.assert_awaited_once_with("Maintenance notice")


@pytest.mark.asyncio
async def test_notification_blast_continues_after_a_channel_error(monkeypatch):
    last_channel = AsyncMock(spec=discord.abc.Messageable)
    client = AsyncMock()
    client.fetch_channel.side_effect = [
        discord.NotFound(response=AsyncMock(), message="Not found"),
        last_channel,
    ]
    monkeypatch.setattr(
        DatabaseHandler,
        "get_configured_krillion_channels",
        AsyncMock(return_value=[101, 202]),
    )

    sent, failed = await send_notification_blast(client, "Maintenance notice")

    assert (sent, failed) == (1, 1)
    last_channel.send.assert_awaited_once_with("Maintenance notice")


@pytest.mark.asyncio
async def test_notification_blast_fails_when_no_channels_are_configured(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr(
        DatabaseHandler,
        "get_configured_krillion_channels",
        AsyncMock(return_value=[]),
    )

    assert await send_notification_blast(client, "Maintenance notice") == (0, 1)
    client.fetch_channel.assert_not_awaited()
