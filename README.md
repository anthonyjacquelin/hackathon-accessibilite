# Document Understanding API

This FastAPI application processes PDFs, text files, and markdown documents using Mistral's AI models to understand document structure and content.

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

4. Create a `.env` file in the root directory and add your Mistral API key:
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

### 1. Process PDF
- **URL**: `/process/pdf`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameter**: file (PDF file)

### 2. Process Text
- **URL**: `/process/text`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameter**: file (Text file)

### 3. Process Markdown
- **URL**: `/process/markdown`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameter**: file (Markdown file)

## Response Format

All endpoints return a JSON response with the following structure:
```json
{
    "content": "The extracted text content",
    "structure": {
        // Document structure analysis
    }
}
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc` 