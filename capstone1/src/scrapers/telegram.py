"""Telegram channel scraper via Telethon."""

from __future__ import annotations

import asyncio
import os

from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

from .base import BaseScraper, console
from .progress import make_task_progress


class TelegramScraper(BaseScraper):
    """Scrape public Telegram channels using Telethon."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        output_dir: str = "data/raw",
        max_records: int = 10000,
    ) -> None:
        super().__init__(output_dir=output_dir, max_records=max_records)
        self.phone = phone
        self.client = TelegramClient("telegram_session", api_id, api_hash)

    async def _fetch_channel_messages(
        self,
        channel_username: str,
        limit: int,
        offset_id: int | None = None,
    ) -> list[dict]:
        """Fetch messages from one channel (client must already be connected)."""
        entity = await self.client.get_entity(channel_username)
        full_channel = await self.client(GetFullChannelRequest(channel=entity))
        subscribers = full_channel.full_chat.participants_count

        records: list[dict] = []
        iter_kwargs: dict = {}
        if offset_id is not None:
            iter_kwargs["offset_id"] = offset_id

        scanned = 0
        max_scan = limit * 15
        async for message in self.client.iter_messages(entity, **iter_kwargs):
            scanned += 1
            if scanned > max_scan:
                break
            if not message.text:
                continue

            reactions_count = 0
            if message.reactions:
                reactions_count = sum(r.count for r in message.reactions.results)

            records.append(
                {
                    "message_id": message.id,
                    "channel_name": entity.title,
                    "channel_username": channel_username,
                    "channel_subscribers": subscribers,
                    "date": message.date.isoformat(),
                    "text": message.text,
                    "views": message.views or 0,
                    "forwards": message.forwards or 0,
                    "replies_count": message.replies.replies if message.replies else 0,
                    "reactions_count": reactions_count,
                    "has_media": message.media is not None,
                    "has_url": message.entities is not None
                    and any(hasattr(e, "url") for e in message.entities),
                    "platform": "telegram",
                    "collection_date": BaseScraper.timestamp(),
                }
            )
            if len(records) >= limit:
                break

        console.print(
            f"Collected {len(records)} messages from {channel_username!r}"
            + (f" (older batch, offset {offset_id})" if offset_id else ""),
            style="green",
        )
        return records

    async def async_scrape(self, channel_username: str, limit: int | None = None) -> list[dict]:
        """Connect, scrape one channel, disconnect."""
        await self.client.start(phone=self.phone)
        try:
            return await self._fetch_channel_messages(
                channel_username, limit or self.max_records
            )
        finally:
            await self.client.disconnect()

    async def _async_scrape_channels(self, channels: list[str]) -> list[dict]:
        """Scrape all channels in one session; backfill until max_records or exhausted."""
        all_records: list[dict] = []
        seen: set[tuple] = set()
        channel_offset: dict[str, int] = {}
        exhausted: set[str] = set()

        await self.client.start(phone=self.phone)
        try:
            with make_task_progress("Telegram channels") as progress:
                task = progress.add_task(
                    f"Target {self.max_records:,} messages",
                    total=self.max_records,
                )
                round_num = 0
                while len(all_records) < self.max_records and len(exhausted) < len(channels):
                    round_num += 1
                    active = [c for c in channels if c not in exhausted]
                    if not active:
                        break

                    for index, channel in enumerate(active):
                        remaining = self.max_records - len(all_records)
                        if remaining <= 0:
                            break

                        channels_left = len(active) - index
                        per_channel = max(1, min(remaining, remaining // channels_left))
                        offset_id = channel_offset.get(channel)

                        progress.update(
                            task,
                            description=(
                                f"Round {round_num} · {channel} "
                                f"({len(all_records):,}/{self.max_records:,}, "
                                f"batch {per_channel:,})"
                            ),
                        )

                        try:
                            batch = await self._fetch_channel_messages(
                                channel, per_channel, offset_id=offset_id
                            )
                        except Exception as exc:
                            console.print(f"Failed channel {channel!r}: {exc}", style="red")
                            exhausted.add(channel)
                            continue

                        new_count = 0
                        oldest_id: int | None = None
                        for record in batch:
                            msg_id = record.get("message_id")
                            if msg_id is not None:
                                oldest_id = (
                                    msg_id
                                    if oldest_id is None
                                    else min(oldest_id, msg_id)
                                )
                            key = (msg_id, record.get("channel_username"))
                            if key[0] is not None:
                                if key in seen:
                                    continue
                                seen.add(key)
                            all_records.append(record)
                            new_count += 1

                        if oldest_id is not None:
                            channel_offset[channel] = oldest_id

                        if new_count == 0:
                            exhausted.add(channel)
                        else:
                            progress.update(task, completed=min(len(all_records), self.max_records))

                    if round_num >= 20:
                        console.print("Stopped after 20 rounds (safety limit).", style="yellow")
                        break
        finally:
            await self.client.disconnect()

        return all_records[: self.max_records]

    def scrape(self, query: str, **kwargs) -> list[dict]:
        """Sync wrapper for a single channel."""
        limit = kwargs.get("limit")
        return asyncio.run(self.async_scrape(query, limit=limit))

    def scrape_channels(
        self,
        channels: list[str],
        filename_prefix: str = "telegram",
    ) -> str:
        """Scrape multiple channels with one Telegram session and event loop."""
        all_records = asyncio.run(self._async_scrape_channels(channels))

        if not all_records:
            console.print("No messages collected.", style="yellow")
            return ""

        return self.save(all_records, f"{filename_prefix}_raw")


if __name__ == "__main__":
    try:
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        phone = os.getenv("TELEGRAM_PHONE")

        if not all([api_id, api_hash, phone]):
            console.print(
                "TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE must be set",
                style="red",
            )
            console.print("Check your Telegram credentials in .env", style="yellow")
            raise SystemExit(1)

        scraper = TelegramScraper(int(api_id), api_hash, phone)
        results = scraper.scrape("nexta_tv", limit=20)
        if results:
            console.print("First result:", style="green")
            print(results[0])
        else:
            console.print("No messages returned.", style="yellow")
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"Scrape failed: {exc}", style="red")
        console.print(
            "Check TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE in .env "
            "and network connectivity.",
            style="yellow",
        )
        raise SystemExit(1) from exc
