import os
import base64
import hashlib
import json
from .agents.methods import MethodsReproducibilityAgent
from .agents.summarization import SummarizationAgent
from .agents.claims import ClaimCheckAgent
from .agents.lit_review_papers import LitReviewPapersAgent
from .agents.flaws import DevilsAdvocate
from .agents.consistency import ConsistencyAgent
from .agents.stats import StatisticalMethodsAgent
from .agents.lines import ManuscriptIssuesAgent
from .agents.final import FinalAggregationAgent
from .agents.math import EquationReviewAgent
import pymupdf4llm
import fitz  # PyMuPDF
from typing import Dict, Any
import re
from typing import Dict, Any, List
import openai
import asyncio
import aiohttp
import uuid
import shutil

async def ask_gpt4o_about_images(base64_images: list, question: str, detail: str = "high") -> str:
    try:
        messages = []
        for idx, img in enumerate(base64_images, 1):
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Analyzing figure {idx}:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
                ]
            })
        
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": question}]
        })

        response = await asyncio.to_thread(openai.chat.completions.create,
            model="gpt-4o",
            messages=messages,
            max_tokens=16000,
            temperature=0.0
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in ask_gpt4o_about_images: {str(e)}")
        return f"Error analyzing images: {str(e)}"

def ask_gpt4o_about_image(base64_image_str, question="What is in this image?", detail="auto"):
    """
    Sends a single base64 image to GPT-4o with a question.
    The 'detail' parameter can be 'low', 'high', or 'auto'.
    Returns the model's response text.
    """
    #client = OpenAI()  # This is conceptual; adapt to your actual GPT-4o client usage.
    # Build the message content
    content_msg = [
        {
            "type": "text",
            "text": question
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image_str}",
                "detail": detail,
            }
        }
    ]
    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # or your actual GPT-4o model name
        messages=[
            {
                "role": "user",
                "content": content_msg
            }
        ],
        max_tokens=16384
    )
    # Assuming the response format matches your examples
    return response.choices[0].message.content
    
def process_math_review(file_path):
    # Add your math review logic here using the EquationReviewAgent
    # Example:
    
    agent = EquationReviewAgent()
    return agent.run(file_path)

def get_file_hash(file_path):
    """Generate a unique hash for a file based on its content."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def load_cached_data(file_hash, cache_dir="cache"):
    """Check if cached data exists and load it."""
    cache_file = os.path.join(cache_dir, f"{file_hash}.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_to_cache(file_hash, data, cache_dir="cache"):
    """Save extracted data to cache."""
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{file_hash}.json")
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)


def extract_and_cache_pdf_data(pdf_path):
    """Extract text and images from the PDF, caching the results for future use."""
    try:
        print(f"Starting extraction for {pdf_path}")
        
        # Verify file exists and is readable
        if not os.path.exists(pdf_path):
            print(f"Error: File not found at {pdf_path}")
            return None
            
        # Initialize parser
        parser = ThoroughDocumentParser()
        
        # Extract text with error handling
        try:
            extracted_text = parser.parse_pdf(pdf_path)
            print(f"Successfully extracted text from {pdf_path}")
        except Exception as e:
            print(f"Error extracting text: {str(e)}")
            return None
            
        # Extract images with error handling
        try:
            image_paths, unique_id = extract_images_from_pdf(pdf_path)
            print(f"Successfully extracted {len(image_paths)} images from {pdf_path}")
        except Exception as e:
            print(f"Error extracting images: {str(e)}")
            image_paths = []

        data = {
            "text": extracted_text,
            "images": image_paths,
            "unique_id": unique_id,
        }

        return data

    except Exception as e:
        print(f"Unexpected error in extract_and_cache_pdf_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# def extract_and_cache_pdf_data(pdf_path):
#     """Extract text and images from the PDF, caching the results for future use."""
#     # file_hash = get_file_hash(pdf_path)
#     # cached_data = load_cached_data(file_hash)

#     # if cached_data:
#         # print(f"Loaded cached data for {pdf_path}")
#         # return cached_data

#     print(f"Extracting data for {pdf_path}...")
#     parser = ThoroughDocumentParser()
#     extracted_text = parser.parse_pdf(pdf_path)
#     image_paths = extract_images_from_pdf(pdf_path)

#     data = {
#         "text": extracted_text,
#         "images": image_paths,
#     }

#     #save_to_cache(file_hash, data)
#     return data

async def extract_images_from_pdf_async(pdf_path, base_dir="extracted_images"):
    """Async version of image extraction"""
    try:
        os.makedirs(base_dir, exist_ok=True)
        unique_id = str(uuid.uuid4())[:8]
        output_dir = os.path.join(base_dir, unique_id)
        os.makedirs(output_dir, exist_ok=True)

        doc = fitz.open(pdf_path)
        tasks = []
        
        async def process_page(page_index):
            try:
                page = doc[page_index]
                pm = page.get_pixmap(dpi=400)
                image_path = os.path.join(output_dir, f"im_{page_index}.png")
                pm.save(image_path)
                return image_path
            except Exception as e:
                print(f"Error processing page {page_index}: {str(e)}")
                return None

        # Create tasks for all pages
        for page_index in range(len(doc)):
            tasks.append(asyncio.create_task(process_page(page_index)))
        
        # Wait for all tasks to complete
        image_paths = await asyncio.gather(*tasks)
        doc.close()
        
        # Filter out None values from failed extractions
        return [path for path in image_paths if path], unique_id

    except Exception as e:
        print(f"Error in extract_images_from_pdf_async: {str(e)}")
        return [], None

def encode_image_to_base64(image_path):
    """Reads the image and returns a base64-encoded string."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

