# Helper: python -m app.db_init
import asyncio
from .db import get_pool
from .sql import CREATE_SQL
async def run():
    pool=await get_pool()
    async with pool.acquire() as conn: await conn.execute(CREATE_SQL)
    await pool.close(); print("DB initialized.")
if __name__=="__main__": asyncio.run(run())
