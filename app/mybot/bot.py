#!/usr/bin/env -S uv run
"""Telegram bot — replies to direct messages and group mentions."""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-telegram-bot>=20.0",
# ]
# ///

import os

from telegram import Update
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("BOT_TOKEN environment variable is required")

REPLY_TEXT = "pong"


async def handle_message(update: Update, context):
    if not update.message or not update.message.text:
        return

    chat = update.effective_chat
    if not chat:
        return

    if chat.type == "private":
        await update.message.reply_text(REPLY_TEXT)
        return

    if chat.type in ("group", "supergroup"):
        bot_username = context.bot.username
        if bot_username and f"@{bot_username.lower()}" in update.message.text.lower():
            await update.message.reply_text(REPLY_TEXT)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