async def run_agent(agent, *args, **kwargs):
    """Asynchronously runs an agent's run method with detailed logging."""
    agent_name = agent.__class__.__name__
    print(f"Starting {agent_name}")
    try:
        result = await agent.run(*args, **kwargs)
        print(f"{agent_name} completed successfully")
        return result
    except Exception as e:
        print(f"{agent_name} failed with error: {str(e)}")
        return f"Error in {agent_name}: {str(e)}"

async def process_full_review_async(file_path, include_math=False):
    """
    Asynchronously generate the full review for a manuscript.
    Includes math review only if `include_math` is True.
    """
    image_dir_id = None
    try:
        print("Starting text extraction")
        all_text = pymupdf4llm.to_markdown(file_path) 
        print("Text extraction complete")
        
        # Start image extraction in parallel with initial text analysis
        image_extraction_task = asyncio.create_task(extract_images_from_pdf_async(file_path))
        
        print("Initializing agents")
        # Initialize agents
        summarization_agent = SummarizationAgent()
        methods_agent = MethodsReproducibilityAgent(openai_model="o1-mini")
        lit_review_agent = LitReviewPapersAgent()
        stats_agent = StatisticalMethodsAgent()
        consistency_agent = ConsistencyAgent()
        flaws_agent = DevilsAdvocate()
        math_agent = EquationReviewAgent()
            
        # List of coroutines for agents that can run concurrently
        agent_tasks = [
            asyncio.create_task(run_agent(summarization_agent, all_text)),
            asyncio.create_task(run_agent(methods_agent, all_text)),
            asyncio.create_task(run_agent(lit_review_agent, all_text)),
            asyncio.create_task(run_agent(stats_agent, all_text)),
            asyncio.create_task(run_agent(consistency_agent, all_text)),
            asyncio.create_task(run_agent(flaws_agent, all_text)),
            asyncio.create_task(run_agent(math_agent, all_text, file_path)),
        ]

        # Wait for all agent tasks to complete
        print("Starting parallel agent tasks")
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*agent_tasks, return_exceptions=True),
                timeout=700  # 8 minutes timeout for all primary agents
            )
        except asyncio.TimeoutError:
            print("Primary agents timeout - some reviews may be incomplete")
            results = ["Timeout occurred during review"] * len(agent_tasks)
        
        # Get image extraction results
        image_paths, image_dir_id = await image_extraction_task
        print(f"Image extraction complete. Found {len(image_paths)} images")
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Agent {i} failed with error: {str(result)}")
                results[i] = f"Error in agent execution: {str(result)}"
            
        print("All agent tasks completed")

        # Extract individual results
        summary_review = results[0]
        methods_review = results[1]
        lit_review = results[2]
        stats_review = results[3]
        consistency_review = results[4]
        flaws_review = results[5]
        math_review = results[6]
        
        # Run dependent agents in parallel
        print("Starting dependent agents")
        dependent_tasks = [
            asyncio.create_task(run_agent(ManuscriptIssuesAgent(), all_text, summary_review)),
            asyncio.create_task(run_agent(ClaimCheckAgent(summary_review), all_text))
        ]
        
        dependent_results = await asyncio.gather(*dependent_tasks)
        issues_review = dependent_results[0]
        claims_review = dependent_results[1]

        print("Starting image review agent")
        if image_paths:
            encoded_images = [encode_image_to_base64(img_path) for img_path in image_paths]
            image_reviews_string = await ask_gpt4o_about_images(
                base64_images=encoded_images,
                question=(
                    "Provide a summary of each figure and then summarize how all the figures "
                    "work together, as if you are reviewing a manuscript submission."
                    "Use the manuscript text below to understand the context of each figure and suggest improvements to how the figures are discussed."
                    "Use thecaptions to improve your understanding of each figure. If a figure is a "
                    "scatter plot or line graph on an x-y axis, please extract some data points "
                    "to inform your analysis. Review each figure in terms of clarity, presentation, "
                    "and importance to the manuscript. Also look for and note any potential typos in the figure or captions."
                    "Finally, provide a detailed summary of the top 5 ways to improve the way figures are used in the manuscript."
                ),
                detail="high"
            )
        else:
            image_reviews_string = "No figures found in the manuscript."

        # Compile all reviews
        reviews = {
            "equation_review": math_review,
            "lit_review": lit_review,
            "issues_review": issues_review,
            "stats_review": stats_review,
            "flaws_review": flaws_review,
            "claims_review": claims_review,
            "summary_review": summary_review,
            "image_reviews": image_reviews_string,
            "methods_review": methods_review,
            "consistency_review": consistency_review
        }

        # Prepare rubric (keeping your existing rubric)
        rubric = """
        Thank you for agreeing to review for a Nature Portfolio journal. Your feedback will be very valuable, and we thank you in advance for your time.

        If you are interested, please see our overview of the editorial process.

        Criteria for publication
        Your report is vital in helping our editors decide if the manuscript meets the journal's criteria for publication, and we ask you to keep the following factors in mind when you write your report:

        The quality of the data — whether they are technically sound, obtained with appropriate techniques, analysed and interpreted carefully, and presented in sufficient detail.
        The level of support for the conclusions — whether sufficiently strong evidence is provided for the authors' claims and all appropriate controls have been included.
        The potential significance of the results — whether these results will be important to the field and advance understanding in a way that will move the field forward. (Note that posting of preprints and/or conference proceedings does not compromise novelty.)
        Please also consult the instructions provided directly by the editor, which may provide more detail or specific instructions for the manuscript under consideration.

        Depending on the manuscript's research area, in addition to the files containing the manuscript and any supplementary information, you might also have access to reporting summaries and editorial policy checklists. These documents contain additional information to help you in the assessment of the work.

        The primary purpose of your review is to provide feedback on the soundness of the research reported. This will help authors to improve their manuscript and editors to reach a decision. We do not ask that you make a recommendation regarding publication, but you can set out the arguments for and against publication if you so wish.

        Elements of a reviewer report
        In your report, please comment on the following aspects of the manuscript.

        Key results
        Your overview of the key messages of the study, in your own words, highlighting what you find significant or notable. Usually, this can be summarized in a short paragraph.

        Validity
        Your evaluation of the validity and robustness of the data interpretation and conclusions. If you feel there are flaws that prohibit the manuscript's publication, please describe them in detail.

        Significance
        Your view on the potential significance of the conclusions for the field and related fields. If you think that other findings in the published literature compromise the manuscript's significance, please provide relevant references.

        Data and methodology
        Your assessment of the validity of the approach, the quality of the data, and the quality of presentation. We ask reviewers to assess all data, including those provided as supplementary information. If any aspect of the data is outside the scope of your expertise, please note this in your report or in the comments to the editor. We may, on a case-by-case basis, ask reviewers to check code provided by the authors (see this Nature editorial for more information).

        Reviewers have the right to view the data and code that underlie the work if it would help in the evaluation, even if these have not been provided with the submission (see this Nature editorial). If essential data are not available, please contact the editor to obtain them before submitting the report.

        Analytical approach
        Your assessment of the strength of the analytical approach, including the validity and comprehensiveness of any statistical tests. If any aspect of the analytical approach is outside the scope of your expertise, please note this in your report or in the comments to the editor.

        Suggested improvements
        Your suggestions for additional experiments or data that could help strengthen the work and make it suitable for publication in the journal. Suggestions should be limited to the present scope of the manuscript; that is, they should only include what can be reasonably addressed in a revision and exclude what would significantly change the scope of the work. The editor will assess all the suggestions received and provide additional guidance to the authors.

        Clarity and context
        Your view on the clarity and accessibility of the text, and whether the results have been provided with sufficient context and consideration of previous work. Note that we are not asking for you to comment on language issues such as spelling or grammatical mistakes.

        References
        Your view on whether the manuscript references previous literature appropriately.

        Your expertise
        Please indicate any particular part of the manuscript, data or analyses that you feel is outside the scope of your expertise, or that you were unable to assess fully.

        Providing constructive feedback
        We ask reviewers to approach peer review with a sincere intention to help the authors improve their manuscripts. Nearly all submissions have weaknesses to be addressed: the best and most constructive reports suggest specific improvements; such feedback can be used by authors to improve their manuscript to the point where it might be suitable for acceptance. Even in instances where manuscripts are rejected, your report will help authors interpret the editor's decision and improve their work prior to submission elsewhere.

        You should be direct in your report, but you should also maintain a respectful tone. As a matter of policy, we do not censor the content of reviewer reports; any comments that were intended for the authors are transmitted, regardless of what we may think of the content. On rare occasions, we may edit a report to remove offensive language or comments that reveal confidential information about other matters.
        """

        print("Finished all primary reviews")
        return reviews, all_text, rubric

    except Exception as e:
        print(f"Error in process_full_review_async: {str(e)}")
        return f"Error processing review: {str(e)}"
    
    finally:
        # Clean up the image directory if it was created
        if image_dir_id:
            cleanup_path = os.path.join("extracted_images", image_dir_id)
            try:
                if os.path.exists(cleanup_path):
                    shutil.rmtree(cleanup_path)
                    print(f"Cleaned up image directory: {cleanup_path}")
            except Exception as e:
                print(f"Error cleaning up image directory: {str(e)}")

def process_final_review(reviews,all_text,rubric):  
    print("Starting final review")
    final_agent = FinalAggregationAgent()
    final_review = final_agent.run(reviews, all_text, rubric)
    print("Final review completed")
    return final_review

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        raise e

