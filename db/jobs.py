from db.pool import get_pool
import asyncpg
import json

async def create_jobs_table():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY,
                    job_title TEXT,
                    job_uuid bigint UNIQUE,
                    job_url TEXT NOT NULL UNIQUE,
                    is_proposal_generated BOOLEAN NOT NULL DEFAULT FALSE,
                    job_description JSONB NOT NULL
                );
            """)
        return True, "Created jobs table"
    except Exception as e:
        return False, f"Could not create the jobs table - {e}"
    
    
async def clear_jobs_table():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM jobs;")
        return True, "Cleared jobs table"
    except Exception as e:
        return False, f"Couldnot clear table - {e}"
    finally:
        await pool.close()
        
async def add_job(uuid:int, job_url: str, job_description:dict):
    try:
        job_title = job_description.pop("title", "No Title")
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO jobs (job_uuid, job_url, job_description, job_title)
                VALUES ($1, $2, $3,$4)
                """,
                uuid,
                job_url,
                json.dumps(job_description),
                job_title
            )
        return True, {"status":"Job added successfully"}
    except asyncpg.UniqueViolationError:
        return True, {"status":"Exists", "message":"Job already exists"}
    except Exception as e:
        return False, {"status":"Failed", "message" : f"Pushing job {job_url} to db failed - {e}"}

async def get_job_by_url(job_url: str):
    """
    Retrieve a job row from the jobs table by job_url.
    Returns the row as a dict, or None if not found.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM jobs WHERE job_url = $1;", job_url
            )
            if row:
                job_description = row["job_description"]
                print(job_description)
                job_uuid = row["job_uuid"]
                return job_uuid, json.loads(job_description)
            return None, None
    except Exception as e:
        print(f"Could not retrieve proposal - {e}")
        return None, None

async def get_job_by_uuid(job_uuid: int):
    """
    Retrieve a job row from the jobs table by job_uuid.
    Returns the row as a dict, or None if not found.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM jobs WHERE job_uuid = $1;", job_uuid
            )
            if row:
                job_description = row["job_description"]
                print(job_description)
                job_url = row["job_url"]
                return job_url, json.loads(job_description)
            return None, None
    except Exception as e:
        print(f"Could not retrieve proposal - {e}")
        return None, None
    
async def view_jobs_table(num_rows: int = 10):
    """
    View the first `num_rows` rows from the jobs table.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM jobs ORDER BY id LIMIT $1;", num_rows
        )
        for row in rows:
            print(dict(row))
            
async def change_proposal_generation_status(job_url: str, value: str):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE jobs SET proposal_generation_status = $1 WHERE job_url = $2",
                value, job_url
            )
        return True, "Job marked as proposal generated"
    except Exception as e:
        return False, f"Could not update job - {e}"