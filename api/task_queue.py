from fastapi import APIRouter, Depends, HTTPException, Query
from db.pool import get_pool
from db.queue_manager import enqueue_task
from security_utils.auth_utils import require_auth

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/enqueue_task")
async def enqueue_task_api(task_type:str, user = Depends(require_auth), payload = None, priority:int=0):
    print(f"Enqueuing task: {task_type} for user: {user} with payload: {payload} and priority: {priority}")
    status, message = await enqueue_task(task_type=task_type, username=user, payload=payload, priority=priority)
    return {"status" : status, "message" : message}