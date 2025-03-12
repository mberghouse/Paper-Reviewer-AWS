import openai

class ComparisonAgent:
    def __init__(self, openai_model="gpt-4o"):
        self.model = openai_model

    def run(self, all_text: str, rubric: str = "Nature Communications guidelines") -> str:
        # Using the prompt from main.py as reference (lines 32-70)
        prompt = f"""
        You are an AI reviewer responsible for reviewing a manuscript according to the Nature Communications reviewer guidelines.  
        Don't use overly excessive markdown - the review should be well-organized but each heading/subheading should use multiple sentences to describe a point. 
        Always follow the numbering format of 1, subheading a. Never use subsubheadings. Generally, try to use 6+ sentence paragraphs for each subheading. 
        Try to be relatively concise, and try to make the review sound like a smart human (train of thought).

        The final review must include:
        
        1. **Summary Section**: A summary of the manuscript's overall aims, methods, findings, and context.
        2. **General Strengths and Weaknesses Section**: Overview of strengths and weaknesses.
        3. **Specific Recommendations Section**: Detailed feedback on introduction, methods, results, claims, clarity, and figures.
           Include at least 2 other recommendation subheadings.
           For each recommendation, provide line numbers when possible.
        4. **Manuscript Scoring and Decision Section**: Score originality, significance, technical quality, clarity, and conclusions.
           Include acceptance recommendation (Nature Communications has 8% acceptance rate).
           Both the scores and recommendation should primarily be determined by the included journal guidelines.
        5. **References**: List any papers you cite, verified via Google Scholar.

        Nature Communications Guidelines: {rubric}

        Your review should be clear, actionable, and at least 30 pages.
        Always include line numbers when possible.

        Here is the manuscript text:
        {all_text}
        """
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16000
        )
        import time
        time.sleep(10)
        return response.choices[0].message.content.strip()
