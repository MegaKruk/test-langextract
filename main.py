"""
PDF Key-Value Extraction using LangExtract
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
import textwrap
from datetime import datetime

import langextract as lx
from dotenv import load_dotenv

load_dotenv()


class PDFExtractor:
    """Handle PDF processing and key-value extraction using LangExtract"""

    def __init__(self, model_id: str = "gpt-4o"):
        """
        Initialize the extractor with model configuration

        Args:
            model_id: OpenAI model to use (default: gpt-4o)
        """
        self.model_id = model_id
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        # Define extraction prompt
        self.prompt = textwrap.dedent("""
            Extract key-value pairs from form documents.
            Focus on filled-in information, not empty fields.
            Extract field names as keys and their values.
            Use exact text from the document.
            Group related information with meaningful attributes.
            For personal details, employment info, and financial data, 
            extract complete information including all subfields.
        """)

        # Provide comprehensive examples for the model
        self.examples = self._create_examples()

    def _create_examples(self) -> List[lx.data.ExampleData]:
        """Create few-shot examples for the extraction task"""
        return [
            lx.data.ExampleData(
                text="Title: Mr  Surname: Smith  Forename(s): Jon  Date of Birth: 15/08/1983",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="personal_info",
                        extraction_text="Mr",
                        attributes={"field": "Title", "value": "Mr"}
                    ),
                    lx.data.Extraction(
                        extraction_class="personal_info",
                        extraction_text="Smith",
                        attributes={"field": "Surname", "value": "Smith"}
                    ),
                    lx.data.Extraction(
                        extraction_class="personal_info",
                        extraction_text="Jon",
                        attributes={"field": "Forename(s)", "value": "Jon"}
                    ),
                    lx.data.Extraction(
                        extraction_class="personal_info",
                        extraction_text="15/08/1983",
                        attributes={"field": "Date of Birth", "value": "15/08/1983"}
                    ),
                ]
            ),
            lx.data.ExampleData(
                text="Gross monthly income $ 42,000  Net monthly income $ 35,000  Account number: 93934950",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="financial_info",
                        extraction_text="42,000",
                        attributes={"field": "Gross monthly income", "value": "$42,000"}
                    ),
                    lx.data.Extraction(
                        extraction_class="financial_info",
                        extraction_text="35,000",
                        attributes={"field": "Net monthly income", "value": "$35,000"}
                    ),
                    lx.data.Extraction(
                        extraction_class="account_info",
                        extraction_text="93934950",
                        attributes={"field": "Account number", "value": "93934950"}
                    ),
                ]
            ),
        ]

    def extract_from_text(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Extract key-value pairs from text

        Args:
            text: Document text to process
            filename: Name of the source file

        Returns:
            Dictionary containing extraction results
        """
        print(f"Processing {filename}...")

        try:
            result = lx.extract(
                text_or_documents=text,
                prompt_description=self.prompt,
                examples=self.examples,
                model_id=self.model_id,
                api_key=self.api_key,
                fence_output=True,
                use_schema_constraints=False,
                extraction_passes=2,  # Multiple passes for better recall
                max_workers=5,  # Parallel processing
                max_char_buffer=2000  # Optimal chunk size for forms
            )

            # Process extractions into key-value format
            key_values = self._process_extractions(result)

            return {
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "model": self.model_id,
                "extractions_count": len(result.extractions) if result.extractions else 0,
                "key_values": key_values,
                "raw_extractions": [
                    {
                        "class": e.extraction_class,
                        "text": e.extraction_text,
                        "attributes": e.attributes
                    }
                    for e in (result.extractions or [])
                ]
            }

        except Exception as e:
            print(f"  Error processing {filename}: {str(e)}")
            return {
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "key_values": {},
                "raw_extractions": []
            }

    def _process_extractions(self, result) -> Dict[str, Any]:
        """
        Convert extractions to organized key-value pairs

        Args:
            result: LangExtract result object

        Returns:
            Dictionary of organized key-value pairs by category
        """
        key_values = {
            "personal_info": {},
            "employment_info": {},
            "financial_info": {},
            "account_info": {},
            "other_info": {}
        }

        if not result.extractions:
            return key_values

        for extraction in result.extractions:
            category = extraction.extraction_class

            # Ensure category exists
            if category not in key_values:
                category = "other_info"

            # Extract field and value from attributes
            if extraction.attributes:
                field = extraction.attributes.get("field", "unknown_field")
                value = extraction.attributes.get("value", extraction.extraction_text)

                # Store the key-value pair
                key_values[category][field] = value

        # Remove empty categories
        key_values = {k: v for k, v in key_values.items() if v}

        return key_values


