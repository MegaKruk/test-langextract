# test-langextract
Test project demonstrating LangExtract for extracting structured data from PDF forms in key-value format.

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file with your OpenAI API key:
```bash
OPENAI_API_KEY=sk-proj-your-key-here
```

3. Create data folder and add PDF files:
```bash
mkdir -p data
cp your-pdfs/*.pdf data/
```

## Usage
Run the extraction for basic, text version (requires text PDFs):
```bash
python main.py
```
Or for multimodal version (works for all PDFs):
```bash
python main_multimodal.py
```

Results will be saved to the `output/` folder:
- `extraction_results.json`  - Formatted JSON output
- `extraction_results.jsonl` - JSONL format
- `extraction_summary.txt`   - Summary report

## Project Structure
```
project_root/
├── main.py             # Main script (text version)
├── main_multimodal.py  # Main script (multimodal version)
├── requirements.txt    # Dependencies
├── .env                # .env with API key
├── data/               # Input PDFs
└── output/             # Results (auto-created)
```

## Configuration
Default model is `gpt-4o`. To change:
```python
extractor = PDFExtractor(model_id="gpt-4o-mini")
```
Or:
```python
MultimodalPDFExtractor(
    vision_model="gpt-4o",  # Need vision capabilities
    extraction_model="gpt-4o-mini"
)
```
## Requirements
- Python 3.11+
- OpenAI API key
