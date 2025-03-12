import openai
import asyncio
class ClaimCheckAgent:
    def __init__(self, lit_review, openai_model="gpt-4o-mini"):
        self.model = openai_model
        self.lit_review = lit_review

    async def run(self, manuscript_text: str) -> str:
        
        prompt = f"""
        Identify any exaggerated claims in the text, or claims that are not well supported 
        by the evidence or references provided. Use the provided summary to improve your contextual understanding of potentailly exaggerated claims.
        Provide page and line references if possible.

        Text: {manuscript_text}

        Literature Review: {self.lit_review}
        """

        response = await asyncio.to_thread(openai.chat.completions.create,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16000,
        )

        summary_output = response.choices[0].message.content.strip()
        return summary_output

