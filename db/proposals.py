import asyncpg
import json
from asyncpg.utils import _quote_ident

from upwork_agent.bidder_agent import Proposal

from db.pool import get_pool

async def create_proposals_table():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    id SERIAL PRIMARY KEY,
                    job_uuid bigint UNIQUE,
                    job_url TEXT NOT NULL UNIQUE,
                    job_type TEXT,
                    proposal JSONB NOT NULL,
                    applied BOOLEAN NOT NULL DEFAULT FALSE,
                    approved_by TEXT
                );
            """)
        return True, "Created proposals table"
    except Exception as e:
        return False, f"Could not create the jobs table - {e}"
    
async def clear_proposals_table():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM proposals;")
        return True, "Cleared proposals table"
    except Exception as e:
        return False, f"Couldnot clear table - {e}"
    finally:
        await pool.close()
        
async def add_proposal(uuid:int, job_url: str, job_type:str, proposal:Proposal, applied: bool = False, approved_by: str = None):
    """
    Insert a proposal into the proposals table.
    proposal_model: a Pydantic model instance.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO proposals (job_uuid, job_url, job_type, proposal, applied,approved_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                uuid,
                job_url,
                job_type,
                proposal.model_dump_json(),  # Convert Pydantic model to dict for JSONB
                applied,
                approved_by
            )
        return True, {"status":"Done", "message" : "Proposal added successfully"}
    except asyncpg.UniqueViolationError:
        return False, {"status":"Exists", "message":"Proposal already exists"}
    except Exception as e:
        return False, {"status" : "Failed", "message" : f"Pushing job {job_url} to db failed - {e}"}
    
async def get_proposal_by_url(job_url: str):
    """
    Retrieve a proposal row from the proposals table by job_url.
    Returns the proposal object, or None if not found.
    """
    try:
        print(f"Retrieving proposal for URL: {job_url}\n\n")
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM proposals WHERE job_url = $1;", job_url
            )
            print(row)
            if row:
                proposal_json = row["proposal"]
                proposal = Proposal.model_validate_json(proposal_json)
                profile = row["profile"]
                job_type = row["job_type"]
                applied = row["applied"]
                approved_by = row["approved_by"]
                return proposal, job_type, profile, applied, approved_by
            return None, None, None, None, None
    except Exception as e:
        print(f"Could not retrieve proposal - {e}")
        return None, None, None, None, None

async def update_proposal_by_url(job_url: str, updates: dict):
    """
    Update fields in the proposals table for a given job_url.
    `updates` should be a dict of {column_name: new_value}.
    """
    try:
        if not updates:
            return "No updates provided."
        set_clauses = []
        values = []
        idx = 1
        for col, val in updates.items():
            set_clauses.append(f"{col} = ${idx}")
            values.append(val)
            idx += 1
        set_clause = ", ".join(set_clauses)
        values.append(job_url)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE proposals
                SET {set_clause}
                WHERE job_url = ${idx}
                """,
                *values
            )
        return True, "Update success."
    except Exception as e:
        return False, f"Update failed - {e}"
    
async def update_proposal_by_uuid(job_uuid: str, updates: dict):
    """
    Update fields in the proposals table for a given job_url.
    `updates` should be a dict of {column_name: new_value}.
    """
    try:
        if not updates:
            return "No updates provided."
        set_clauses = []
        values = []
        idx = 1
        for col, val in updates.items():
            set_clauses.append(f"{col} = ${idx}")
            values.append(val)
            idx += 1
        set_clause = ", ".join(set_clauses)
        values.append(job_uuid)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE proposals
                SET {set_clause}
                WHERE job_uuid = ${idx}
                """,
                *values
            )
        return True, "Update success."
    except Exception as e:
        return False, f"Update failed - {e}"
    
async def view_proposals_table(num_rows: int = 10):
    """
    View the first `num_rows` rows from the proposals table.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM proposals ORDER BY id LIMIT $1;", num_rows
        )
        for row in rows:
            print(dict(row))
            
