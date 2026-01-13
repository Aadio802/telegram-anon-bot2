import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found. Add it in Railway Variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

searching = set()
waiting = set()
chat_pairs = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome! Use /find to chat with a stranger.")

@dp.message(Command("find"))
async def find(message: types.Message):
    uid = message.from_user.id

    if uid in chat_pairs:
        await message.answer("You are already chatting.")
        return

    if searching:
        partner = searching.pop()
        chat_pairs[uid] = partner
        chat_pairs[partner] = uid

        await bot.send_message(partner, "Connected to a stranger!")
        await message.answer("Connected to a stranger!")
    else:
        searching.add(uid)
        await message.answer("Searching for someone...")

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

    # If chatting, disconnect
    if uid in pairs:
        partner = pairs.pop(uid)
        pairs.pop(partner)

        await bot.send_message(partner, "Stranger skipped you.")
        waiting.add(partner)

    # Remove user from waiting if already there
    waiting.discard(uid)

    # Try to match again
    if waiting:
        partner = waiting.pop()
        pairs[uid] = partner
        pairs[partner] = uid

        await message.answer("Connected to a new stranger!")
        await bot.send_message(partner, "Connected to a new stranger!")
    else:
        waiting.add(uid)
        await message.answer("Searching for a new stranger...")

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
