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

    # If user is currently chatting, disconnect properly
    if uid in chat_pairs:
        partner = chat_pairs.pop(uid)
        chat_pairs.pop(partner, None)

        await bot.send_message(partner, "Your partner left the chat — you will be rematched soon.")

        # Now put the partner back into waiting
        waiting.add(partner)

    # Also remove the caller from waiting if they were there
    waiting.discard(uid)

    # Now put the caller into waiting
    waiting.add(uid)

    # Now attempt to match WHILE handling waiting logic same as /find
    if len(waiting) >= 2:
        # get any other user
        others = list(waiting - {uid})
        if len(others) > 0:
            match_partner = others[0]
            waiting.discard(uid)
            waiting.discard(match_partner)

            chat_pairs[uid] = match_partner
            chat_pairs[match_partner] = uid

            await message.answer("🔗 Connected to a new stranger!")
            await bot.send_message(match_partner, "🔗 Connected to a new stranger!")
            return

    # If no match yet
    await message.answer("🔍 Searching for a new stranger...")

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
