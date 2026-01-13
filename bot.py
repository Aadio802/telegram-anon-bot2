import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiosqlite

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

queue = []

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            rating INTEGER DEFAULT 0,
            votes INTEGER DEFAULT 0
        )
        """)
        await db.commit()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome to Anonymous Chat\nSend /find to find a stranger.")

@dp.message(Command("find"))
async def find(message: types.Message):
    user_id = message.from_user.id

    if queue:
        partner = queue.pop(0)
        await bot.send_message(partner, "Connected to a stranger!")
        await message.answer("Connected to a stranger!")
        dp.chat_pairs[partner] = user_id
        dp.chat_pairs[user_id] = partner
    else:
        queue.append(user_id)
        await message.answer("Searching...")

dp.chat_pairs = {}

@dp.message()
async def relay(message: types.Message):
    uid = message.from_user.id
    if uid in dp.chat_pairs:
        await bot.send_message(dp.chat_pairs[uid], message.text)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
py
