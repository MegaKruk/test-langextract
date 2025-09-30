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
Run the extraction:
```bash
python main.py
```

Results will be saved to the `output/` folder:
- `extraction_results.json`  - Formatted JSON output
- `extraction_results.jsonl` - JSONL format
- `extraction_summary.txt`   - Summary report

## Project Structure
```
project_root/
├── main.py             # Main script
├── requirements.txt    # Dependencies
├── .env                # .env with API key
├── data/               # Input PDFs
└── output/             # Results (auto-created)
```

## How It Works
The script:
1. Reads all PDFs from the `data/` folder
2. Extracts text using PyPDF2
3. Uses LangExtract with OpenAI to identify key-value pairs
4. Organizes results by category (personal info, financial info, etc.)
5. Saves structured output to JSON files

## Configuration
Default model is `gpt-4o`. To change:

```python
extractor = PDFExtractor(model_id="gpt-4o-mini")
```

## Requirements
- Python 3.12+
- OpenAI API key
