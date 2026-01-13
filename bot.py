import os
import asyncio
import re
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN
from database import init_db

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

waiting = set()
pairs = {}
rating_targets = {}

# -------- Helpers --------

async def save_rating(target, score):
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (target,))
        await db.execute("""
            UPDATE users
            SET rating_sum = rating_sum + ?, rating_count = rating_count + 1
            WHERE user_id = ?
        """, (score, target))
        await db.commit()

async def user_exists(uid):
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
        await db.commit()

async def is_banned(uid):
    async with aiosqlite.connect("botdata.db") as db:
        async with db.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
    return bool(row and row[0] == 1)

async def is_premium(uid):
    async with aiosqlite.connect("botdata.db") as db:
        async with db.execute("SELECT is_premium FROM users WHERE user_id=?", (uid,)) as cur:
            row = await cur.fetchone()
    return bool(row and row[0] == 1)

# -------- Bot Commands --------

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    uid = message.from_user.id
    await user_exists(uid)
    await message.answer(
        "Welcome! 👋\nUse /find to connect with a stranger."
    )

@dp.message(Command("find"))
async def find_handler(message: types.Message):
    uid = message.from_user.id
    await user_exists(uid)

    if await is_banned(uid):
        await message.answer("🚫 You are banned.")
        return

    if uid in pairs:
        await message.answer("❗ You are already chatting.")
        return

    if uid in waiting:
        await message.answer("🔎 You are already searching. Please wait...")
        return

    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "🔗 Connected to a stranger!")
            await message.answer("🔗 Connected to a stranger!")
            return

    waiting.add(uid)
    await message.answer("🔍 Searching for a partner...")

@dp.message(Command("next"))
async def next_handler(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "❌ Your partner left the chat.")

        if partner not in waiting:
            waiting.add(partner)

    if uid in waiting:
        await message.answer("🔎 You are already searching. Please wait...")
        return

    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "🔗 Connected to a stranger!")
            await message.answer("🔗 Connected to a stranger!")
            return

    waiting.add(uid)
    await message.answer("🔍 Searching for a partner...")

@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]

        await bot.send_message(partner, "❌ Your partner disconnected.")

        rating_targets[partner] = uid
        rating_targets[uid] = partner

        await bot.send_message(partner, "Rate your partner: /rate 1–5")
        await message.answer("Rate your partner: /rate 1–5")
        return

    if uid in waiting:
        waiting.remove(uid)
        await message.answer("Stopped searching.")
        return

    await message.answer("You’re not in a conversation.")

@dp.message(lambda m: m.text and m.text.startswith("/rate "))
async def rate_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Usage: /rate <1–5>")
        return

    try:
        score = int(parts[1])
    except ValueError:
        await message.answer("❌ Invalid number. Enter 1 to 5.")
        return

    if score < 1 or score > 5:
        await message.answer("❌ Rating must be 1–5.")
        return

    uid = message.from_user.id
    if uid not in rating_targets:
        await message.answer("⚠️ No partner to rate right now.")
        return

    target = rating_targets.pop(uid)
    await save_rating(target, score)
    await message.answer(
        f"✅ Your rating ({score}⭐) has been recorded!"
    )

@dp.message(Command("myrating"))
async def my_rating(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("botdata.db") as db:
        async with db.execute(
            "SELECT rating_sum, rating_count FROM users WHERE user_id=?", (uid,)
        ) as cur:
            row = await cur.fetchone()

    if not row or row[1] == 0:
        await message.answer("⭐ You have no ratings yet.")
    else:
        avg = row[0]/row[1]
        await message.answer(
            f"⭐ Your average rating: {avg:.2f} based on {row[1]} ratings."
        )

@dp.message(lambda m: m.text and m.text.lower().startswith("report "))
async def report_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: report <user_id>")
        return

    try:
        bad = int(parts[1])
    except:
        await message.answer("⚠️ Invalid user ID.")
        return

    reporter = message.from_user.id
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute(
            "INSERT INTO reports (reporter, reported) VALUES (?, ?)",
            (reporter, bad),
        )
        await db.commit()

    await message.answer("🚨 Report submitted.")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    uid = message.from_user.id
    # Replace 123456789 with your Telegram ID
    if uid != 123456789:
        await message.answer("Unauthorized.")
        return

    await message.answer(
        "Admin Panel:\n/ban <id>\n/unban <id>\n/stats"
    )

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /ban <user_id>")
        return

    target = int(parts[1])
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute(
            "UPDATE users SET is_banned=1 WHERE user_id=?", (target,)
        )
        await db.commit()

    await message.answer(f"🚫 Banned {target}")

@dp.message(Command("unban"))
async def unban_user(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /unban <user_id>")
        return

    target = int(parts[1])
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute(
            "UPDATE users SET is_banned=0 WHERE user_id=?", (target,)
        )
        await db.commit()

    await message.answer(f"✅ Unbanned {target}")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    async with aiosqlite.connect("botdata.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total = await cur.fetchone()
    await message.answer(f"📊 Total users: {total[0]}")

@dp.message()
async def relay_handler(message: types.Message):
    uid = message.from_user.id
    if uid in pairs and message.text:
        # block normal links if not premium
        if re.search(r"http[s]?://", message.text.lower()):
            if not await is_premium(uid):
                await message.answer("🔒 Links are for PREMIUM users.")
                return
        await bot.send_message(pairs[uid], message.text)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


