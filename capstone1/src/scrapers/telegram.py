# telegram telethon

from __future__ import annotations

import asyncio
import os

from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

from .base import BaseScraper, console
from .progress import make_task_progress


def normalize_phone(phone: str) -> str:
    # phone to +country e164 format
    cleaned = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


class TelegramScraper(BaseScraper):
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        output_dir: str = "data/raw",
        max_records: int = 15000,
    ) -> None:
        super().__init__(output_dir=output_dir, max_records=max_records)
        self.phone = normalize_phone(phone)
        self.client = TelegramClient("telegram_session", api_id, api_hash)

    async def _start_client(self) -> None:
        await self.client.connect()
        if await self.client.is_user_authorized():
            return

        force_sms = os.getenv("TELEGRAM_FORCE_SMS", "").lower() in ("1", "true", "yes")
        console.print(
            f"Telegram login for {self.phone}",
            style="cyan",
        )
        console.print(
            "Code is sent to the Telegram app (chat «Telegram» / «Login code»), not SMS.",
            style="yellow",
        )
        if force_sms:
            console.print("TELEGRAM_FORCE_SMS=1 — requesting SMS delivery.", style="yellow")
        else:
            console.print(
                "If no code in the app, set TELEGRAM_FORCE_SMS=1 in .env and retry.",
                style="dim",
            )

        await self.client.start(phone=self.phone, force_sms=force_sms)
        console.print("Telegram session saved (telegram_session.session).", style="green")

    async def _fetch_channel_messages(
        self,
        channel_username: str,
        limit: int,
        offset_id: int | None = None,
    ) -> list[dict]:
        entity = await self.client.get_entity(channel_username)
        full_channel = await self.client(GetFullChannelRequest(channel=entity))
        subscribers = full_channel.full_chat.participants_count

        records: list[dict] = []
        iter_kwargs: dict = {}
        if offset_id is not None:
            iter_kwargs["offset_id"] = offset_id

        scanned = 0
        max_scan = limit * 15  # cap scans when channel has mostly media/no text
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
        await self._start_client()
        try:
            return await self._fetch_channel_messages(
                channel_username, limit or self.max_records
            )
        finally:
            await self.client.disconnect()

    async def _async_scrape_channels(
        self,
        channels: list[str],
        filename_prefix: str,
        resume: bool = False,
    ) -> list[dict]:
        all_records: list[dict] = []
        seen: set[tuple] = set()
        channel_offset: dict[str, int] = {}
        exhausted: set[str] = set()

        if resume:
            checkpoint = self.load_checkpoint(filename_prefix)
            if checkpoint:
                all_records, _, _, meta = checkpoint
                for record in all_records:
                    key = (record.get("message_id"), record.get("channel_username"))
                    if key[0] is not None:
                        seen.add(key)
                channel_offset = {
                    k: int(v) for k, v in (meta.get("channel_offset") or {}).items()
                }
                exhausted = set(meta.get("exhausted") or [])
                console.print(
                    f"Resuming Telegram from checkpoint: {len(all_records):,} records",
                    style="cyan",
                )

        await self._start_client()
        try:
            with make_task_progress("Telegram channels") as progress:
                task = progress.add_task(
                    f"Target {self.max_records:,} messages",
                    total=self.max_records,
                    completed=min(len(all_records), self.max_records),
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

                        self.save_checkpoint(
                            all_records[: self.max_records],
                            filename_prefix,
                            completed_queries=sorted(exhausted),
                            total_queries=len(channels),
                            extra={
                                "channel_offset": channel_offset,
                                "exhausted": sorted(exhausted),
                            },
                        )

                    if round_num >= 20:
                        console.print("Stopped after 20 rounds (safety limit).", style="yellow")
                        break
        finally:
            await self.client.disconnect()

        return all_records[: self.max_records]

    def scrape(self, query: str, **kwargs) -> list[dict]:
        limit = kwargs.get("limit")
        return asyncio.run(self.async_scrape(query, limit=limit))

    def scrape_channels(
        self,
        channels: list[str],
        filename_prefix: str = "telegram",
        resume: bool = False,
    ) -> str:
        all_records = asyncio.run(
            self._async_scrape_channels(channels, filename_prefix, resume=resume)
        )

        if not all_records:
            console.print("No messages collected.", style="yellow")
            return ""

        return self.save(all_records, f"{filename_prefix}_raw")

    async def async_login(self) -> None:
        try:
            await self._start_client()
        finally:
            await self.client.disconnect()

    def login(self) -> None:
        asyncio.run(self.async_login())


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
