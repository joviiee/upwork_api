import asyncio
from typing import Optional
from nyx.browser import NyxBrowser
from nyx.page import NyxPage
from utils.prompts_archive import PromptArchive

from fastapi import Request

class AppState:
    def __init__(self):
        self.browser:NyxBrowser = None
        self.page:NyxPage = None

        self.filter_urls = []
        self.latest_urls = []

        self.prompt_archive:PromptArchive = None
        self.bidder_agent = None

        self.proposal_prompt_changed = True
        
        self.proposal_system_prompt = None
        
        self.prompt_lock = asyncio.Lock()

        self.worker_task: Optional[asyncio.Task] = None
        
def get_app_state(request:Request):
    return request.app.state.core