import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

waiting = set()
pairs = {}

# /start
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Welcome! Use /find to connect with a stranger.")

# /find
@dp.message(Command("find"))
async def find_handler(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        await message.answer("You are already in a chat. Use /next or /stop.")
        return

    if uid in waiting:
        await message.answer("You're already searching...")
        return

    # Try match
    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "Connected to a stranger!")
            await message.answer("Connected to a stranger!")
            return

    waiting.add(uid)
    await message.answer("Searching for a partner...")

# /next
@dp.message(Command("next"))
async def next_handler(message: types.Message):
    uid = message.from_user.id

    # If in a chat, disconnect
    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "Your partner left the chat.")

        # put partner back into waiting
        waiting.add(partner)

    # If already searching
    if uid in waiting:
        await message.answer("You're already searching...")
        return

    # Try matching again
    for other in list(waiting):
        if other != uid:
            waiting.remove(other)
            pairs[uid] = other
            pairs[other] = uid
            await bot.send_message(other, "Connected to a stranger!")
            await message.answer("Connected to a stranger!")
            return

    waiting.add(uid)
    await message.answer("Searching for a partner...")

# /stop
@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "Your partner disconnected.")
        await message.answer("You left the chat.")
        return

    if uid in waiting:
        waiting.remove(uid)
        await message.answer("Stopped searching.")
        return

    await message.answer("You’re not in a conversation right now.")

# relay all other messages in chat
@dp.message()
async def relay_handler(message: types.Message):
    uid = message.from_user.id
    if uid in pairs:
        await bot.send_message(pairs[uid], message.text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

