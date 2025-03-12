import openai
#pip install transformers==4.38.2
import os
import subprocess
import time
import asyncio

class BaseAgent:
    async def run(self, *args, **kwargs):
        raise NotImplementedError("Agents must implement async run method")  
class EquationReviewAgent(BaseAgent):
    def __init__(self, openai_model="gpt-4o", nougat_model="0.1.0-base", output_dir="nougat_output"):
        """
        Initialize the agent.
        openai_model: The model name to be used for o1-mini.
        nougat_model: The Nougat model tag to use. (Default base model: "0.1.0-base")
        output_dir: Directory where Nougat will store the .mmd file.
        """
        self.model = openai_model
        self.nougat_model = nougat_model
        self.output_dir = output_dir
        # Initialize the OpenAI client (customize with your key)

    
    async def run(self, txt_content, pdf_path: str) -> str:
        """
        Reviews the equations present in a PDF manuscript.
        Steps:
        1. Calls Nougat to process the given PDF and output a markdown (mmd) file.
        2. Reads the generated markdown file containing the equations.
        3. (Optionally) converts the markdown to plain text.
        4. Crafts a detailed prompt asking the o1-mini model to review the equations.
        5. Returns the o1-mini response.
        """
        # Ensure the output directory exists
        # os.makedirs(self.output_dir, exist_ok=True)
        
        # # Step 1: Call Nougat via subprocess to process the PDF.
        # # Build the command:
        # #   nougat path/to/pdf -o output_dir -m nougat_model --markdown
        # nougat_cmd =  "nougat" +  " -o " + self.output_dir +" -m "+"0.1.0-small " + "--recompute --markdown --no-skipping pdf " +pdf_path
        # #+ "--recompute --no-skipping "
        #     # #"--recompute",
        #     # "-o", self.output_dir,
        #     # "-m", "0.1.0-small",
        #     # #"--full-precision",
        #     # #"--no-markdown",
        #     # #"--recompute",
        #     # # "-m", self.nougat_model,
        #     # # "--markdown"
        
        # try:
        #     print(f"Running Nougat on {pdf_path} ...")
        #     subprocess.run(nougat_cmd, check=True)
        # except subprocess.CalledProcessError as e:
        #     raise RuntimeError(f"Nougat processing failed: {e}")

        # # Step 2: Wait briefly to ensure file writing is complete, then read the markdown file.
        # # Nougat saves each PDF as a .mmd file named similarly to the PDF filename.
        # pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        # mmd_filename = os.path.join(self.output_dir, f"{pdf_basename}.mmd")
        # # txt_filename = f"{pdf_basename}.txt"
        # if not os.path.exists(mmd_filename):
        #     # If the expected filename is not found, try listing the output_dir for any mmd file
        #     mmd_files = [f for f in os.listdir(self.output_dir) if f.endswith(".mmd")]
        #     if mmd_files:
        #         mmd_filename = os.path.join(self.output_dir, mmd_files[0])
        #     else:
        #         raise FileNotFoundError("No markdown file (.mmd) found in the output directory.")

        # with open(mmd_filename, "r", encoding="utf-8") as f:
        #     markdown_content = f.read()
        
        # with open(txt_filename, "r", encoding="utf-8") as f:
            # txt_content = f.read()
        # Step 3: Optionally, convert markdown to plain text.
        # For simplicity, we can just remove simple markdown syntax like '#' or backticks.
        #plain_text = markdown_content#self._convert_markdown_to_plaintext(markdown_content)

        # Step 4: Construct a detailed prompt for reviewing the equations.
        prompt = f"""
        You are an expert academic reviewer specializing in mathematical and scientific notation.
        Below is a rendering of a PDF manuscript that comes from pymupdf4llm and is a markdown-based extraction. 
        
        
        Manuscript from pymupdf4llm:
        {txt_content}
        
        Please perform the following tasks:
        1. Analyze the clarity and correctness of the equations in the manuscript.
        2. Assess whether the equations are well explained and logically integrated into the 
           overall research context.
        3. Identify any errors, ambiguities, or formatting issues in the mathematical expressions.
        4. Offer suggestions for how the manuscript could improve its equation presentation, 
           including recommendations for additional explanations or alternative representations if needed.
        
        Provide your response in clear, academic language, and use Latex for all equations.
        """
        
        #Step 5: Call GPT-4o (or o1-mini) with the prompt.
        response = await asyncio.to_thread(openai.chat.completions.create,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=16384
        )
        
        return response.choices[0].message.content

    def _convert_markdown_to_plaintext(self, markdown_content: str) -> str:
        """
        A basic conversion from markdown to plain text by removing common markdown syntax.
        For a production system, consider using a library (like `mistune` or `markdown2`)
        to generate plain text.
        """
        # Remove headings (#), backticks, and extra whitespace.
        plain_text = markdown_content.replace("#", "")
        plain_text = plain_text.replace("`", "")
        # Optionally, remove any remaining markdown link syntax
        # For a simple solution, remove brackets and parentheses.
        plain_text = plain_text.replace("[", "").replace("]", "").replace("(", "").replace(")", "")
        return plain_text.strip()
