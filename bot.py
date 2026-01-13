import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from database import init_db

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found. Add it in Railway Variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

waiting = set()
pairs = {}
rating_targets = {}

# ---------- Helper to save rating ----------
async def save_rating(target, score):
    async with aiosqlite.connect("users.db") as db:
        # ensure user exists
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (target,))
        # update rating
        await db.execute("""
            UPDATE users
            SET rating_sum = rating_sum + ?, rating_count = rating_count + 1
            WHERE user_id = ?
        """, (score, target))
        await db.commit()

# ---------- /start ----------
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Welcome! 👋\nUse /find to connect with a stranger."
    )

# ---------- /find ----------
@dp.message(Command("find"))
async def find_handler(message: types.Message):
    uid = message.from_user.id

    # already in a chat?
    if uid in pairs:
        await message.answer("You are already chatting. Use /next or /stop.")
        return

    # already searching?
    if uid in waiting:
        await message.answer("You're already searching. Please wait!")
        return

    # try to match
    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "🔗 Connected to a stranger!")
            await message.answer("🔗 Connected to a stranger!")
            return

    # no partner yet, add to waiting
    waiting.add(uid)
    await message.answer("🔍 Searching for a partner...")

# ---------- /next ----------
@dp.message(Command("next"))
async def next_handler(message: types.Message):
    uid = message.from_user.id

    # If user was chatting, disconnect
    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "Your partner left the chat.")

        # put partner back into waiting
        if partner not in waiting:
            waiting.add(partner)

    # If already searching
    if uid in waiting:
        await message.answer("You're already searching. Please wait!")
        return

    # try match again
    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "🔗 Connected to a stranger!")
            await message.answer("🔗 Connected to a stranger!")
            return

    # no partner yet
    waiting.add(uid)
    await message.answer("🔍 Searching for a partner...")

# ---------- /stop (disconnect + ask for rating) ----------
@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    uid = message.from_user.id

    # if chatting, end chat
    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]

        await bot.send_message(partner, "Your partner disconnected.")
        
        # request ratings
        rating_targets[partner] = uid
        rating_targets[uid] = partner
        
        await bot.send_message(partner, "Rate your partner: /rate <1–5>")
        await message.answer("Rate your partner: /rate <1–5>")
        return

    # if waiting but not chatting
    if uid in waiting:
        waiting.remove(uid)
        await message.answer("Stopped searching.")
        return

    # idle
    await message.answer("You’re not in a conversation right now.")

# ---------- /rate (save a rating) ----------
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

    target = rating_targets.pop(uid)
    await save_rating(target, score)
    await message.answer(f"Thanks! You rated your partner {score}⭐")

# ---------- /myrating (view your rating) ----------
@dp.message(Command("myrating"))
async def my_rating(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute(
            "SELECT rating_sum, rating_count FROM users WHERE user_id=?", (uid,)
        ) as cur:
            row = await cur.fetchone()

    if not row or row[1] < 1:
        await message.answer("No ratings yet.")
    else:
        avg = row[0] / row[1]
        await message.answer(
            f"⭐ Your rating: {avg:.2f} based on {row[1]} rating(s)."
        )

# ---------- relay other messages ----------
@dp.message()
async def relay_handler(message: types.Message):
    uid = message.from_user.id
    if uid in pairs:
        await bot.send_message(pairs[uid], message.text)

# ---------- start polling (with DB init) ----------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

