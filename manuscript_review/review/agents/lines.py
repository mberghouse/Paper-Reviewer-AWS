import openai
import asyncio
class BaseAgent:
    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agents must implement run method")

class ManuscriptIssuesAgent(BaseAgent):
    def __init__(self, openai_model="gpt-4o-mini"):
        self.model = openai_model

    async def run(self, manuscript_text: str, summary_text: str) -> str:
        prompt = f"""
        You are an AI reviewer specializing in identifying issues in academic manuscripts. Your tasks are:
        
        1. Analyze the manuscript text provided.
        2. Compare your analysis with the summary text to understand the primary weaknesses of the paper.
        3. Identify specific lines in the manuscript that require revision. 
        4. For each issue, explain why the line requires revision and suggest what the substance of the revision should be.

        Summary text:
        {summary_text}

        Manuscript text:
        {manuscript_text}
        """


        response = await asyncio.to_thread(openai.chat.completions.create,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16384,
        )
        return response.choices[0].message.content