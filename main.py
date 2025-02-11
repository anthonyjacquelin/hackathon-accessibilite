from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mistralai import Mistral
import os
from dotenv import load_dotenv
from pdf2image import convert_from_bytes
from PIL import Image
import io
import base64
from pydantic import BaseModel
import asyncio

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="PDF to Markdown Transcription API",
    description="API for transcribing PDFs to markdown using Mistral's vision model",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Mistral client
mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

class TranscriptionResponse(BaseModel):
    markdown_content: str

def image_to_base64(image: Image.Image, max_size: tuple = (600, 800)) -> str:
    """Optimized image processing with efficient resizing and compression"""
    width, height = image.size
    aspect_ratio = width / height
    
    # Calculate target dimensions
    if width > max_size[0] or height > max_size[1]:
        if aspect_ratio > 1:
            new_width = min(width, max_size[0])
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = min(height, max_size[1])
            new_width = int(new_height * aspect_ratio)
        
        image = image.resize((new_width, new_height), Image.Resampling.BILINEAR)
    
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=75, optimize=True)
    return base64.b64encode(buffered.getvalue()).decode()

def split_image_into_sections(image: Image.Image, max_height: int = 2000) -> list[Image.Image]:
    """Efficient image splitting with larger section size"""
    width, height = image.size
    return [image] if height <= max_height else [
        image.crop((0, y, width, min(y + max_height, height)))
        for y in range(0, height, max_height)
    ]

async def process_section(section: Image.Image) -> str:
    """Parallel section processing with optimized API call"""
    img_base64 = image_to_base64(section)
    messages = [
        {
            "role": "system",
            "content": """Transcribe this document section into markdown preserving structure, 
                        formatting, headers, lists, tables, and code blocks using appropriate syntax."""
        },
        {
            "role": "user",
            "content": f"<img>{img_base64}</img>\nConvert this document section to markdown."
        }
    ]
    
    # Run blocking API call in thread pool
    response = await asyncio.to_thread(
        mistral_client.chat.complete,
        model="mistral-large-latest",
        messages=messages,
        max_tokens=4000
    )
    return response.choices[0].message.content

@app.post("/transcribe/pdf", response_model=TranscriptionResponse)
async def transcribe_pdf(file: UploadFile):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Invalid PDF file")
    
    try:
        pdf_content = await file.read()
        pdf_images = convert_from_bytes(pdf_content, dpi=100, thread_count=4)
        
        full_markdown = []
        page_tasks = []
        
        for page_num, image in enumerate(pdf_images, 1):
            sections = split_image_into_sections(image)
            
            # Process all sections in parallel
            section_tasks = [process_section(section) for section in sections]
            sections_md = await asyncio.gather(*section_tasks)
            
            page_content = f"\n\n## Page {page_num}\n\n" + "\n\n".join(sections_md)
            full_markdown.append(page_content)
        
        return TranscriptionResponse(markdown_content="\n".join(full_markdown).strip())
    
    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=os.cpu_count())