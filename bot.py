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

    if uid in chat_pairs:
        partner = chat_pairs[uid]
        del chat_pairs[partner]
        del chat_pairs[uid]
        await bot.send_message(partner, "Your partner disconnected.")

    if uid in waiting:
        waiting.remove(uid)

    await message.answer("Chat stopped. Use /find to search again.")

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
