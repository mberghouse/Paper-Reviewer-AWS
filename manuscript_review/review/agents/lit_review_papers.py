import openai
import json
import os
from paperscraper import dump_queries
import asyncio
class BaseAgent:
    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agents must implement run method")

class LitReviewPapersAgent(BaseAgent):
    def __init__(self, openai_model="gpt-4o"):
        self.model = openai_model

    def get_key_phrases(self, manuscript_text: str) -> list:
        """Extract key phrases using GPT-4"""
        prompt = f"""
        Given this manuscript text, identify the 5 most important keywords or phrases that best describe 
        the core topic and methodology. The first keyword should be the primary topic. Do not include keywords that correspond to new named creations.
        Order them from most important to least important. Keywords/phrases should aim to be 1 or 2 words.
        Return only the 5 keywords/phrases in a comma-separated list.

        Text: {manuscript_text}
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}], 
            temperature=0.0,
        )
        
        keywords = response.choices[0].message.content.strip().split(',')
        keywords = [k.strip() for k in keywords]
        return keywords

    def generate_queries(self, keywords: list) -> list:
        """Generate query combinations"""
        primary = keywords[0]
        queries = [
            [primary, keywords[1]],
            [primary, keywords[1], keywords[2]],
            [primary, keywords[1], keywords[3]],
            [primary, keywords[1], keywords[4]],
            [primary, keywords[2], keywords[3]],
            [primary, keywords[3], keywords[4]],
            [keywords[1], keywords[2], keywords[3]],
            [keywords[1], keywords[2], keywords[4]],
            [keywords[1], keywords[3], keywords[4]],
        ]
        return queries

    def extract_paper_data(self, base_path: str, keywords: list) -> list:
        """Extract data from JSONL files"""
        papers_data = []
        folders = ['arxiv', 'medrxiv', 'pubmed']
        
        # Construct the correct base path
        base_path = os.path.join('C:', 'Users', 'marc', 'Desktop', 'ReviewAI2', 'ReviewAI', 'src', 'manuscript_review')
        print(f"Searching in base path: {base_path}")
        print(f"Using keywords queries: {keywords}")
        
        for folder in folders:
            if len(papers_data) >= 90:  # Check if we've reached the limit
                print(f"\nReached 80 papers limit. Stopping extraction.")
                break
            
            folder_path = os.path.join(base_path, folder)
            print(f"\nChecking folder: {folder_path}")
            if not os.path.exists(folder_path):
                print(f"Folder does not exist: {folder_path}")
                continue
                
            for query in keywords:
                if len(papers_data) >= 90:  # Check if we've reached the limit
                    break
                
                filename = '_'.join(query).lower().replace(' ', '') + '.jsonl'
                file_path = os.path.join(folder_path, filename)
                print(f"Looking for file: {file_path}")
                
                if os.path.exists(file_path):
                    print(f"Found file: {file_path}")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            paper_count = 0
                            for line in f:
                                if len(papers_data) >= 90:  # Check if we've reached the limit
                                    break
                                try:
                                    paper = json.loads(line.strip())
                                    papers_data.append({
                                        'title': paper.get('title', ''),
                                        'abstract': paper.get('abstract', ''),
                                        'date': paper.get('date', ''),
                                        'authors': paper.get('authors', '')
                                    })
                                    paper_count += 1
                                except json.JSONDecodeError as e:
                                    print(f"Error parsing JSON line in {file_path}: {str(e)}")
                                    continue
                            print(f"Loaded {paper_count} papers from {file_path}")
                    except Exception as e:
                        print(f"Error processing {file_path}: {str(e)}")
                else:
                    print(f"File does not exist: {file_path}")
        
        print(f"\nTotal papers collected: {len(papers_data)}")
        return papers_data

    async def run(self, manuscript_text: str) -> str:
        # Get key phrases
        keywords = self.get_key_phrases(manuscript_text)
        print("Generated keywords:", keywords)
        
        # Generate and run queries
        queries = self.generate_queries(keywords)
        print("Generated queries:", queries)
        
        # Use the correct base path for dump_queries too
        base_path = os.path.join('C:', 'Users', 'marc', 'Desktop', 'ReviewAI2', 'ReviewAI', 'src', 'manuscript_review')
        dump_queries(queries, base_path)
        print("Queries dumped to files")

        # Extract paper data
        papers_data = self.extract_paper_data(base_path, queries)
        if not papers_data:
            print("Warning: No papers were found in the data extraction")
            return "Error: No relevant papers found in the literature search."
            
        print(f"Successfully extracted {len(papers_data)} papers")
        
        # Format papers data for prompt
        papers_text = ""
        for i, paper in enumerate(papers_data):
            papers_text += f"\nPaper {i+1}:\nTitle: {paper['title']}\nAuthors: {paper['authors']}\nDate: {paper['date']}\nAbstract: {paper['abstract']}\n---"
        
        # Rest of the function remains the same...
        # Rest of the function remains the same...
        # Generate literature review using o1-mini
        prompt = f"""
        You are an expert researcher and literature review specialist. You have been provided with:
        1. The manuscript text being reviewed
        2. A collection of relevant papers from arxiv, medrxiv, and pubmed
        
        Based on this information, please:
        1. Analyze how the manuscript's work relates to and builds upon existing literature
        2. Identify any gaps in the manuscript's literature review
        3. Suggest specific new papers that should be cited (from the provided papers). Mention at least 10 new papers that should be cited.
        4. Provide a detailed analysis of how the current work fits into the broader research landscape
        5. Provide a bibliography for all the papers cited in your review. Start with the number 1 and continue in the order each reference appears in your review.

        Please be extremely detailed and specific in your review, but only suggest revisions/additions that will almost certainly improve the quality of the manuscript.
        Your review should be at least 10 pages in length.

        Manuscript Text:
        {manuscript_text}
        
        Relevant Papers:
        {papers_text}
        """

        response = await asyncio.to_thread(openai.chat.completions.create,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16384
        )
        
        return response.choices[0].message.content.strip()