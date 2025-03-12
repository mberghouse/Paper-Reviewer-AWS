import openai
import asyncio
class BaseAgent:
    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agents must implement run method")

class ConsistencyAgent(BaseAgent):
    def __init__(self, openai_model="gpt-4o-mini"):
        self.model = openai_model
        #self.lit_review = lit_review

    async def run(self, manuscript_text: str) -> str:

        prompt = f"""
        You have been tasked with checking the consistency of the following manuscript.
        Please identify any inconsistent use of concepts or phrases, any inconsistencies between
        various claims, and any inconsistencies in the introduction, methods, results or discussion.

        Manuscript text: {manuscript_text}
        """

        response = await asyncio.to_thread(openai.chat.completions.create,
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16000
        )

        return response.choices[0].message.content
