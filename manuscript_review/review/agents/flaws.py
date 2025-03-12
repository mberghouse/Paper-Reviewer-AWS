import openai
import asyncio
class BaseAgent:
    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agents must implement run method")

class DevilsAdvocate(BaseAgent):
    def __init__(self, openai_model="gpt-4o-mini"):
        self.model = openai_model
        #self.lit_review = lit_review

    async def run(self, manuscript_text: str) -> str:

        prompt = f"""
        You are a critical peer reviewer. Identify every potential flaw, 
        from methodological issues to unclear statements or contradictory logic, in the following manuscript. 
        Provide them as a detailed bullet list. Each bullet should describe the nature of the flaw, the severity of the flaw, and why the flaw may have a significant impact on the overall manuscript.

        Text: {manuscript_text}
        """

        response = await asyncio.to_thread(openai.chat.completions.create,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16000
        )

        return response.choices[0].message.content

