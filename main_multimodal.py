"""
PDF Key-Value Extraction using Multimodal LLM + LangExtract
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import textwrap
from datetime import datetime
from io import BytesIO

import langextract as lx
from dotenv import load_dotenv
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image

# Load environment variables
load_dotenv()


class MultimodalPDFExtractor:
    """Use GPT-4 Vision to read PDFs, then LangExtract for structured extraction"""

    def __init__(self, vision_model: str = "gpt-4o", extraction_model: str = "gpt-4o"):
        """
        Initialize with multimodal and extraction models

        Args:
            vision_model: Model for reading PDF pages (needs vision capabilities)
            extraction_model: Model for structured extraction via LangExtract
        """
        self.vision_model = vision_model
        self.extraction_model = extraction_model
        self.api_key = os.getenv('OPENAI_API_KEY')

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        self.client = OpenAI(api_key=self.api_key)

        # LangExtract prompt and examples
        self.prompt = textwrap.dedent("""
            Extract key-value pairs from form documents.
            Focus on filled-in information, not empty fields.
            Extract field names as keys and their values.
            Use exact text from the document.
            Group related information with meaningful attributes.
            For personal details, employment info, and financial data, 
            extract complete information including all subfields.
        """)

        self.examples = self._create_examples()

    def _create_examples(self) -> List[lx.data.ExampleData]:
        """Create few-shot examples for LangExtract"""
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
                text="Gross monthly income $ 42,000  Account number: 93934950",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="financial_info",
                        extraction_text="42,000",
                        attributes={"field": "Gross monthly income", "value": "$42,000"}
                    ),
                    lx.data.Extraction(
                        extraction_class="account_info",
                        extraction_text="93934950",
                        attributes={"field": "Account number", "value": "93934950"}
                    ),
                ]
            ),
        ]

    def extract_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract key-value pairs from PDF using vision model + LangExtract

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with extraction results
        """
        filename = pdf_path.name
        print(f"Processing {filename}...")

        try:
            # Step 1: Convert PDF to images
            print(f"Converting PDF to images...")
            images = self._pdf_to_images(pdf_path)

            if not images:
                return self._error_result(filename, "Failed to convert PDF to images")

            # Step 2: Use vision model to read each page
            print(f"Reading {len(images)} pages with {self.vision_model}...")
            page_texts = []

            for i, image in enumerate(images):
                print(f"Page {i + 1}/{len(images)}...")
                text = self._read_image_with_vision(image, page_num=i + 1)
                if text:
                    page_texts.append(text)

            if not page_texts:
                return self._error_result(filename, "Could not extract text from PDF images")

            # Combine all page texts
            full_text = "\n\n--- Page Break ---\n\n".join(page_texts)
            print(f"Extracted {len(full_text)} characters total")

            # Step 3: Use LangExtract for structured extraction
            print(f"Running structured extraction with LangExtract...")
            result = lx.extract(
                text_or_documents=full_text,
                prompt_description=self.prompt,
                examples=self.examples,
                model_id=self.extraction_model,
                api_key=self.api_key,
                fence_output=True,
                use_schema_constraints=False,
                extraction_passes=2,
                max_workers=5,
                max_char_buffer=3000
            )

            key_values = self._process_extractions(result)

            return {
                "filename": filename,
                "timestamp": datetime.now().isoformat(),
                "vision_model": self.vision_model,
                "extraction_model": self.extraction_model,
                "pages": len(images),
                "text_length": len(full_text),
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
            print(f"Error processing {filename}: {str(e)}")
            return self._error_result(filename, str(e))

    def _pdf_to_images(self, pdf_path: Path) -> List[Image.Image]:
        """Convert PDF pages to images"""
        try:
            # Convert with reasonable DPI for form reading
            images = convert_from_path(pdf_path, dpi=150)
            return images
        except Exception as e:
            print(f"Error converting PDF: {str(e)}")
            return []

    def _read_image_with_vision(self, image: Image.Image, page_num: int) -> str:
        """
        Use GPT-4 Vision to read text from image

        Args:
            image: PIL Image object
            page_num: Page number for context

        Returns:
            Extracted text from the image
        """
        try:
            # Convert image to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # Call GPT-4 Vision
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Read and transcribe all text from this form/document page. Include all field names and their filled values. Preserve the structure and formatting as much as possible."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"# Use high detail for form reading
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1  # Low temperature for accurate transcription
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Vision API error: {str(e)}")
            return ""

    def _process_extractions(self, result) -> Dict[str, Any]:
        """Convert LangExtract results to organized key-value pairs"""
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

            if category not in key_values:
                category = "other_info"

            if extraction.attributes:
                field = extraction.attributes.get("field", "unknown_field")
                value = extraction.attributes.get("value", extraction.extraction_text)
                key_values[category][field] = value

        # Remove empty categories
        key_values = {k: v for k, v in key_values.items() if v}

        return key_values

    def _error_result(self, filename: str, error: str) -> Dict[str, Any]:
        """Create error result dictionary"""
        return {
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "key_values": {},
            "raw_extractions": []
        }


def save_results(results: List[Dict], output_dir: Path):
    """Save extraction results"""
    # JSON format
    json_path = output_dir / "extraction_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {json_path}")

    # JSONL format
    jsonl_path = output_dir / "extraction_results.jsonl"
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
    print(f"Saved JSONL to {jsonl_path}")

    # Summary
    summary_path = output_dir / "extraction_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("PDF Key-Value Extraction Summary (Multimodal)\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total files processed: {len(results)}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")

        for result in results:
            f.write(f"\nFile: {result['filename']}\n")
            f.write("-" * 30 + "\n")

            if 'error' in result:
                f.write(f"Error: {result['error']}\n")
            else:
                f.write(f"Pages: {result.get('pages', 'N/A')}\n")
                f.write(f"Text extracted: {result.get('text_length', 0)} chars\n")
                f.write(f"Total extractions: {result['extractions_count']}\n")

                if result['key_values']:
                    f.write("Key-Value Pairs by Category:\n")
                    for category, kvs in result['key_values'].items():
                        f.write(f"{category}: {len(kvs)} pairs\n")

    print(f"Saved summary to {summary_path}")