def read_pdf_text(pdf_path: Path) -> str:
    """
    Read text from PDF file

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text from PDF
    """
    try:
        import PyPDF2

        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"

        return text

    except ImportError:
        print("PyPDF2 not installed. Install with: pip install PyPDF2")
        raise
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {str(e)}")
        return ""


def save_results(results: List[Dict], output_dir: Path):
    """
    Save extraction results to JSON and JSONL formats

    Args:
        results: List of extraction results
        output_dir: Output directory path
    """
    # Save as formatted JSON for readability
    json_path = output_dir / "extraction_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {json_path}")

    # Save as JSONL for LangExtract compatibility
    jsonl_path = output_dir / "extraction_results.jsonl"
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
    print(f"Saved JSONL to {jsonl_path}")

    # Save summary
    summary_path = output_dir / "extraction_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("PDF Key-Value Extraction Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total files processed: {len(results)}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")

        for result in results:
            f.write(f"\nFile: {result['filename']}\n")
            f.write("-" * 30 + "\n")
            if 'error' in result:
                f.write(f"Error: {result['error']}\n")
            else:
                f.write(f"Total extractions: {result['extractions_count']}\n")
                if result['key_values']:
                    f.write("Key-Value Pairs by Category:\n")
                    for category, kvs in result['key_values'].items():
                        f.write(f"{category}: {len(kvs)} pairs\n")

    print(f"Saved summary to {summary_path}")


def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("PDF Key-Value Extraction with LangExtract")
    print("=" * 60 + "\n")

    # Setup directories
    project_root = Path.cwd()
    data_dir = project_root / "data"
    output_dir = project_root / "output"

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Check data directory
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        print("Please create a 'data' folder and add PDF files.")
        return

    # Find all PDF files
    pdf_files = list(data_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {data_dir}")
        return

    print(f"Found {len(pdf_files)} PDF file(s) to process:\n")
    for pdf in pdf_files:
        print(f"- {pdf.name}")

    # Initialize extractor
    print("\nInitializing LangExtract with OpenAI...")
    try:
        extractor = PDFExtractor(model_id="gpt-4o")
    except ValueError as e:
        print(f"Error: {e}")
        print("Please add your OpenAI API key to .env file:")
        print("OPENAI_API_KEY=sk-proj-...")
        return

    # Process each PDF
    print("\nStarting extraction process...\n")
    results = []

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing {pdf_path.name}...")

        # Read PDF text
        pdf_text = read_pdf_text(pdf_path)

        if pdf_text:
            # Extract key-value pairs
            result = extractor.extract_from_text(pdf_text, pdf_path.name)
            results.append(result)

            # Print sample of extracted data
            if result['key_values']:
                print(f"Extracted {result['extractions_count']} items")
                for category, kvs in list(result['key_values'].items())[:2]:
                    if kvs:
                        sample_items = list(kvs.items())[:3]
                        print(f"\t{category}:")
                        for field, value in sample_items:
                            print(f"\t\t- {field}: {value}")
        else:
            print(f"Could not read text from {pdf_path.name}")
            results.append({
                "filename": pdf_path.name,
                "timestamp": datetime.now().isoformat(),
                "error": "Could not extract text from PDF",
                "key_values": {},
                "raw_extractions": []
            })

        print()

    # Save results
    print("Saving results...")
    save_results(results, output_dir)

    print("\n" + "=" * 60)
    print("Extraction Complete!")
    print(f"Results saved to: {output_dir}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
