from utils.session import Session
from utils.constants import upwork_login_url, cloudfare_challenge_div_id, upwork_url, home_url, send_job_updates_webhook_url, send_job_updates_webhook_url_test
from utils.models import Proposal

from db.proposals import get_proposal_by_url, update_proposal_by_url
from db.queue_manager import update_task_status
from db.jobs import change_proposal_generation_status

from typing import Literal, Optional
import asyncio
import re 

from nyx.page import NyxPage

class ApplicationSession(Session):
    def __init__(self,
                 task_id:int,
                 page:NyxPage, 
                 job_url:str,
                 username:str, 
                 password:str,
                 human:str,
                 security_answer:str = None, 
                 status_endpoint:str = send_job_updates_webhook_url,
                 ):
        super().__init__(task_id, page, username, password, security_answer, status_endpoint)
        self.job_url = job_url
        self.human = human
        self.applied = False
        self.proposal:Optional[Proposal] = None
        self.proposal_type:Optional[Literal["Hourly", "Fixed Price"]] = None
        
    async def run(self):
        try:
            client_setup_success = await self.setup_client()
            if not client_setup_success:
                return False
        except Exception as e:
            print(f"Error setting up client: {e}")
        try:
            client_setup_success = await self.setup_client()
            if not client_setup_success:
                await update_task_status(self.task_id, "failed")
                return False
            proposal_fetch_status = await self.get_proposal()
            if not proposal_fetch_status:
                await self.send_status()
                self.print_status()
                await update_task_status(self.task_id, "failed")
                return False
            login_status = await self.login(upwork_login_url)
            if not login_status:
                await self.send_status()
                self.print_status()
                await update_task_status(self.task_id, "failed")
                return False
            reach_bidding_page_status = await self.reach_bidding_page()
            if not reach_bidding_page_status:
                await self.send_status()
                self.print_status()
                await update_task_status(self.task_id, "failed")
                return False
            apply_status = await self.apply_for_job()
            if not apply_status:
                await self.send_status()
                self.print_status()
                await update_task_status(self.task_id, "failed")
                return False
            update_proposal_status = await self.update_proposal_status()
            if not update_proposal_status:
                await self.send_status()
                self.print_status()
                return False
            await update_task_status(self.task_id, "completed")
            self.update_status("Success", "Application process completed successfully")
            await self.send_status()
            self.print_status()
            await self.close_client()
            await self.page.goto(home_url)
            return True
        except Exception as e:
            print("taking screenshot of error")
            await self.page.take_screenshot(filename=f"screenshots/application_session_error_{self.task_id}.png")
            await self.close_client()
            await self.page.goto(home_url)
            return False
        
    async def reach_bidding_page(self):
        try:
            await self.page.goto(self.job_url, wait_for = 'button[data-cy="submit-proposal-button"]', captcha_selector=cloudfare_challenge_div_id, wait_until= "domcontentloaded", referer="https://www.upwork.com")
            await self.page.click(selector = 'button[data-cy="submit-proposal-button"]', expect_navigation=True)
            await asyncio.sleep(1)
            return True
        except Exception as e:
            warning_elements = await self.page.get_all_elements(selector = 'div.air3-alert-content')
            if len(warning_elements) > 0:
                for element in warning_elements:
                    warning_text = await element.text_content()
                    if "no longer available" in warning_text.lower():
                        self.update_status("Failed", "Job is no longer available")
                        await self.send_status()
                        self.print_status()
                        return True
            else:
                await self.page.take_screenshot(filename=f"screenshots/reach_bidding_page_error_{self.task_id}.png")
                self.update_status("Failed", f"Error reaching job page: {e}")
                await self.send_status()
                self.print_status()
                return False
    
    async def get_proposal(self):
        try:
            existing_proposal, job_type, profile, applied, approved_by = await get_proposal_by_url(self.job_url)
            self.proposal = existing_proposal
            if existing_proposal:
                self.proposal_type = job_type
                self.profile = profile
                print(self.profile)
                print(self.proposal_type)
            else:
                self.update_status("Failed", "No existing proposal found for the job URL")
                await self.send_status()
                self.print_status()
                return False
            return True
        except Exception as e:
            self.update_status("Failed", f"Error retrieving proposal: {e}")
            await self.send_status()
            self.print_status()
            return False
        
    async def update_proposal_status(self):
        if not self.proposal:
            self.update_status("Failed", "No proposal to update")
            await self.send_status()
            self.print_status()
            return False
        try:
            updates = {
                "applied": self.applied, 
                "approved_by": self.human
                }
            update_status, msg = await update_proposal_by_url(self.job_url, updates)
            if not update_status:
                self.update_status("Failed", f"Database update error - {msg}")
                await self.send_status()
                self.print_status()
                return False
            job_update_status, job_update_msg = await change_proposal_generation_status(self.job_url, "applied")
            if not job_update_status:
                self.update_status("Failed", f"Job status update error - {job_update_msg}")
                await self.send_status()
                self.print_status()
                return False
            self.print_status()
            return True
        except Exception as e:
            self.update_status("Failed", f"Error updating proposal status: {e}")
            await self.send_status()
            self.print_status()
            return False
        
    async def apply_for_job(self):
        if not self.proposal:
            self.update_status("Failed", "No proposal to apply with")
            await self.send_status()
            self.print_status()
            return False
        try:
            profile_change_status = await self.change_profile()
            if not profile_change_status:
                return False
            if self.proposal_type == "Fixed Price":
                return True
            cover_letter = self.proposal.cover_letter
            await asyncio.sleep(3)
            await self.page.copy_to_clipboard(cover_letter)
            await self.page.wait_for_element('textarea[aria-labelledby="cover_letter_label"]')
            textbox = await self.page.get_element(selector = 'textarea[aria-labelledby="cover_letter_label"]')
            if not textbox:
                self.update_status("Failed", "Cover letter textbox not found")
                await self.send_status()
                self.print_status()
                return False
            await self.page.paste_from_clipboard(selector = 'textarea[aria-labelledby="cover_letter_label"]')
            
            questions_and_answers = self.question_answer_parser()
            if questions_and_answers:
                q_a_divs = await self.page.get_all_elements(selector = 'div.fe-proposal-job-questions > div')
                for div in q_a_divs:
                    question_label = await div.query_selector('label.label')
                    question_in_page = await question_label.text_content()
                    print(question_in_page.strip())
                    print(questions_and_answers[question_in_page.strip()])
                    text_area = await div.query_selector('textarea')
                    await self.page.copy_to_clipboard(questions_and_answers[question_in_page.strip()])
                    await self.page.paste_from_clipboard(selector = text_area)
            self.applied = True 
            self.update_status("Success", "Applied for job successfully")
            await self.send_status()
            self.print_status()
            return True
        except Exception as e:
            self.update_status("Failed", f"Error applying for job: {e}")
            await self.send_status()
            self.print_status()
            return False
        
    async def change_profile(self):
        if self.profile == "general_profile":
            return True
        else:
            try:
                dropdown_locator = self.page.locator('div.fe-proposal-settings-special-profile')
                try:
                    await dropdown_locator.wait_for(state="visible", timeout=5000)
                    dropdown_found = True
                except Exception as e:
                    dropdown_found = False
                if not dropdown_found:
                    self.update_status("Failed", "Special profile dropdown not found on page")
                    await self.send_status()
                    self.print_status()
                    return True
                else:
                    change_profile_element = await self.page.get_element(selector = 'div.fe-proposal-settings-special-profile')
                    dropdown_toggle = await change_profile_element.query_selector('div[data-test="dropdown-toggle"]')
                    print("found dropdown toggle")
                    if dropdown_toggle:
                        await self.page.click(dropdown_toggle)
                        await asyncio.sleep(1)
                        options_list = await self.page.get_element(selector = 'ul#dropdown-menu')
                        options = await options_list.query_selector_all('li[role="option"] span.air3-menu-item-text > span')
                        print(f"Found {len(options)} profile options in dropdown")
                        for option in options:
                            if await option.inner_text().strip() == "Machine Learning":
                                await self.page.click(option)
                                await asyncio.sleep(1)
                                if await change_profile_element.query_selector('div.air3-dropdown-toggle-title'):
                                    selected_option = await change_profile_element.query_selector('div.air3-dropdown-toggle-title').inner_text().strip()
                                    if selected_option == "Machine Learning":
                                        return True
                                    else:
                                        print(f"Profile selection failed, expected 'Machine Learning' but got '{selected_option}'")
                                        return False
                    else:
                        await self.page.take_screenshot(filename=f"screenshots/profile_change_error_{self.task_id}.png")
                        print("Dropdown toggle not found in change profile element")
                        return False
            except Exception as e:
                await self.page.take_screenshot(filename=f"screenshots/profile_change_error_{self.task_id}.png")
                print(f"Error changing profile: {e}")
                return False
        
    def question_answer_parser(self):
        q_a_dict = {}
        if len(self.proposal.questions_and_answers) == 0:
            return None
        for question_and_answer in self.proposal.questions_and_answers:
            question = re.sub(r"^\d+\.\s*", "", question_and_answer.question.strip())
            answer = question_and_answer.answer.strip()
            q_a_dict[question] = answer
        return q_a_dict
        
    
    