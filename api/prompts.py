from fastapi import APIRouter, Depends, HTTPException, Query
from db.pool import get_pool
from db.queue_manager import enqueue_task
from security_utils.auth_utils import require_auth
from state import get_app_state,AppState

router = APIRouter(prefix="/prompts", tags=["prompts"])

@router.post("/update_proposal_prompt")
async def update_proposal_prompt_api(prompt_text:str, user = Depends(require_auth),state:AppState = Depends(get_app_state)):
    try:
        new_version = await state.prompt_archive.add_prompt("proposal", prompt_text)
        async with state.prompt_lock:
            state.proposal_prompt_changed = True
        return {"status" : "Done", "value" : f"Prompt updated to version {new_version}"}
    except Exception as e:
        return {"status" : "Failed", "message" : str(e)}
    
@router.get("/get_active_proposal_prompt")
async def get_active_proposal_prompt_api(user = Depends(require_auth),state:AppState = Depends(get_app_state)):
    try:
        prompt_text = await state.prompt_archive.get_active_prompt("proposal")
        if prompt_text:
            return {"status" : "Done", "value" : prompt_text}
        else:
            return {"status" : "Failed", "message" : "No active prompt found."}
    except Exception as e:
        return {"status" : "Failed", "message" : str(e)}
    
@router.get("/list_proposal_prompt_versions")
async def list_proposal_prompt_versions_api(user = Depends(require_auth),state:AppState = Depends(get_app_state)):
    try:
        versions = await state.prompt_archive.list_versions("proposal")
        return {"status" : "Done", "value" : versions}
    except Exception as e:
        return {"status" : "Failed", "message" : str(e)}
    
@router.post("/rollback_proposal_prompt")
async def rollback_proposal_prompt_api(version:int, user = Depends(require_auth),state:AppState = Depends(get_app_state)):
    try:
        if version == 0:
            async with state.prompt_archive.pool.acquire() as conn:
                await conn.execute(
                    "UPDATE prompts SET is_active=FALSE WHERE prompt_name=$1",
                    "proposal"
                )
        else:
            await state.prompt_archive.rollback("proposal", version)
        async with state.prompt_lock:
            state.proposal_prompt_changed = True
        return {"status" : "Done", "value" : f"Rolled back to {version}"}
    except Exception as e:
        return {"status" : "Failed", "message" : str(e)}
    
@router.get("/get_proposal_prompt")
async def get_proposal_prompt_by_version_api(version:int, user = Depends(require_auth), state:AppState = Depends(get_app_state)):
    try:
        prompt_text = await state.prompt_archive.get_prompt_by_version("proposal", version)
        if prompt_text:
            return {"status" : "Done", "value" : prompt_text}
        else:
            return {"status" : "Failed", "message" : "Prompt not found for the specified version."}
    except Exception as e:
        return {"status" : "Failed", "message" : str(e)}