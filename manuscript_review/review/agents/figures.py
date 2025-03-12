import fitz  # PyMuPDF
import base64
import os
from openai import OpenAI
import asyncio
################################################################################
# 1. Extract Images from PDF with fitz
################################################################################
async def extract_images_from_pdf(pdf_path, output_dir="extracted_images"):
    """
    Extracts raster images from each page of a PDF using PyMuPDF (fitz).
    Saves them as PNGs (or JPEGs) and returns a list of filepaths.

    """
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    image_paths = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        pm=page.get_pixmap(dpi=400)
        pm.save('pdf_images/im_'+str(page_index)+'.png')
        image_path = 'pdf_images/im_'+str(page_index)+'.png'
        image_paths.append(image_path)

    doc.close()
    return image_paths

################################################################################
# 2. Encode Images to Base64
################################################################################
def encode_image_to_base64(image_path):
    """
    Reads the image at 'image_path' and returns a base64-encoded string.
    """
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    return encoded

################################################################################
# 3. Create GPT-4o Request with image in base64
################################################################################
async def ask_gpt4o_about_image(base64_image_str, question="What is in this image?", detail="auto"):
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

    response = await asyncio.to_thread(openai.chat.completions.create,
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

