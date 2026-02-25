from db.pool import get_pool
from asyncpg.utils import _quote_ident

async def drop_table(table_name:str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"DROP TABLE IF EXISTS {_quote_ident(table_name)};")
    
async def check_table_schema(table_name: str):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Query column names and data types
            result = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = $1;
            """, table_name)
            # Format result as a list of dicts
            schema = [{"column": row['column_name'], "type": row['data_type']} for row in result]
            return True, {"status": "Schema retrieved", "schema": schema}
    except Exception as e:
        return False, {"status": f"Failed to check schema for {table_name} - {e}", "schema": []}
