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

    if uid in chat_pairs:
        await message.answer("You are already chatting.")
        return

    if uid in waiting:
        await message.answer("Already searching...")
        return

    if waiting:
        partner = waiting.pop()
        chat_pairs[uid] = partner
        chat_pairs[partner] = uid
        await bot.send_message(partner, "Connected to a stranger!")
        await message.answer("Connected to a stranger!")
    else:
        waiting.add(uid)
        await message.answer("Searching...")

@dp.message(Command("stop"))
async def stop_chat(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "Your partner disconnected.")

        # Set up rating targets so each knows who to rate
        rating_targets[partner] = uid
        rating_targets[uid] = partner

        await bot.send_message(partner, "Rate your partner: /rate <1–5>")
        await message.answer("Rate your partner: /rate <1–5>")
        return

        await message.answer("You were not chatting. Use /find to start.")

@dp.message(Command("next"))
async def next_chat(message: types.Message):
    uid = message.from_user.id

    # If user is already in waiting (searching)
    if uid in waiting and uid not in chat_pairs:
        await message.answer("You're already searching for someone. Please wait...")
        return

    # If user is in a chat, disconnect both sides
    if uid in chat_pairs:
        partner = chat_pairs[uid]

        # Remove both from chat pairs
        del chat_pairs[partner]
        del chat_pairs[uid]

        # Tell the partner what happened
        await bot.send_message(partner, "Your partner left the chat and is searching again...")
        
        # Put partner back into waiting if not already
        if partner not in waiting:
            waiting.add(partner)

        # Tell this user they're starting a new search
        await message.answer("Searching for a new stranger...")

        # Put the user back into waiting for a new match
        waiting.add(uid)
        return

    # Otherwise user is not chatting and not searching yet
    # Put them into waiting
    waiting.add(uid)
    await message.answer("Searching for a new stranger...")

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
