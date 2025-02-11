# Document Understanding API

This FastAPI application processes PDFs and converts them to markdown format using Mistral's vision model.

## Features

- PDF processing with structure analysis
- Text file processing
- Markdown file processing
- Document structure understanding
- Table detection and analysis
- Headers and sections identification

## Prerequisites

- Python 3.8+
- Mistral API key
- Poppler (for PDF processing)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Poppler:
   - Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/
   - macOS: `brew install poppler`
   - Ubuntu/Debian: `sudo apt-get install poppler-utils`

5. Create a `.env` file in the root directory and add your Mistral API key:
```
MISTRAL_API_KEY=your_api_key_here
```

## Running the Application

Start the FastAPI server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Transcribe PDF
- **URL**: `/transcribe/pdf`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameter**: file (PDF file)
- **Response**: JSON object containing markdown content
```json
{
    "markdown_content": "The transcribed markdown content"
}
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`