def check_dependencies():
    """Check required dependencies"""
    deps = {
        "openai": False,
        "pdf2image": False,
        "Pillow": False
    }

    try:
        import openai
        deps["openai"] = True
    except ImportError:
        pass

    try:
        import pdf2image
        deps["pdf2image"] = True
    except ImportError:
        pass

    try:
        from PIL import Image
        deps["Pillow"] = True
    except ImportError:
        pass

    print("Dependency Status:")
    print("-" * 30)
    for lib, installed in deps.items():
        status = "Installed" if installed else "✗ Not installed"
        print(f"{lib}: {status}")

    if not all(deps.values()):
        print("\nMissing dependencies. Install with:")
        print("pip install openai pdf2image Pillow")
        print("\nAlso need system packages:")
        print("- Ubuntu/Debian: apt-get install poppler-utils")
        print("- macOS: brew install poppler")
        return False

    print()
    return True


def main():
    """Main execution"""
    print("\n" + "=" * 60)
    print("Multimodal PDF Extraction (Vision + LangExtract)")
    print("=" * 60 + "\n")

    # Check dependencies
    if not check_dependencies():
        return

    # Setup directories
    project_root = Path.cwd()
    data_dir = project_root / "data"
    output_dir = project_root / "output"

    output_dir.mkdir(exist_ok=True)

    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        print("Please create a 'data' folder and add PDF files.")
        return

    # Find PDF files
    pdf_files = list(data_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {data_dir}")
        return

    print(f"Found {len(pdf_files)} PDF file(s) to process:\n")
    for pdf in pdf_files:
        print(f"- {pdf.name}")

    # Initialize extractor
    print("\nInitializing multimodal extractor...")
    print("Vision model: gpt-4o (for reading PDF pages)")
    print("Extraction model: gpt-4o (for structured extraction)")

    try:
        extractor = MultimodalPDFExtractor(
            vision_model="gpt-4o",  # Need vision capabilities
            extraction_model="gpt-4o"
        )
    except ValueError as e:
        print(f"Error: {e}")
        print("Please add your OpenAI API key to .env file:")
        print("OPENAI_API_KEY=sk-proj-...")
        return

    # Process PDFs
    print("\nStarting extraction...\n")
    results = []

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing {pdf_path.name}...")

        result = extractor.extract_from_pdf(pdf_path)
        results.append(result)

        # Print sample results
        if result['key_values']:
            print(f"Extracted {result['extractions_count']} items from {result.get('pages', 'N/A')} pages")
            for category, kvs in list(result['key_values'].items())[:2]:
                if kvs:
                    sample_items = list(kvs.items())[:3]
                    print(f"{category}:")
                    for field, value in sample_items:
                        print(f"- {field}: {value}")
        elif 'error' in result:
            print(f"Error: {result['error']}")

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
    