from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from db.pool import get_pool
from security_utils.auth_utils import require_auth
import asyncio
import json
import traceback
from state import get_app_state
from upwork_agent.bidder_agent import generate_proposal_for_job
from db.jobs import change_proposal_generation_status, get_job_by_url
from db.proposals import get_proposal_by_url, update_proposal_by_url
from utils.models import Proposal as ProposalModel

print("Jobs API Loaded")

router = APIRouter(prefix="/proposals", tags=["proposals"])

class SaveProposalRequest(BaseModel):
    job_url: str
    proposal: ProposalModel
    profile: str = "general_profile"

@router.post("/generate_proposal")
async def generate_proposal_api(job_url:str, user = Depends(require_auth),state = Depends(get_app_state)):
    try:
        await change_proposal_generation_status(job_url, "processing")
        asyncio.create_task(generate_proposal_for_job(state, job_url))
        return {"status" : "Processing", "message" : f"Proposal generation started for {job_url}. It will be available in the proposals list once done."}
    except Exception as e:
        traceback.print_exc()
        return {"status" : "Failed", "message" : str(e)}

@router.get("/get_proposal")
async def get_proposal_api(job_url: str, user = Depends(require_auth)):
    try:
        proposal, job_type, profile, applied, approved_by = await get_proposal_by_url(job_url)
        print(proposal, job_type, profile)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found for this job.")
        return {
            "status": "Done",
            "job_url": job_url,
            "job_type": job_type,
            "profile": profile,
            "proposal": proposal.model_dump(),
            "applied": applied,
            "approved_by": approved_by
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save_proposal")
async def save_proposal_api(payload: SaveProposalRequest, user = Depends(require_auth)):
    try:
        proposal = payload.proposal
        profile = payload.profile if hasattr(payload, "profile") and payload.profile else "general_profile"
        if proposal.questions_and_answers is None:
            proposal.questions_and_answers = []

        updated, message = await update_proposal_by_url(
            payload.job_url,
            {"proposal": proposal.model_dump_json(), "profile": profile }
        )
        if not updated:
            raise HTTPException(status_code=500, detail=message)

        await change_proposal_generation_status(payload.job_url, "draft")

        return {
            "status": "Done",
            "job_url": payload.job_url,
            "proposal": proposal.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))