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
import re
import uvicorn

load_dotenv()

app = FastAPI(
    title="PDF to Markdown Transcription API",
    description="API for transcribing PDFs to markdown using Mistral's vision model",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

class TranscriptionResponse(BaseModel):
    markdown_content: str

def clean_markdown(content: str) -> str:
   
    # Replace escaped newlines with actual newlines
    content = content.replace("\\n", "\n")
    
    # Remove any markdown code block wrapping
    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()
    if content.startswith("```markdown") and content.endswith("```"):
        content = content[10:-3].strip()
    
    # Clean up multiple consecutive blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Add two spaces at the end of lines that should have a line break
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.rstrip()
        # Add two spaces for line breaks on certain patterns
        if (line and not line.startswith('|') and  # Skip table rows
            not line.startswith('#') and  # Skip headers
            not line.startswith('---') and  # Skip horizontal rules
            not line.startswith('> ') and  # Skip blockquotes
            not line.endswith(':') and  # Skip lines ending with colon
            not line.endswith('.') and  # Skip lines ending with period
            not line.endswith('  ')):  # Skip lines already having line breaks
            line += '  '
        cleaned_lines.append(line)
    
    # Join lines back together
    content = '\n'.join(cleaned_lines)
    
    # Ensure proper spacing around horizontal rules
    content = re.sub(r'([^\n])\n---', r'\1\n\n---', content)
    content = re.sub(r'---\n([^\n])', r'---\n\n\1', content)
    
    # Ensure proper spacing around tables
    content = re.sub(r'([^\n])\n\|', r'\1\n\n|', content)
    content = re.sub(r'\|\n([^\n|])', r'|\n\n\1', content)
    
    # Convert email addresses to markdown links
    content = re.sub(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'[\1](mailto:\1)', content)
    
    # Clean up any remaining multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()

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
    """Process a section of the document using Pixtral vision model"""
    img_base64 = image_to_base64(section)
    
    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": """You are a document transcription assistant. Your task is to:
                    1. Carefully read and transcribe all text from the image
                    2. Preserve the document structure using markdown formatting
                    3. Use appropriate markdown syntax for:
                       - Headers (# for main headers, ## for subheaders, etc.)
                       - Lists (- or * for bullet points, 1. for numbered lists)
                       - Tables (using | for columns)
                       - Bold and italic text when apparent
                       - Code blocks when relevant (use triple backticks without language specifier)
                    4. Follow these Markdown formatting rules:
                       - Add blank lines before and after horizontal rules (---)
                       - Add blank lines before and after tables
                       - Add blank lines before and after code blocks
                       - Ensure proper indentation for nested lists
                       - Never use language specifiers in code blocks
                       - Never wrap the entire content in code blocks
                       - Use actual newlines instead of \n characters
                       - Add two spaces at the end of lines that need line breaks
                    5. Maintain the visual hierarchy and layout of the original document
                    6. Return ONLY the raw markdown content without any formatting markers or metadata
                    7. Do not wrap the response in markdown code blocks or any other markers"""
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Transcribe this document section into clean, raw markdown without any wrapping or escaping."
                },
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{img_base64}"
                }
            ]
        }
    ]
    
    # Run blocking API call in thread pool
    response = await asyncio.to_thread(
        mistral_client.chat.complete,
        model="pixtral-12b-2409",
        messages=messages,
        max_tokens=4000
    )
    
    return clean_markdown(response.choices[0].message.content)

@app.post("/transcribe/pdf", response_model=TranscriptionResponse)
async def transcribe_pdf(file: UploadFile):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Invalid PDF file")
    
    try:
        pdf_content = await file.read()
        
        pdf_images = convert_from_bytes(pdf_content, dpi=100, thread_count=4)
        
        full_markdown = []
        
        for page_num, image in enumerate(pdf_images, 1):
            sections = split_image_into_sections(image)
            
            # Process all sections in parallel
            section_tasks = [process_section(section) for section in sections]
            sections_md = await asyncio.gather(*section_tasks)
            
            page_content = f"## Page {page_num}\n\n" + "\n\n".join(
                section.strip() for section in sections_md if section.strip()
            )
            full_markdown.append(clean_markdown(page_content))
        
        final_markdown = "\n\n".join(full_markdown).strip()
        
        return TranscriptionResponse(markdown_content=final_markdown)
    
    except Exception as e:
        raise HTTPException(500, f"Processing error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=os.cpu_count())