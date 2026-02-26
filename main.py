from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import traceback
import pickle
import asyncio
import json
import re
import os
from dotenv import load_dotenv

from nyx.browser import NyxBrowser
from nyx.page import NyxPage

from upwork_agent.bidder_agent import build_bidder_agent,call_proposal_generator_agent, Proposal
from db.pool import init_pool, close_pool
from db.proposals import add_proposal, create_proposals_table
from db.jobs import create_jobs_table, get_job_by_url
from db.auth import create_user_table
from db.queue_manager import create_queue_table, enqueue_task, get_next_task, update_task_status, abort_tasks_on_restart
from utils import generate_search_links
from utils.prompts_archive import PromptArchive
from rag_utils.embed_data import check_embeddings_exist, embed_documents, create_docs_from_csv, ensure_pgvector
from security_utils.auth_utils import require_auth

from api import (
    auth_router,
    jobs_router,
    task_router,
    proposals_router,
    prompts_router
)

from state import AppState, get_app_state
from upwork_agent.scrape_jobs import ScraperSession
from upwork_agent.application import ApplicationSession

ALLOWED_ORIGINS = os.getenv("ORIGINS", "http://localhost,http://localhost:8000,http://localhost:5678,http://127.0.0.1:5678,http://localhost:5173").split(",")

LOGIN_USERNAME = os.getenv("UPWORK_USERNAME")
LOGIN_PASSWORD = os.getenv("UPWORK_PASSWORD")
SECURITY_QUESTION_ANSWER = os.getenv("UPWORK_SECURITY_QUESTION_ANSWER")

latest_urls_path = 'state_data/latest_links.pkl'
if os.path.exists(latest_urls_path):
    print("Loading latest URLs from", latest_urls_path)
    with open(latest_urls_path, 'rb') as f:
        latest_urls = pickle.load(f)
    print("Latest URLs loaded:", latest_urls)
else:
    print("No latest URLs file found, initializing with None values.")
    latest_urls = {
        "Frontend" : None,
        "Backend" : None,
        "Fullstack" : None,
        "Mobile" : None,
        "AI/ML" : None,
        "GenAI" : None,
        "Devops" : None,
        "IOT" : None,
        "Low code/No code" : None,
        "Non Tech" : None,
        "Data Engineering" : None,
        "Business Intelligence" : None,
        "Best Match" : None
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    state:AppState = AppState()
    # Startup code
    browser:NyxBrowser = NyxBrowser()
    await browser.start()
    state.browser = browser
    print("Browser started")
    state.filter_urls = generate_search_links()
    state.latest_urls = latest_urls
    page:NyxPage = await state.browser.new_page()
    state.page = page
    if not check_embeddings_exist():
        embed_documents(create_docs_from_csv("data/proposals.csv"))
    await init_pool()
    print("Database pool initialized")
    await ensure_pgvector()
    state.proposal_prompt_changed = False
    state.prompt_archive = PromptArchive()
    await state.prompt_archive.init()
    state.proposal_system_prompt = await state.prompt_archive.get_active_prompt("proposal")
    print("Prompt archive initialized")
    state.bidder_agent = build_bidder_agent()
    print("Bidder agent created")
    abort_status, msg = await abort_tasks_on_restart()
    print(abort_status, msg)
    app.state.core = state
    worker_task = asyncio.create_task(worker_loop())
    print("Worker loop started")
    yield
    # Shutdown code
    # cm.__exit__(None, None, None)
    worker_task.cancel()
    await close_pool()
    print("Database pool closed")
    await state.browser.shutdown()
    
app = FastAPI(
    title="Upwork API",
    description="An upwork automation bot with intelligence and captcha solving capabilities.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth_router,prefix="/api")
app.include_router(jobs_router,prefix="/api")
app.include_router(task_router,prefix="/api")
app.include_router(proposals_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

async def check_for_jobs(task_id:int):
    session = ScraperSession(
            task_id=task_id,
            page = app.state.core.page, 
            links_to_visit=app.state.core.filter_urls, 
            last_links=app.state.core.latest_urls, 
            username= LOGIN_USERNAME, 
            password=LOGIN_PASSWORD, 
            security_answer=SECURITY_QUESTION_ANSWER
        )
    await session.run()

async def apply_for_job(task_id:int,job_url: str, human:str = "Unable to verify"):
    session = ApplicationSession(
            task_id = task_id,
            page = app.state.core.page, 
            job_url=job_url,
            username= LOGIN_USERNAME, 
            password=LOGIN_PASSWORD, 
            security_answer=SECURITY_QUESTION_ANSWER, 
            human=human
        )
    await session.run()
            
async def worker_loop():
    while True:
        try:
            status,task = await get_next_task()
            if status:
                task_id = task['id']
                task_type = task['task_type']
                user = task['username']
                print(f"Processing task: {task_type} for user: {user}")
                for key, value in task.items():
                    print(f"{key}: {value}")
                if task_type == 'check_for_jobs':
                    await check_for_jobs(task_id=task_id)
                    await update_task_status(task_id=task_id, status='done')
                elif task_type == 'apply_for_job':
                    payload_string = task.get("payload","")
                    payload = json.loads(payload_string) if payload_string else {}
                    job_url = payload.get("job_url")
                    print(f"Job URL from task payload: {job_url}")
                    if job_url:
                        await apply_for_job(task_id=task_id,job_url=job_url, human=user)
        except Exception as e:
            print(f"Error in worker loop: {e}")
            traceback.print_exc()
        finally:
            await asyncio.sleep(3)
