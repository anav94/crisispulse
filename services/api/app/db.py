import os, asyncpg
DB_DSN=os.getenv("API_DB_DSN","postgresql://cp_user:cp_pass@postgres:5432/crisispulse")
async def get_pool(): return await asyncpg.create_pool(dsn=DB_DSN, min_size=1, max_size=5)
