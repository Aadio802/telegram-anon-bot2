import aiosqlite

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            rating_sum INTEGER DEFAULT 0,
            rating_count INTEGER DEFAULT 0
        )
        """)
        await db.commit()
