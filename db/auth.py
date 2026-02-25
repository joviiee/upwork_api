from db.pool import get_pool
from asyncpg import UniqueViolationError

async def create_user_table():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
            """)
        return True, "Created users table"
    except Exception as e:
        return False, f"Could not create the users table - {e}"

async def get_user_password(username: str) -> str | None:
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            query = "SELECT password_hash FROM users WHERE username = $1"
            stored_password = await connection.fetchval(query, username)
            return stored_password
    except Exception as e:
        raise e
    
async def add_user(username: str, password_hash: str) -> bool:
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            query = "INSERT INTO users (username, password_hash) VALUES ($1, $2)"
            await connection.execute(query, username, password_hash)
            return True, "User added successfully"
    except UniqueViolationError:
        raise 
    except Exception as e:
        return False, str(e)