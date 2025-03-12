import openai
import asyncio

class SummarizationAgent:
    def __init__(self, openai_model="gpt-4o"):
        self.model = openai_model

    async def run(self, manuscript_text: str) -> str:
        
        """
        Generate a concise summary of the manuscript in two to three paragraphs,
        plus three paragraphs describing strengths, weaknesses, and 
        recommendations for improvement.
        """
        prompt = f"""
        You are an expert manuscript reviewer for a top scientific journal. The text below comes from a manuscript:

        Please provide the following:
        1. A concise yet thorough three-paragraph summary of the text:
           - Paragraph 1: Summarize the overall topic, context, and main points.
           - Paragraph 2: Summarize any specific arguments, methods, or notable findings.
           - Paragraph 3: Summarize the validity of all claims and the relationship with current literature.

        2. Three additional paragraph that briefly describes the manuscript's 
           main strengths, notable weaknesses, and recommendations for improvement.

        Manuscript text: {manuscript_text}
        """

        response = await asyncio.to_thread(openai.chat.completions.create,
            model='gpt-4o',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16000
        )

        summary_output = response.choices[0].message.content.strip()
        return summary_output