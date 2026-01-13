import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found. Add it in Railway Variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

queue = []
pairs = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome! Use /find to chat with a stranger.")

@dp.message(Command("find"))
async def find(message: types.Message):
    user_id = message.from_user.id

    if user_id in pairs:
        await message.answer("You are already chatting.")
        return

    if queue:
        partner = queue.pop(0)
        pairs[user_id] = partner
        pairs[partner] = user_id

        await bot.send_message(partner, "Partner found 😺 /next — find a new partner /stop — stop this chat")
        await message.answer("Connected to a stranger!")
    else:
        queue.append(user_id)
        await message.answer("Searching for a partner...")

@dp.message(Command("stop"))
async def stop(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]

        await bot.send_message(partner, "Your partner left the chat.")
        await message.answer("You stopped the chat. Searching for a new partner....")
    else:
        await message.answer("You are not in a chat.")

@dp.message(Command("next"))
async def next_chat(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        partner = pairs[uid]
        del pairs[partner]
        del pairs[uid]
        await bot.send_message(partner, "Your partner left. Finding a new one...")

    await find(message)

@dp.message()
async def relay(message: types.Message):
    uid = message.from_user.id

    if uid in pairs:
        partner = pairs[uid]
        await bot.send_message(partner, message.text)
    else:
        await message.answer("Use /find to start chatting.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
