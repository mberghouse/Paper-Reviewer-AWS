import openai
import asyncio
class BaseAgent:
    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agents must implement run method")

class StatisticalMethodsAgent(BaseAgent):
    def __init__(self, openai_model="gpt-4o-mini"):
        self.model = openai_model

    async def run(self, manuscript_text: str) -> str:
        prompt = f"""
        You are a highly knowledgeable AI reviewer specializing in statistical analysis in academic research.
        Below is the manuscript text related to methods and results. Please conduct a thorough review of its 
        statistical methods with the following objectives:
        
        1. Evaluate if the statistical methods described in the text are appropriate for the study.
        2. Assess whether the methods effectively back up the claims made in the manuscript.
        3. Determine if the statistical techniques are clearly explained and reproducible.
        4. Identify any potential shortcomings or areas where additional statistical methods might improve 
           the study's validity and reliability.

        Your response should be thorough and detailed
        
        Manuscript text:
        {manuscript_text}
        """
        response = await asyncio.to_thread(openai.chat.completions.create,
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16000
        )
        
        summary_output = response.choices[0].message.content.strip()
        return summary_output

# Example usage:
