import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found. Add it in Railway Variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

import aiosqlite
searching = set()
waiting = set()
chat_pairs = {}
rating_targets = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome! Use /find to chat with a stranger.")

@dp.message(Command("find"))
async def find(message: types.Message):
    uid = message.from_user.id

    # If user already chatting
    if uid in pairs:
        await message.answer("You are already chatting. Use /next or /stop.")
        return

    # If user is already in waiting
    if uid in waiting:
        await message.answer("You're already searching. Please wait...")
        return

    # Try to match with anyone in waiting pool
    # Make a list copy to avoid modifying while iterating
    for other in list(waiting):
        if other != uid:
            # found someone
            waiting.remove(other)

            pairs[uid] = other
            pairs[other] = uid

            await bot.send_message(other, "🔗 Connected to a stranger!")
            await message.answer("🔗 Connected to a stranger!")
            return

    # Otherwise put this user into waiting pool
    waiting.add(uid)
    await message.answer("🔍 Searching for a partner...")

@dp.message(Command("stop"))
async def stop_chat(message: types.Message):
    uid = message.from_user.id

    # If user is currently in a chat
    if uid in pairs:
        partner = pairs[uid]

        # Remove both sides of the chat
        del pairs[partner]
        del pairs[uid]

        # Tell the partner
        await bot.send_message(partner, "Your partner disconnected.")

        # Set up rating targets
        rating_targets[partner] = uid
        rating_targets[uid] = partner

        # Ask both to rate each other
        await bot.send_message(partner, "Rate your partner: /rate 1–5")
        await message.answer("Rate your partner: /rate 1–5")
        return

    # If user was searching for a match but not in a chat
    if uid in waiting:
        waiting.remove(uid)
        await message.answer("Stopped searching. Use /find to search again.")
        return

    # Otherwise user not in chat or searching
    await message.answer("You are not in a chat. Use /find to start.")

@dp.message(Command("next"))
async def next_chat(message: types.Message):
    uid = message.from_user.id

    # If user is currently in a chat
    if uid in pairs:
        partner = pairs[uid]

        # remove chat
        del pairs[partner]
        del pairs[uid]

        await bot.send_message(partner, "Your partner left the chat.")

        # add partner back to waiting if not already in
        if partner not in waiting:
            waiting.add(partner)

    # If user already searching
    if uid in waiting:
        await message.answer("You're already searching. Please wait...")
        return

    # Try matching immediately
    for other in list(waiting):
        if other != uid:
            waiting.remove(other)

            pairs[uid] = other
            pairs[other] = uid

            await bot.send_message(other, "🔗 Connected to a stranger!")
            await message.answer("🔗 Connected to a stranger!")
            return

    # Otherwise put user in waiting
    waiting.add(uid)
    await message.answer("🔍 Searching for a partner...")

@dp.message(lambda m: m.text and m.text.startswith("/rate "))
async def rate_handler(message: types.Message):
    parts = message.text.split(" ", 1)
    if len(parts) != 2:
        await message.answer("Usage: /rate <1–5>")
        return

    try:
        score = int(parts[1])
    except ValueError:
        await message.answer("Please enter a number from 1 to 5.")
        return

    if score < 1 or score > 5:
        await message.answer("Rating must be between 1 and 5.")
        return

    uid = message.from_user.id

    if uid not in rating_targets:
        await message.answer("You have no one to rate right now.")
        return

    # Save and clear
    target = rating_targets.pop(uid)
    await save_rating(target, score)
    await message.answer(f"Thanks! You rated your partner {score}⭐")

@dp.message()
async def relay(message: types.Message):
    uid = message.from_user.id
    if uid in pairs:
        partner = pairs[uid]
        await bot.send_message(partner, message.text)
    else:
        await message.answer("Use /find to start chatting.")

from database import init_db
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
