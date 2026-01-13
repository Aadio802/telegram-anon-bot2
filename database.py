import aiosqlite

async def init_db():
    async with aiosqlite.connect("botdata.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                rating_sum INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter INTEGER,
                reported INTEGER
            );
        """)
        await db.commit()
