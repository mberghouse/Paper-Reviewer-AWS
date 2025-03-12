import openai
import asyncio
class BaseAgent:
    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agents must implement run method")

class MethodsReproducibilityAgent(BaseAgent):
    def __init__(self, openai_model="gpt-4o-mini"):
        self.model = openai_model

    async def run(self, methods_text: str) -> str:
        """
        Analyze whether the methodology is described clearly enough 
        for another researcher to replicate.
        """
        prompt = f"""
        You are a peer reviewer focusing on methods and reproducibility.
        Here is the full text from the manuscript:

        {methods_text}

        Please provide an analysis addressing:
        1. Are the methods described in sufficient detail for replication?
        2. Are sample sizes, data collection procedures, and analysis methods stated clearly?
        3. Are any critical details missing, such as code/data availability or important experimental methods?
        4. What additional methods could be included to improve the paper?
        4. Summarize concerns or suggestions for improvement.
        Please be detailed and thorough in your response. Aim for a 3 page response.
        """


        response = await asyncio.to_thread(openai.chat.completions.create,
            model='gpt-4o',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16000
        )
        return response.choices[0].message.content
