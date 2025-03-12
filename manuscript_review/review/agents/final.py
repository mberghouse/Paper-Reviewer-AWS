import openai
class FinalAggregationAgent:
    def __init__(self, openai_model="gpt-4o"):
        self.model = openai_model

    def run(self, reviews: dict,all_text:str, rubric: str = "Nature Communications guidelines") -> str:
        prompt = f"""
        You are an AI reviewer responsible for reviewing a manuscript and synthesizing your own review with detailed AI-generated reviews into a final comprehensive analysis following the Nature Communications reviewer guidelines.  
        Don't use overly excessive markdown - the review should be well-organized but each heading/subheading should use multiple sentences to describe a point. 
        Always follow the numbering format of 1, subheading a. Never use subsubheadings. Generally, try to use 6+ sentence paragraphs for each subheading. 
        Try to be relatively concise, and try to make the review sound like a smart human (train of thought). Don't provide too much structure in your output. Some sections will require more explanation and will be longer than others.
        Above all, the review should be extremely thorough and robust, and full of examples given as a person would when delivering train of thought comments/writing.
        
        The final review must at least include:
        
        1. **Summary Section**: A summary of the manuscript's overall aims, methods, findings, and context in 
           relation to the field.
        2. **General Strengths and Weaknesses Section**: An overview of the manuscript's strengths (e.g., novelty, 
           robustness of findings) and its weaknesses (e.g., unclear methodology, unsupported claims, flaws in logic).
        3. **Specific Recommendations Section**: Detailed, actionable feedback organized by key areas of improvement, 
           including introduction and literature review (please include all relevant new references from the AI-generated literature review below), 
           methods (especially statistical/mathematical), results, claims, writing clarity, and figures (provide a general review of how well the figures back up the claims and specific recommendations for particular figures that require fixing). Each section of the specific recommendations should have at least 4 keys points that are each explained in paragraph format.
           Include at least 3 other recommendation subheadings based on your analysis of the reviews and manuscript text.
           Be detailed in terms of the problem needing revision and why it's important to revise them.
           For each of the specific recommendations, ALWAYS provide the general lines or page number from the original manuscript text for the thing you are referencing. 
           If you have the exact line numbers, that is even better.
        4. **Manuscript Scoring and Decision Section**: Assign scores for originality, significance to the field, 
           technical quality, clarity, and validity of conclusions. Include a recommendation for acceptance, 
           major revisions, minor revisions, or rejection. Both the scores and recommendation should primarily be determined by the included journal guidelines.
        5. **References**: A section for any addititional or in-text references that you bring up in your review. 
           These references should all come from the AI-generated literature review or the original manuscript text. 
           Only put references in this section if they are explicitly cited in the review that you generate.
           References in your review should start with the number 1 and be organized in the order they appear in your review, 
           regardless of the order they are cited in the AI-generated literature review or the original manuscript text.

        The final review should include the most of the content of each of the following reviews. 
        NEVER mention any of these reviews by name in your response:
        
        Summary Review:
        {reviews.get('summary_review', 'No summary review provided.')}

        Literature Review:
        {reviews.get('lit_review', 'No literature review provided.')}

        Methods Review:
        {reviews.get('methods_review', 'No methods review provided.')}
        
        Statistical Methods Review:
        {reviews.get('stats_review', 'No statistical methods review provided.')}
        
        Equation Review:
        {reviews.get('equation_review', 'No equation review provided.')}

        Issues Review:
        {reviews.get('issues_review', 'No issues review provided.')}

        Flaws Review:
        {reviews.get('flaws_review', 'No flaws review provided.')}

        Claims Review:
        {reviews.get('claims_review', 'No claims review provided.')}

        Image Review:
        {reviews.get('image_reviews', 'No image review provided.')}


        Nature Communications Guidelines: {rubric}
 
        Your review should not be repetitive at all, and should be at least 30 pages in length. 
        You must make sure all content of the review is clear, it contains actionable feedback, and it adheres to the Nature Communications reviewer guidelines.
        NEVER REPEAT FULL SECTIONS.
        Always include manuscript line numbers when possible.

        Here is the original manuscript text:
        {all_text}
        
        """
        response = openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16384
        )
        final_review = response.choices[0].message.content.strip()
        return final_review
        
        
