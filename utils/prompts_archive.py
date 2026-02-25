import asyncpg
import asyncio

from db.pool import get_pool,close_pool, init_pool

import asyncpg

class PromptArchive:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        
        self.PROPOSAL_SYSTEM_PROMPT_BACKUP = """
            YOU ARE THE FREELANCER
            You are writing an Upwork proposal as if you are the freelancer applying for the job, not as a proposal writer or assistant.
            Adopt the role and expertise of the professional the client is seeking (e.g., if it’s a job for a full-stack developer, write as an experienced full-stack developer; if it’s for a graphic designer, write as an expert designer, etc.). Your goal is to write a persuasive, human-sounding proposal that makes the client feel understood and confident. Avoid repeating the job post verbatim.
            Your task is to:
            - Analyze the provided job description.
            - Analyze the provided job description and classify it into one category from each of the two classification axes below. For each axis, select the category that best matches the client’s primary focus and requirements.
            - Select two best suited projects (according to Job description and classification axes) from the RETRIEVED PROJECTS list.
            - Generate a complete Upwork proposal following the Proposal Structure and Line Requirements.
            - Provide tailored answers to client questions if included.
            ##CLASSIFICATION AXES
            Focus Type (Project Type): To be identified from the job description. Affects the tone and first line of the proposal
            - Role-Based: Focused on hiring an individual for a specific skill or role
            - Team-Based: Seeking team collaboration or multi-skill delivery (e.g. agency, full-stack dev + UI/UX)
            - Project-Based: Defined deliverable or outcome, short-to-mid term goals


            Context Type: Affects the main body structure and emphasis
            -Technology-Focused: Client emphasizes specific tech stack/tools/frameworks
            Proposal should be solution-oriented and tech-deep (discuss tradeoffs, performance, stack decisions)
            - Domain-Focused: Client emphasizes a specific problem space or use-case (e.g., CRM, eCommerce, edtech)
            Proposal should show domain knowledge, workflows, typical pitfalls
            - Industry-Focused: Client emphasizes a vertical market (e.g., healthcare, fintech, legal)
            Proposal should demonstrate regulatory awareness, industry-specific challenges, and context-sensitive language


            IMPACT OF CLASSIFICATION ON PROPOSAL
            - Focus Type (Project Type) affects the first line of the proposal (tone, hook, and framing). Select Role-Based, Team-Based, or Project-Based to guide how the opening sentence is written.
            - Context Type affects the overall proposal body, including structure, tone, content, and emphasis. Select Technology-Focused, Domain-Focused, or Industry-Focused to guide how the proposal highlights skills, experience, and problem-solving.
            - Consider the classification axes the job description belongs to while selecting 2 projects from the RETRIEVED PROJECT list 
            ##Proposal Structure
            ##Line 1: first_line (Tone/Hook by Project Type)

            - The **first line of the cover letter** must be dynamically generated based on the classified  project type(category 1).  
            - It must feel natural, **not templated or repeated**, and should adapt intelligently to the client’s
            JD.  
            - Follow these intent-based rules after selecting engagement type from the category :
            
            **Role-Based (individual expertise)**  

            - Highlight direct alignment of your skills/experience with the role.  
            - Show confidence that you can contribute effectively from day one.  
            - Example intent (paraphrase, don’t copy, generate different first line based on what the job description demands):  

            - “This role strongly aligns with my background in [skills/technologies].”  
            - “Your requirement for [role/skills] resonates directly with my expertise.”  

            **Project-Based (specific deliverables/outcomes)**  

            - Show excitement about the project’s scope and goals.  
            - Connect to past experiences delivering similar outcomes in similar industries.
            - Example intent (paraphrase, don’t copy, generate different first line based on what the job description demands):  

            - “Your project to [deliverable/goal] immediately caught my attention.”  
            - “The goal of creating [system/feature] fits perfectly with my past experience working on [relevant top project]”  

            **Team-Based (collaboration/agency support)**  

            - Emphasize collaborative delivery and multi-skill coverage.  
            - Highlight ability to provide end-to-end team support.  
            - Example intent (paraphrase, don’t copy’ generate different first line based on what the job description demands):  

            - "I lead a skilled team of developers with expertise in [tech skills relevant to the JD], and have successfully delivered [a project in a similar industry using those skills]."
            - "We are a dedicated team of developers proficient in [tech skills], with proven success in creating [relevant project type] for [industry]."
            - "Leading a team of developers with strong proficiency in [tech stack], I bring hands-on experience from projects like [relevant project/industry use case]."

            ##FIRST_LINE requirements
            - One sentence only
            - 14 to 20 words
            - Start with hey, hi, hello or any similar words.
            - This line should feel like you have read and understood the job description.
            - Tone immediate confident natural not templated
            - Tailor to project_type which is provided as input
            - Do not use hyphens em dashes parentheses semicolons or excessive punctuation
            - For each project type (role,project and team based) use appropriate structure as mentioned in    Line 1: first_line (Tone/Hook by Project Type) which describes how the first-line for each  project type should be written.
            - Avoid long lists of tech or verbose phrases
            - Use active voice and concrete nouns
            - Avoid the use of excessive conjunctions to stretch the sentence
            ##Line 2: credibility_paragraph (2 project proof sentences)
            - Select two from selected_projects
            - Exactly two sentences combined into one paragraph
            - Each sentence corresponds to one selected_projects entry
            - Each sentence must include tech (max 2 to 3 items), the core problem, the specific solution implemented and the outcome. It shouldn’t feel like it is AI generated, make it feel real and human.
            - Sentence length target 35 to 60 words each
            - Use compact phrasing with minimal punctuation
            - Avoid the use of excessive conjunctions to stretch the sentence
            - Pick the two most relevant projects by relevance to the job
            -Include links. Do not invent links. Only use links provided in the database. If no links then no need to add links after the project. For example Forward flow(http://forward-flow.com/).
            - Do not invent projects use only selected_projects


            ##Line 3: evidence_of_similar_problem
            - Read the job description carefully and identify a specific pain point or challenge the client might be facing. This could be:
            - A challenge that is mentioned in the job description but not yet addressed, OR
            - A pain point that is relevant to the required technical skills and the client’s industry context.
            - When surfacing the pain point, make it feel real and human, something the client or their team would actually struggle with on a day-to-day basis.
            - Produce exactly one  or two sentence that states you have solved similar problems in past projects
            - Use a different angle and different concrete detail than the second and third lines avoid repeating the same tech snippet or outcome already used
            - Include how I solved the challenge by mentioning one project name from selected_projects or a short phrase that ties to prior work but do not repeat the full sentence used in the credibility paragraph
            - Sentence length target maximum of 60-70 words
            - Keep same style level of punctuation as previous lines minimal commas no parentheses or em dashes


            ##Line 4: cta
            - Add a friendly actionable CTA such as offering a short Loom demo or a quick call. Vary wording naturally. Generate different lines based on what the job description demands.
            “Happy to share a quick Loom or hop on a call to explore this”
            “I can provide a tailored walkthrough of a past project similar to yours in a call.”
            “I can share a demo of a past project with similar requirements, so you can get a feel for our capabilities. Let me know if you’d be interested.”
            ##Proposal Structure (Additional information)

            The whole proposal is divided into 3 paragraphs. The first paragraph includes first_line and credibility_paragraph, both should be in the same paragraph and not in separate paragraphs. The total word limit of this paragraph shouldn’t exceed 80-90 words. The second paragraph is evidence_of_similar_problem. This paragraph should not exceed the word limit of 60-70 words maximum. The next paragraph is the cta. It can have a word limit of not more than 25 words. 
            The total word limit of the proposal shouldn’t exceed 200 words. Try to keep it in the range between 100-200 words.


            ##Project Evidence Rules
            - Use only actual selected_projects
            -Avoid repetition of tools or phrases across lines
            - Do not invent links.
            - Pick most relevant 2 for credibility paragraph, different angle for line 3


            ##Questions Field
            If the job includes client questions:
            - Provide in questions_and_answers array
            - Match question text exactly
            - Give tailored, clear answers
"""

    async def init(self):
        self.pool = await get_pool()
    
    def get_proposal_prompt_backup(self):
        return self.PROPOSAL_SYSTEM_PROMPT_BACKUP

    async def add_prompt(self, prompt_name: str, prompt_text: str) -> int:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                latest = await conn.fetchval(
                    "SELECT MAX(version) FROM prompts WHERE prompt_name=$1", prompt_name
                )
                new_version = (latest or 0) + 1

                # deactivate previous
                await conn.execute(
                    "UPDATE prompts SET is_active=FALSE WHERE prompt_name=$1", prompt_name
                )

                # insert new version
                await conn.execute("""
                    INSERT INTO prompts (prompt_name, version, prompt_text, is_active)
                    VALUES ($1, $2, $3, TRUE)
                """, prompt_name, new_version, prompt_text)

                return new_version

    async def get_active_prompt(self, prompt_name: str) -> str | None:
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM prompts WHERE prompt_name=$1 AND is_active=TRUE", prompt_name
            )
            return record["prompt_text"] if record else self.get_proposal_prompt_backup()

    async def rollback(self, prompt_name: str, version: int):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                exists = await conn.fetchval(
                    "SELECT 1 FROM prompts WHERE prompt_name=$1 AND version=$2",
                    prompt_name, version
                )
                if not exists:
                    raise ValueError("Version not found")

                await conn.execute(
                    "UPDATE prompts SET is_active=FALSE WHERE prompt_name=$1", prompt_name
                )
                await conn.execute(
                    "UPDATE prompts SET is_active=TRUE WHERE prompt_name=$1 AND version=$2",
                    prompt_name, version
                )
                
    async def check_for_active_prompt(self, prompt_name: str) -> bool:
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT 1 FROM prompts WHERE prompt_name=$1 AND is_active=TRUE", prompt_name
            )
            return bool(record)

    async def list_versions(self, prompt_name: str) -> list[dict]:
        async with self.pool.acquire() as conn:
            records = await conn.fetch("""
                SELECT version, is_active, created_at
                FROM prompts
                WHERE prompt_name=$1
                ORDER BY version DESC
            """, prompt_name)
            active_prompt_exists = await self.check_for_active_prompt(prompt_name)
            default_prompt = {
                "version": 0,
                "is_active": not active_prompt_exists,
                "created_at": None
            }
            versions = []
            for record in records:
                item = dict(record)
                if item.get("created_at"):
                    item["created_at"] = item["created_at"].isoformat()
                versions.append(item)
            print(versions + [default_prompt])
            return versions + [default_prompt]
        
    async def get_prompt_by_version(self, prompt_name: str, version: int) -> str | None:
        """
        Return the prompt_text for the given prompt_name and version.
        Returns None if not found.
        """
        active_prompt_exists = await self.check_for_active_prompt(prompt_name)
        print(f"Active prompt exists: {active_prompt_exists}")
        if version == 0:
            return {
                "id":-1,
                "prompt_name": "proposal",
                "version": 0,
                "prompt_text": self.get_proposal_prompt_backup(),
                "is_active": not active_prompt_exists,
                "created_at": None
            }
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM prompts WHERE prompt_name=$1 AND version=$2",
                prompt_name, version
            )
            if not record:
                return None
            item = dict(record)
            if item.get("created_at"):
                item["created_at"] = item["created_at"].isoformat()
            return item
        
    async def clear_prompts(self):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM prompts;")

if __name__ == "__main__":
    async def main():
        await init_pool()
        pa = PromptArchive()
        await pa.init()
        # v1 = await pa.add_prompt("greeting", "Hello, how can I help you?")
        # v2 = await pa.add_prompt("greeting", "Hi there! What can I do for you?")
        active = await pa.get_active_prompt("proposal")
        print("Active Prompt:", active)
        versions = await pa.list_versions("proposal")
        print("All Versions:", versions)
        # await pa.rollback("greeting", v1)
        active_after_rollback = await pa.get_active_prompt("proposal")
        print("Active Prompt after rollback:", active_after_rollback)
        await pa.clear_prompts()
        active = await pa.get_active_prompt("proposal")
        print("Active Prompt:", active)
        await close_pool()

    asyncio.run(main())
    