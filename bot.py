import os
import asyncio
import re
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import BOT_TOKEN
from database import init_db

# Bot setup
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

waiting = set()
pairs = {}
rating_targets = {}

# --- Helpers ---

async def save_rating(target, score):
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (target,))
        await db.execute("""
            UPDATE users
            SET rating_sum = rating_sum + ?, rating_count = rating_count + 1
            WHERE user_id = ?
        """, (score, target))
        await db.commit()

async def user_is_banned(uid):
    async with aiosqlite.connect("botdata.db") as db:
        async with db.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
    return bool(row and row[0] == 1)

async def add_user_if_not_exists(uid):
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
        await db.commit()

# --- Core Commands ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await add_user_if_not_exists(message.from_user.id)
    await message.answer("Welcome! Use /find to connect with a stranger.")

@dp.message(Command("find"))
async def find_handler(message: types.Message):
    uid = message.from_user.id
    if await user_is_banned(uid):
        await message.answer("🚫 You are banned.")
        return

    if uid in pairs:
        await message.answer("You are already chatting.")
        return

    if uid in waiting:
        await message.answer("You are already searching.")
        return

    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "Connected!")
            await message.answer("Connected!")
            return

    waiting.add(uid)
    await message.answer("Searching...")

@dp.message(Command("next"))
async def next_handler(message: types.Message):
    uid = message.from_user.id
    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "Partner left.")
        waiting.add(partner)

    if uid in waiting:
        await message.answer("Already searching.")
        return

    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "Connected!")
            await message.answer("Connected!")
            return

    waiting.add(uid)
    await message.answer("Searching...")

@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    uid = message.from_user.id
    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "Partner disconnected.")
        rating_targets[partner] = uid
        rating_targets[uid] = partner
        await bot.send_message(partner, "Rate partner: /rate 1-5")
        await message.answer("Rate partner: /rate 1-5")
        return

    if uid in waiting:
        waiting.remove(uid)
        await message.answer("Stopped searching.")
        return

    await message.answer("Not in a conversation.")

@dp.message(lambda m: m.text and m.text.startswith("/rate "))
async def rate_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /rate <1-5>")
        return
    try:
        score = int(parts[1])
    except:
        await message.answer("Invalid number.")
        return
    if score < 1 or score > 5:
        await message.answer("Number must be 1-5.")
        return

    uid = message.from_user.id
    if uid not in rating_targets:
        await message.answer("Nothing to rate.")
        return

    target = rating_targets.pop(uid)
    await save_rating(target, score)
    await message.answer(f"Thanks for rating {score}⭐")

@dp.message(Command("myrating"))
async def my_rating(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("botdata.db") as db:
        async with db.execute("SELECT rating_sum, rating_count FROM users WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
    if not row or row[1] == 0:
        await message.answer("No ratings yet.")
    else:
        avg = row[0]/row[1]
        await message.answer(f"⭐ Your rating: {avg:.2f} based on {row[1]} ratings.")

# --- Admin Panel ---

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    uid = message.from_user.id
    # Only you (owner) can see admin tools — replace 123 with your Telegram ID
    if uid != 123456789:
        await message.answer("Unauthorized.")
        return
    await message.answer("Admin: /ban <id>, /unban <id>, /stats")

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /ban <user_id>")
        return
    target = int(parts[1])
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target,))
        await db.commit()
    await message.answer(f"Banned {target}")

@dp.message(Command("unban"))
async def unban_user(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /unban <user_id>")
        return
    target = int(parts[1])
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target,))
        await db.commit()
    await message.answer(f"Unbanned {target}")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    async with aiosqlite.connect("botdata.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total = await cur.fetchone()
    await message.answer(f"Total users: {total[0]}")

# --- Relay system ---

@dp.message()
async def relay(message: types.Message):
    uid = message.from_user.id
    if uid in pairs and message.text:
        # Check free user link block
        if "http" in message.text.lower():
            async with aiosqlite.connect("botdata.db") as db:
                async with db.execute("SELECT is_premium FROM users WHERE user_id=?", (uid,)) as cur:
                    is_p = await cur.fetchone()
            if not is_p or is_p[0] == 0:
                await message.answer("Links are for premium users.")
                return

        await bot.send_message(pairs[uid], message.text)

# --- Premium Buy Prompt ---

@dp.message(Command("premium"))
async def premium(message: types.Message):
    await message.answer("To unlock premium features like sending LINKS and high-rating filter, send Stars to this bot.")

# --- Start Polling ---

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

