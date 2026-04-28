# Image to TikZ Converter

AI-powered web application for converting images to TikZ code using Hugging Face vision-language models.

## Features

- 🖼️ Drag & drop or file upload
- 📋 Paste images from clipboard (Ctrl+V)
- 🤖 AI-powered TikZ code generation
- 📝 One-click code copying
- ⚡ Multiple model support for optimal quality

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **AI**: Hugging Face Inference API
- **Image Processing**: Pillow

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd image-to-latex
```

2. Install dependencies:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. Configure Hugging Face token:
```bash
# Copy example config
cp .env.example .env

# Get your token at https://huggingface.co/settings/tokens
# Edit .env and add your token:
HF_TOKEN=hf_your_token_here
```

4. Run the application:
```bash
python app.py
# or simply run START.bat
```

Open http://localhost:5000 in your browser.

## Usage

1. Upload an image (drag & drop or Ctrl+V)
2. Click "Convert to TikZ"
3. Wait for processing (~30-60 seconds on first run)
4. Copy the generated TikZ code
5. Use in TeXmaker or Overleaf

## Supported Models

Configure in `.env` file:

### Qwen/Qwen2-VL-72B-Instruct (default)
- Best quality for complex diagrams
- Excellent math formula understanding
- Processing time: ~30-60 sec

### meta-llama/Llama-3.2-11B-Vision-Instruct
- Good balance of speed and quality
- Faster than Qwen
- Processing time: ~20-40 sec

### mistralai/Pixtral-12B-2409
- Specialized in math and scientific diagrams
- High accuracy for formulas
- Processing time: ~25-45 sec

Change model in `.env`:
```bash
MODEL_ID=meta-llama/Llama-3.2-11B-Vision-Instruct
```

## Supported Formats

PNG, JPG/JPEG, GIF, BMP, WEBP

## Troubleshooting

**401 Unauthorized**: Check your HF_TOKEN in `.env`

**503 Service Unavailable**: Model is loading (wait 30-60 sec) or try another model

**404 Model not found**: Verify model name in `.env`

## License

MIT
