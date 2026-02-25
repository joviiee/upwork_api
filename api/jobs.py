from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from db.pool import get_pool
from security_utils.auth_utils import require_auth
import json

print("Jobs API Loaded")

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/")
async def list_jobs(
    user = Depends(require_auth),
    pool = Depends(get_pool),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    offset = (page - 1) * limit
    
    async with pool.acquire() as conn:
        conditions = []
        params = []

        if status and status != "all":
            conditions.append(f"proposal_generation_status = ${len(params) + 1}")
            params.append(status)

        if search:
            conditions.append(f"job_title ILIKE ${len(params) + 1}")
            params.append(f"%{search}%")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        base_params = list(params)

        limit_param = len(params) + 1
        offset_param = len(params) + 2
        params.extend([limit, offset])

        rows = await conn.fetch(
            f"""
            SELECT
                id,
                job_uuid,
                job_url,
                job_title,
                proposal_generation_status
            FROM jobs
            {where_clause}
            ORDER BY id DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
            """,
            *params,
        )

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM jobs {where_clause}",
            *base_params,
        )
        
        print(f"Jobs retrieved - {len(rows)}")

        payload =  {
            "page": page,
            "limit": limit,
            "total": total,
            "has_next": offset + limit < total,
            "jobs": [
                {
                    "id": r["id"],
                    "job_uuid": r["job_uuid"],
                    "job_url": r["job_url"],
                    "job_title": r["job_title"],
                    "proposal_generation_status": r["proposal_generation_status"],
                }
                for r in rows
            ],
        }
        print(payload)
        return payload

@router.get("/{job_id}")
async def get_job(
    job_id: int,
    user = Depends(require_auth),
    pool = Depends(get_pool),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                id,
                job_uuid,
                job_url,
                job_title,
                proposal_generation_status,
                job_description
            FROM jobs
            WHERE id = $1
            """,
            job_id,
        )

        if not row:
            raise HTTPException(status_code=404, detail="Job not found")

        payload =  {
            "id": row["id"],
            "job_uuid": row["job_uuid"],
            "job_url": row["job_url"],
            "job_title": row["job_title"],
            "proposal_generation_status": row["proposal_generation_status"],
            "job_description": json.loads(row["job_description"]),
        }
        print(payload)
        return payload