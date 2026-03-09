# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import re
import string
import time
import zipfile

import aiohttp
from dotenv import load_dotenv
from rich.progress import Progress
from telethon import TelegramClient, events

# ─── Constants ────────────────────────────────────────────────────────────────

MEDIA_DIR = "Media"
BASE_DIR = os.path.realpath(os.path.dirname(__file__))
ZIP_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".mp4", ".avi", ".mkv"}

# ─── Setup ────────────────────────────────────────────────────────────────────

os.makedirs(MEDIA_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

def load_config() -> tuple[int, str, int]:
    """Load credentials from environment variables (.env file)."""
    load_dotenv()

    api_id    = os.getenv("TELEGRAM_API_ID")
    api_hash  = os.getenv("TELEGRAM_API_HASH")
    admin_id  = os.getenv("TELEGRAM_ADMIN_ID")

    missing = [
        name for name, val in {
            "TELEGRAM_API_ID": api_id,
            "TELEGRAM_API_HASH": api_hash,
            "TELEGRAM_ADMIN_ID": admin_id,
        }.items() if not val
    ]
    if missing:
        raise ValueError(f"Missing variables in .env: {', '.join(missing)}")

    return int(api_id), api_hash, int(admin_id)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def safe_path(user_input: str, allowed_dir: str) -> str | None:
    """
    Resolve a user-supplied path and verify it stays within allowed_dir.
    Returns the absolute path, or None if the path escapes the directory.
    """
    full_path = os.path.realpath(os.path.join(allowed_dir, user_input))
    if full_path.startswith(allowed_dir + os.sep) or full_path == allowed_dir:
        return full_path
    return None


def sanitize_username(username: str) -> str:
    """Remove any character that isn't alphanumeric, underscore or hyphen."""
    return re.sub(r"[^\w\-]", "_", username)


class RichProgressBar:
    """Custom progress bar for download callbacks using rich."""

    def __init__(self, total: int):
        self.progress = Progress()
        self.task = self.progress.add_task("[cyan]Downloading...", total=total)
        self.progress.start()

    def __call__(self, current: int, total: int):
        self.progress.update(self.task, completed=current)

    def close(self):
        self.progress.stop()

# ─── Bot ──────────────────────────────────────────────────────────────────────

class Bot:
    def __init__(self, api_id: int, api_hash: str, admin_id: int):
        self.api_id   = api_id
        self.api_hash = api_hash
        self.admin_id = admin_id
        SESSION_PATH = os.path.join(os.getenv("SESSION_DIR", "."), "TSMD")
        self.client  = TelegramClient(SESSION_PATH, api_id, api_hash)
        self._letter_iter = iter(string.ascii_uppercase)

    # ── Utilities ─────────────────────────────────────────────────────────────

    async def is_admin(self, event) -> bool:
        return event.sender_id == self.admin_id

    def get_next_letter(self) -> str:
        try:
            return next(self._letter_iter)
        except StopIteration:
            self._letter_iter = iter(string.ascii_uppercase)
            return next(self._letter_iter)

    # ── Handlers ──────────────────────────────────────────────────────────────

    async def show_welcome(self, event):
        if not await self.is_admin(event):
            return
        await event.respond(
            "Welcome to the Self-Destructing Media Downloader!\n\n"
            "Available commands:\n"
            "/ping    - Check if the bot is alive and measure ping time.\n"
            "/status  - Get the number of downloaded files in the media folder.\n"
            "/files   - List all files in the media folder.\n"
            "/check   - List current files in the media folder.\n"
            "/download [file_path] - Send a specific file to you.\n"
            "/delete  [file_path]  - Delete a specific file.\n"
            "/all     - Send all media files to you.\n"
            "/zip     - Create and send a zip of all media files.\n"
        )

    async def handle_ping(self, event):
        if not await self.is_admin(event):
            return
        try:
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.google.com"):
                    ping_ms = round((time.time() - start) * 1000)
            await event.respond(f"Bot is alive! Ping: {ping_ms} ms")
        except Exception as e:
            logger.error(f"Ping error: {e}")
            await event.respond(f"Failed to measure ping: {e}")

    async def handle_status(self, event):
        if not await self.is_admin(event):
            return
        photos, videos = 0, 0
        for root, dirs, files in os.walk(MEDIA_DIR):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in {".jpg", ".jpeg", ".png"}:
                    photos += 1
                elif ext in {".mp4", ".avi", ".mkv"}:
                    videos += 1
        await event.respond(f"Bot Status:\nPhotos: {photos}\nVideos: {videos}")

    async def handle_files(self, event):
        if not await self.is_admin(event):
            return
        lines = []
        for root, dirs, files in os.walk(MEDIA_DIR):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            lines.append(f"Directory: {root}")
            for file_name in files:
                if not file_name.startswith("."):
                    lines.append(f"    File: {os.path.join(root, file_name)}")
        await event.respond("\n".join(lines) if lines else "No files found.")

    async def handle_check(self, event):
        if not await self.is_admin(event):
            return
        current_files = [
            os.path.join(root, file)
            for root, dirs, files in os.walk(MEDIA_DIR)
            for file in files
        ]
        if current_files:
            await event.respond("Current files:\n" + "\n".join(current_files))
        else:
            await event.respond("No files found in the media folder.")

    async def handle_download(self, event):
        if not await self.is_admin(event):
            return
        try:
            user_input = event.pattern_match.group(1).strip()
            file_path  = safe_path(user_input, BASE_DIR)

            if file_path is None:
                logger.warning(f"Path traversal attempt blocked: {user_input}")
                await event.respond("⛔ Unauthorized path.")
                return

            if os.path.isfile(file_path):
                await self.client.send_file(event.sender_id, file_path)
                await event.respond("File sent successfully!")
            else:
                await event.respond("File not found.")
        except Exception as e:
            logger.error(f"Error in /download: {e}")
            await event.respond(f"Error: {e}")

    async def handle_delete(self, event):
        if not await self.is_admin(event):
            return
        try:
            user_input = event.pattern_match.group(1).strip()
            file_path  = safe_path(user_input, BASE_DIR)

            if file_path is None:
                logger.warning(f"Path traversal attempt blocked: {user_input}")
                await event.respond("⛔ Unauthorized path.")
                return

            if os.path.isfile(file_path):
                os.remove(file_path)
                await event.respond("File deleted successfully!")
            else:
                await event.respond("File not found.")
        except Exception as e:
            logger.error(f"Error in /delete: {e}")
            await event.respond(f"Error: {e}")

    async def handle_all(self, event):
        if not await self.is_admin(event):
            return
        try:
            media_files = [
                os.path.join(root, file)
                for root, dirs, files in os.walk(MEDIA_DIR)
                for file in files
                if os.path.splitext(file)[1].lower() in ZIP_ALLOWED_EXTENSIONS
            ]
            if media_files:
                for media_file in media_files:
                    await self.client.send_file(event.sender_id, media_file)
                await event.respond("All media files sent successfully!")
            else:
                await event.respond("No media files found.")
        except Exception as e:
            logger.error(f"Error in /all: {e}")
            await event.respond(f"Error: {e}")

    async def handle_zip(self, event):
        if not await self.is_admin(event):
            return
        try:
            zip_filename = "media_files.zip"
            with zipfile.ZipFile(zip_filename, "w") as zipf:
                for root, dirs, files in os.walk(MEDIA_DIR):
                    for file_name in files:
                        if os.path.splitext(file_name)[1].lower() in ZIP_ALLOWED_EXTENSIONS:
                            full_path = os.path.join(root, file_name)
                            zipf.write(full_path, os.path.relpath(full_path, MEDIA_DIR))

            await self.client.send_file(event.sender_id, zip_filename)
            await event.respond("ZIP file created and sent successfully!")
            os.remove(zip_filename)
        except Exception as e:
            logger.error(f"Error in /zip: {e}")
            await event.respond(f"Error creating zip file: {e}")

    async def downloader(self, event):
        """Automatically download received self-destructing media."""
        me = await self.client.get_me()
        if event.sender_id == me.id:
            return

        sender      = await event.get_sender()
        raw_username = sender.username if sender.username else "unknown"
        username    = sanitize_username(raw_username)
        user_id     = str(sender.id) if sender.id else "unknown"

        # Reuse existing folder for this user if it exists
        existing_folder = next(
            (f for f in os.listdir(MEDIA_DIR) if f"@{username} - {user_id}" in f),
            None,
        )
        if existing_folder:
            user_folder_name = existing_folder
        else:
            letter = self.get_next_letter()
            user_folder_name = f"{letter} - @{username} - {user_id}"

        user_folder_path = os.path.join(MEDIA_DIR, user_folder_name)
        os.makedirs(user_folder_path, exist_ok=True)

        logger.info(f"Received media from @{username} (ID: {user_id}). Downloading...")
        try:
            progress_bar = RichProgressBar(event.file.size)
            result = await event.download_media(
                file=user_folder_path,
                progress_callback=progress_bar,
            )
            progress_bar.close()

            media_type = "photo" if event.photo else "video"
            logger.info(f"{media_type.capitalize()} downloaded from @{username} (ID: {user_id})")
            await self.client.send_file(
                "me", result, caption=f"Downloaded from @{raw_username}"
            )
        except Exception as e:
            logger.error(f"Failed to download media from @{username}: {e}")
            await event.respond(f"Error downloading media: {e}")

    # ── Registration ──────────────────────────────────────────────────────────

    def register_handlers(self):
        add = self.client.add_event_handler
        priv = lambda e: e.is_private  # noqa: E731

        add(self.show_welcome,    events.NewMessage(func=lambda e: priv(e) and e.text == "/help"))
        add(self.handle_ping,     events.NewMessage(func=lambda e: priv(e) and e.text == "/ping"))
        add(self.handle_status,   events.NewMessage(func=lambda e: priv(e) and e.text == "/status"))
        add(self.handle_files,    events.NewMessage(func=lambda e: priv(e) and e.text == "/files"))
        add(self.handle_check,    events.NewMessage(func=lambda e: priv(e) and e.text == "/check"))
        add(self.handle_all,      events.NewMessage(func=lambda e: priv(e) and e.text == "/all"))
        add(self.handle_zip,      events.NewMessage(func=lambda e: priv(e) and e.text == "/zip"))
        add(self.handle_download, events.NewMessage(pattern=r"/download (.+)", func=priv))
        add(self.handle_delete,   events.NewMessage(pattern=r"/delete (.+)",   func=priv))
        add(self.downloader,      events.NewMessage(
            func=lambda e: priv(e) and (e.photo or e.video) and e.media_unread
        ))

# ─── Entry point ──────────────────────────────────────────────────────────────

async def main():
    api_id, api_hash, admin_id = load_config()
    bot = Bot(api_id, api_hash, admin_id)
    bot.register_handlers()

    await bot.client.start()
    logger.info("Bot is running...")
    await bot.client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())