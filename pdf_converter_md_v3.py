"""
PDFConverter Class for converting various document formats to PDF.

This class handles conversion of documents (DOCX, DOC, RTF), spreadsheets (XLS, XLSX),
and images (JPG, JPEG, PNG, TIF, SVG) to PDF format.

Current Implementation: Uses Markdown pipeline for documents (pip-only, no LibreOffice)
- DOCX -> Markdown -> PDF (preserves structure: headings, lists, tables, bold/italic)
- DOC -> Markdown -> PDF (best effort)
- RTF -> Markdown -> PDF (basic structure)

IMPROVED SPREADSHEET HANDLING:
- Intelligent column width calculation
- Multi-line headers and cells (ALL wrapped in Paragraphs)
- Aggressive content limiting to prevent overflow
- Smart table splitting with row indices
- Robust error handling

Future: Will integrate with AzureSql and ADLSConnect
"""

import os
import tempfile
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# Placeholder for AzureSql (not yet ready)
class AzureSql:
    """Placeholder for AzureSql class."""
    pass

# ADLSConnect can be imported but connection not set up yet
try:
    from data_io.adls.adls_connect import ADLSConnect
except ImportError:
    class ADLSConnect:
        """Placeholder for ADLSConnect class."""
        pass


class PDFConverter:
    """
    A class to convert various file formats to PDF using pip-installable packages only.
    
    Supported formats:
    - Documents: docx, doc, rtf (via Markdown pipeline)
    - Spreadsheets: xls, xlsx
    - Images: jpg, jpeg, png, tif, svg
    
    Files that are already PDF or have unsupported extensions are skipped.
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        'docx', 'doc', 'rtf',               # Documents (via Markdown)
        'xls', 'xlsx',                      # Spreadsheets
        'jpg', 'jpeg', 'png', 'tif', 'svg'  # Images
    }
    
    DOCUMENT_EXTENSIONS = {'docx', 'doc', 'rtf'}
    SPREADSHEET_EXTENSIONS = {'xls', 'xlsx'}
    IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'tif', 'svg'}
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize PDFConverter.
        
        Parameters:
        -----------
        output_dir : str, optional
            Directory where converted PDFs will be saved.
            If None, uses a temporary directory.
        """
        self.output_dir = output_dir or tempfile.mkdtemp(prefix='pdf_converter_')
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"PDFConverter initialized with output directory: {self.output_dir}")
        
        # Check required packages
        self._check_required_packages()
        
    def _check_required_packages(self) -> None:
        """Check if required Python packages are installed."""
        required_packages = {
            'mammoth': 'mammoth',        # DOCX to Markdown
            'markdown': 'markdown',      # Markdown parsing
            'striprtf': 'striprtf',      # RTF to text
            'openpyxl': 'openpyxl',      # XLSX reading
            'xlrd': 'xlrd',              # XLS reading
            'PIL': 'Pillow',             # Image processing
            'reportlab': 'reportlab'     # PDF generation
        }
        
        missing = []
        for module, package in required_packages.items():
            try:
                __import__(module)
            except ImportError:
                missing.append(package)
        
        if missing:
            print(f"Warning: Missing packages: {', '.join(missing)}")
            print(f"Install with: pip install {' '.join(missing)}")
        else:
            print("All required packages are installed")
    
    def is_supported_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Check if the file is supported for conversion.
        
        Parameters:
        -----------
        file_path : str
            Path to the file to check
            
        Returns:
        --------
        Tuple[bool, str] : (is_supported, reason)
            is_supported: True if file can be converted, False otherwise
            reason: Explanation of why file is/isn't supported
        """
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_path_lower = file_path.lower()
        
        # Extract extension, handling malformed extensions
        ext = os.path.splitext(file_path_lower)[1]
        if ext:
            ext = ext.lstrip('.')
        else:
            return False, "No file extension found"
        
        # Check for malformed extensions (e.g., '.23).pdf', '.pdf;')
        if not ext.isalnum():
            return False, f"Malformed extension: {ext}"
        
        # Skip if already a PDF
        if ext == 'pdf':
            return False, "File is already a PDF"
        
        # Check if extension is supported
        if ext not in self.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported extension: {ext}"
        
        return True, f"Supported {self._get_file_category(ext)} file"
    
    def _get_file_category(self, ext: str) -> str:
        """Get the category of a file based on its extension."""
        if ext in self.DOCUMENT_EXTENSIONS:
            return "document"
        elif ext in self.SPREADSHEET_EXTENSIONS:
            return "spreadsheet"
        elif ext in self.IMAGE_EXTENSIONS:
            return "image"
        return "unknown"
    
    def convert_to_pdf(
        self,
        input_path: str,
        output_filename: Optional[str] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        Convert a file to PDF.
        
        Parameters:
        -----------
        input_path : str
            Path to the input file
        output_filename : str, optional
            Name for the output PDF file. If None, generates from input filename.
            
        Returns:
        --------
        Tuple[bool, Optional[str], str] : (success, output_path, message)
            success: True if conversion succeeded
            output_path: Path to converted PDF, or None if failed
            message: Status message
        """
        # Check if file is supported
        is_supported, reason = self.is_supported_file(input_path)
        if not is_supported:
            print(f"Skipping {input_path}: {reason}")
            return False, None, reason
        
        # Generate output filename if not provided
        if output_filename is None:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{base_name}.pdf"
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Get file extension
        ext = os.path.splitext(input_path.lower())[1].lstrip('.')
        
        try:
            # Route to appropriate conversion method
            if ext in self.DOCUMENT_EXTENSIONS:
                success = self._convert_document_to_pdf(input_path, output_path, ext)
            elif ext in self.SPREADSHEET_EXTENSIONS:
                success = self._convert_spreadsheet_to_pdf(input_path, output_path)
            elif ext in self.IMAGE_EXTENSIONS:
                success = self._convert_image_to_pdf(input_path, output_path)
            else:
                return False, None, f"Unsupported file type: {ext}"
            
            if success:
                print(f"Successfully converted {os.path.basename(input_path)} to {os.path.basename(output_path)}")
                return True, output_path, "Conversion successful"
            else:
                return False, None, "Conversion failed"
                
        except Exception as e:
            print(f"Error converting {input_path}: {str(e)}")
            return False, None, f"Error: {str(e)}"
    
    def _convert_document_to_pdf(self, input_path: str, output_path: str, ext: str) -> bool:
        """
        Convert document (DOCX/DOC/RTF) to PDF via Markdown pipeline.
        
        Pipeline: Document -> Markdown -> PDF
        Preserves: Headings, lists, tables, bold/italic, links
        
        Parameters:
        -----------
        input_path : str
            Path to input document
        output_path : str
            Path where PDF should be saved
        ext : str
            File extension (docx, doc, or rtf)
            
        Returns:
        --------
        bool : True if conversion succeeded, False otherwise
        """
        try:
            print(f"Converting document: {os.path.basename(input_path)} (via Markdown pipeline)")
            
            # Step 1: Convert to Markdown
            markdown_text = None
            
            if ext == 'docx':
                markdown_text = self._docx_to_markdown(input_path)
            elif ext == 'doc':
                markdown_text = self._doc_to_markdown(input_path)
            elif ext == 'rtf':
                markdown_text = self._rtf_to_markdown(input_path)
            
            if not markdown_text:
                print(f"Failed to extract content from {ext.upper()} file")
                return False
            
            # Step 2: Convert Markdown to PDF
            return self._markdown_to_pdf(markdown_text, output_path)
            
        except Exception as e:
            print(f"Error converting document to PDF: {str(e)}")
            return False
    
    def _docx_to_markdown(self, docx_path: str) -> Optional[str]:
        """Convert DOCX to Markdown using mammoth."""
        try:
            import mammoth
            
            with open(docx_path, 'rb') as docx_file:
                result = mammoth.convert_to_markdown(docx_file)
                markdown_text = result.value
                
                if result.messages:
                    for msg in result.messages:
                        print(f"  {msg}")
                
                return markdown_text
                
        except Exception as e:
            print(f"Error converting DOCX to Markdown: {str(e)}")
            return None
    
    def _doc_to_markdown(self, doc_path: str) -> Optional[str]:
        """
        Convert DOC to Markdown (best effort using mammoth).
        
        Note: mammoth primarily supports DOCX. For DOC files, it attempts
        conversion but may fall back to basic text extraction.
        """
        try:
            import mammoth
            
            with open(doc_path, 'rb') as doc_file:
                result = mammoth.convert_to_markdown(doc_file)
                markdown_text = result.value
                
                if markdown_text and len(markdown_text.strip()) > 0:
                    return markdown_text
                else:
                    # Fallback: basic text extraction
                    print("  Mammoth couldn't extract, using basic text extraction")
                    return self._extract_text_from_doc(doc_path)
                    
        except Exception as e:
            print(f"Error converting DOC: {str(e)}")
            # Fallback to basic text extraction
            return self._extract_text_from_doc(doc_path)
    
    def _extract_text_from_doc(self, doc_path: str) -> Optional[str]:
        """Basic text extraction from DOC files (fallback)."""
        try:
            # This is a very basic approach
            # In reality, DOC is a complex binary format
            with open(doc_path, 'rb') as f:
                content = f.read()
                # Try to extract printable ASCII text
                text = ''.join(chr(b) if 32 <= b < 127 else ' ' for b in content)
                # Clean up multiple spaces
                text = re.sub(r' +', ' ', text)
                # Try to detect paragraphs
                text = re.sub(r'([.!?])\s+', r'\1\n\n', text)
                return text.strip()
        except Exception as e:
            print(f"Error extracting text from DOC: {str(e)}")
            return None
    
    def _rtf_to_markdown(self, rtf_path: str) -> Optional[str]:
        """Convert RTF to Markdown via text extraction."""
        try:
            from striprtf.striprtf import rtf_to_text
            
            with open(rtf_path, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()
            
            # Strip RTF formatting
            text = rtf_to_text(rtf_content)
            
            # Convert to basic Markdown
            # Auto-detect potential headings (lines with few words in CAPS)
            lines = text.split('\n')
            markdown_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    markdown_lines.append('')
                    continue
                
                # Heuristic: short lines in UPPERCASE might be headings
                words = line.split()
                if len(words) <= 10 and line.isupper() and len(line) > 5:
                    markdown_lines.append(f"## {line.title()}")
                # Detect bullet points
                elif line.startswith(('-', '*', '•')):
                    markdown_lines.append(f"* {line[1:].strip()}")
                else:
                    markdown_lines.append(line)
            
            return '\n'.join(markdown_lines)
            
        except Exception as e:
            print(f"Error converting RTF to Markdown: {str(e)}")
            return None
    
    def _markdown_to_pdf(self, markdown_text: str, output_path: str) -> bool:
        """Convert Markdown to PDF using reportlab."""
        try:
            import markdown
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
            from reportlab.lib import colors
            from html.parser import HTMLParser
            
            # Convert Markdown to HTML
            html_content = markdown.markdown(
                markdown_text,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
            
            # Create PDF
            pdf = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Styles
            styles = getSampleStyleSheet()
            
            # Custom styles for Markdown elements
            styles.add(ParagraphStyle(
                name='MarkdownHeading1',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#2C3E50'),
                spaceAfter=12,
                spaceBefore=12
            ))
            
            styles.add(ParagraphStyle(
                name='MarkdownHeading2',
                parent=styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#34495E'),
                spaceAfter=10,
                spaceBefore=10
            ))
            
            styles.add(ParagraphStyle(
                name='MarkdownHeading3',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=colors.HexColor('#7F8C8D'),
                spaceAfter=8,
                spaceBefore=8
            ))
            
            # Parse HTML and build PDF story
            story = []
            parser = MarkdownHTMLParser(story, styles)
            parser.feed(html_content)
            
            # Build PDF
            if story:
                pdf.build(story)
            else:
                # Empty document
                story = [Paragraph("(Empty document)", styles['Normal'])]
                pdf.build(story)
            
            return os.path.exists(output_path)
            
        except Exception as e:
            print(f"Error converting Markdown to PDF: {str(e)}")
            return False


class MarkdownHTMLParser(HTMLParser):
    """Parse HTML from Markdown conversion and build ReportLab story."""
    
    def __init__(self, story, styles):
        super().__init__()
        self.story = story
        self.styles = styles
        self.current_text = []
        self.current_tag = None
        self.list_items = []
        self.in_list = False
        self.table_data = []
        self.in_table = False
        self.current_row = []
        
        from reportlab.lib.units import inch
        self.inch = inch
    
    def handle_starttag(self, tag, attrs):
        if tag in ['h1', 'h2', 'h3']:
            self.current_tag = tag
        elif tag in ['ul', 'ol']:
            self.in_list = True
            self.list_items = []
        elif tag == 'li':
            self.current_tag = 'li'
        elif tag == 'table':
            self.in_table = True
            self.table_data = []
        elif tag == 'tr':
            self.current_row = []
        elif tag in ['td', 'th']:
            self.current_tag = tag
        elif tag in ['strong', 'b']:
            self.current_text.append('<b>')
        elif tag in ['em', 'i']:
            self.current_text.append('<i>')
        elif tag == 'a':
            for attr_name, attr_value in attrs:
                if attr_name == 'href':
                    self.current_text.append(f'<a href="{attr_value}">')
        elif tag == 'p':
            self.current_tag = 'p'
    
    def handle_endtag(self, tag):
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        
        if tag in ['h1', 'h2', 'h3']:
            text = ''.join(self.current_text).strip()
            if text:
                style_name = f'MarkdownHeading{tag[1]}'
                self.story.append(Paragraph(text, self.styles[style_name]))
                self.story.append(Spacer(1, 0.1 * self.inch))
            self.current_text = []
            self.current_tag = None
        elif tag in ['ul', 'ol']:
            # Add list items
            for item in self.list_items:
                bullet_text = f"• {item}" if tag == 'ul' else f"{self.list_items.index(item) + 1}. {item}"
                self.story.append(Paragraph(bullet_text, self.styles['Normal']))
            self.story.append(Spacer(1, 0.1 * self.inch))
            self.in_list = False
            self.list_items = []
        elif tag == 'li':
            text = ''.join(self.current_text).strip()
            if text:
                self.list_items.append(text)
            self.current_text = []
            self.current_tag = None
        elif tag == 'table':
            # Create table
            if self.table_data:
                table = Table(self.table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                self.story.append(table)
                self.story.append(Spacer(1, 0.2 * self.inch))
            self.in_table = False
            self.table_data = []
        elif tag == 'tr':
            if self.current_row:
                self.table_data.append(self.current_row)
            self.current_row = []
        elif tag in ['td', 'th']:
            text = ''.join(self.current_text).strip()
            self.current_row.append(text)
            self.current_text = []
            self.current_tag = None
        elif tag in ['strong', 'b']:
            self.current_text.append('</b>')
        elif tag in ['em', 'i']:
            self.current_text.append('</i>')
        elif tag == 'a':
            self.current_text.append('</a>')
        elif tag == 'p':
            text = ''.join(self.current_text).strip()
            if text:
                self.story.append(Paragraph(text, self.styles['Normal']))
                self.story.append(Spacer(1, 0.1 * self.inch))
            self.current_text = []
            self.current_tag = None
    
    def handle_data(self, data):
        if self.current_tag or self.in_list or self.in_table:
            self.current_text.append(data)


class PDFConverter(PDFConverter):
    """Extended PDFConverter with improved spreadsheet handling."""
    
    def _convert_spreadsheet_to_pdf(self, input_path: str, output_path: str) -> bool:
        """
        Convert spreadsheet (XLS/XLSX) to PDF with intelligent formatting.
        
        FINAL VERSION: All cells wrapped in Paragraphs, aggressive content limiting,
        proper error handling, no text escaping cells.
        
        Parameters:
        -----------
        input_path : str
            Path to input spreadsheet
        output_path : str
            Path where PDF should be saved
            
        Returns:
        --------
        bool : True if conversion succeeded
        """
        try:
            print(f"Converting spreadsheet: {os.path.basename(input_path)}")
            
            # Read spreadsheet data
            sheets_data = self._read_spreadsheet(input_path)
            
            if not sheets_data:
                print("No data found in spreadsheet")
                return False
            
            print(f"  Found {len(sheets_data)} sheet(s) to process")
            
            # Create PDF with landscape orientation
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            
            pdf = SimpleDocTemplate(
                output_path,
                pagesize=landscape(letter),
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )
            styles = getSampleStyleSheet()
            story = []
            
            # Calculate available width for tables
            page_width = landscape(letter)[0] - 1*inch
            
            # Track success/failure
            successful_sheets = 0
            failed_sheets = 0
            
            # Process each sheet
            for sheet_idx, (sheet_name, sheet_data) in enumerate(sheets_data):
                try:
                    if not sheet_data:
                        print(f"  Sheet '{sheet_name}': No data, skipping")
                        continue
                    
                    print(f"  Processing sheet {sheet_idx + 1}/{len(sheets_data)}: '{sheet_name}'")
                    
                    # Add sheet name as heading
                    story.append(Paragraph(f"<b>{sheet_name}</b>", styles['Heading1']))
                    story.append(Spacer(1, 0.2 * inch))
                    
                    # Filter out completely empty rows
                    non_empty_data = [
                        row for row in sheet_data 
                        if any(str(cell).strip() for cell in row)
                    ]
                    
                    if non_empty_data:
                        # Limit rows to prevent huge files
                        max_rows = 150
                        if len(non_empty_data) > max_rows:
                            non_empty_data = non_empty_data[:max_rows]
                            print(f"  Note: Limited to first {max_rows} rows")
                        
                        # Process the table with robust handling
                        success = self._add_table_robust(
                            story,
                            non_empty_data,
                            sheet_name,
                            page_width,
                            styles
                        )
                        
                        if success:
                            successful_sheets += 1
                            print(f"  Sheet '{sheet_name}': Successfully processed")
                        else:
                            failed_sheets += 1
                            print(f"  Sheet '{sheet_name}': Failed to process table")
                            story.append(Paragraph(
                                f"<i>(Sheet '{sheet_name}' could not be fully rendered)</i>",
                                styles['Normal']
                            ))
                    else:
                        print(f"  Sheet '{sheet_name}': All rows empty after filtering")
                        story.append(Paragraph(
                            f"<i>(Sheet '{sheet_name}' contains no data)</i>",
                            styles['Normal']
                        ))
                    
                    # Add page break between sheets (if not last sheet)
                    if sheet_idx < len(sheets_data) - 1:
                        story.append(PageBreak())
                        
                except Exception as sheet_error:
                    failed_sheets += 1
                    print(f"  Error processing sheet '{sheet_name}': {str(sheet_error)}")
                    import traceback
                    traceback.print_exc()
                    story.append(Paragraph(
                        f"<i>(Error processing sheet '{sheet_name}')</i>",
                        styles['Normal']
                    ))
                    if sheet_idx < len(sheets_data) - 1:
                        story.append(PageBreak())
            
            # Build PDF
            print(f"  Building PDF: {successful_sheets} sheets successful, {failed_sheets} sheets failed")
            if story:
                pdf.build(story)
            else:
                pdf.build([Paragraph("(Empty spreadsheet)", styles['Normal'])])
            
            file_exists = os.path.exists(output_path)
            if file_exists and successful_sheets > 0:
                print(f"  Successfully created PDF with {successful_sheets} sheet(s)")
                return True
            else:
                return False
            
        except Exception as e:
            print(f"Error converting spreadsheet: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _read_spreadsheet(self, file_path: str) -> List[Tuple[str, List[List[str]]]]:
        """Read spreadsheet and return data from all sheets."""
        try:
            ext = os.path.splitext(file_path.lower())[1].lstrip('.')
            
            if ext == 'xlsx':
                return self._read_xlsx(file_path)
            elif ext == 'xls':
                return self._read_xls(file_path)
            else:
                return []
                
        except Exception as e:
            print(f"Error reading spreadsheet: {str(e)}")
            return []
    
    def _read_xlsx(self, file_path: str) -> List[Tuple[str, List[List[str]]]]:
        """Read XLSX file using openpyxl."""
        try:
            import openpyxl
            
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheets_data = []
            
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                sheet_data = []
                
                for row_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                    if row_idx >= 500:  # Safety limit
                        break
                    row_data = [str(cell) if cell is not None else '' for cell in row]
                    sheet_data.append(row_data)
                
                if any(any(cell for cell in row) for row in sheet_data):
                    sheets_data.append((sheet_name, sheet_data))
            
            return sheets_data
            
        except Exception as e:
            print(f"Error reading XLSX: {str(e)}")
            return []
    
    def _read_xls(self, file_path: str) -> List[Tuple[str, List[List[str]]]]:
        """Read XLS file using xlrd."""
        try:
            import xlrd
            
            workbook = xlrd.open_workbook(file_path)
            sheets_data = []
            
            for sheet in workbook.sheets():
                sheet_data = []
                
                max_rows = min(sheet.nrows, 500)
                for row_idx in range(max_rows):
                    row = sheet.row_values(row_idx)
                    row_data = [str(cell) if cell is not None else '' for cell in row]
                    sheet_data.append(row_data)
                
                if any(any(cell for cell in row) for row in sheet_data):
                    sheets_data.append((sheet.name, sheet_data))
            
            return sheets_data
            
        except Exception as e:
            print(f"Error reading XLS: {str(e)}")
            return []
    
    def _add_table_robust(self, story, data, sheet_name, page_width, styles):
        """
        ROBUST: Add table with ALL cells as Paragraphs, aggressive limiting, proper error handling.
        """
        try:
            from reportlab.platypus import Paragraph, Spacer
            from reportlab.lib.units import inch
            
            if not data or len(data) == 0:
                return True
            
            # Normalize data
            max_cols = max(len(row) for row in data)
            normalized_data = []
            for row in data:
                if len(row) < max_cols:
                    row = list(row) + [''] * (max_cols - len(row))
                normalized_data.append(row[:max_cols])
            data = normalized_data
            
            num_cols = len(data[0])
            print(f"  Table: {len(data)} rows x {num_cols} columns")
            
            # AGGRESSIVE content truncation to prevent overflow
            max_cell_length = 200  # Reduced from 300
            truncated_data = []
            for row in data:
                truncated_row = []
                for cell in row:
                    cell_str = str(cell) if cell is not None else ''
                    if len(cell_str) > max_cell_length:
                        truncated_row.append(cell_str[:max_cell_length] + '...')
                    else:
                        truncated_row.append(cell_str)
                truncated_data.append(truncated_row)
            data = truncated_data
            
            # Calculate realistic column widths
            col_widths = self._calculate_realistic_widths(data, num_cols)
            total_width = sum(col_widths)
            
            print(f"  Required width: {total_width:.0f} pts vs page width: {page_width:.0f} pts")
            
            # Decide: fit or split
            if total_width <= page_width * 0.80:
                # Fits comfortably
                print(f"  Strategy: Single table")
                return self._add_single_table_all_paragraphs(story, data, col_widths, styles)
            else:
                # Split into parts
                print(f"  Strategy: Split table (ratio: {total_width/page_width:.1f}x)")
                return self._add_split_table_all_paragraphs(story, data, col_widths, sheet_name, page_width, styles)
                
        except Exception as e:
            print(f"Error adding table: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _calculate_realistic_widths(self, data, num_cols):
        """Calculate realistic column widths without scaling down."""
        try:
            col_max_lengths = []
            for col_idx in range(num_cols):
                max_len = 0
                for row in data[:30]:
                    if col_idx < len(row):
                        cell_value = row[col_idx]
                        if cell_value is not None:
                            max_len = max(max_len, len(str(cell_value)))
                col_max_lengths.append(max_len)
            
            min_width = 50  # Minimum 50pt (IMPROVED FOR READABILITY)
            char_width = 6
            
            col_widths = []
            for max_len in col_max_lengths:
                if max_len == 0:
                    width = min_width
                else:
                    width = max(min_width, max_len * char_width)
                    width = min(width, 250)  # Cap at 250pt
                col_widths.append(width)
            
            # DON'T normalize - let splitting handle wide tables
            total_width = sum(col_widths)
            # REMOVED AGGRESSIVE SCALING: Let _add_table_robust decide whether to split
            # This prevents millimeter-wide unreadable columns!
            
            return col_widths
            
        except Exception as e:
            print(f"Error calculating widths: {str(e)}")
            return [80] * num_cols
    
    def _add_single_table_all_paragraphs(self, story, data, col_widths, styles):
        """
        Add single table with ALL cells as Paragraphs for proper text wrapping.
        """
        try:
            from reportlab.platypus import Table, TableStyle, Paragraph
            from reportlab.lib import colors
            from reportlab.lib.styles import ParagraphStyle
            
            num_cols = len(data[0])
            
            # Font size based on columns
            if num_cols <= 8:
                font_size = 7
            elif num_cols <= 12:
                font_size = 6
            else:
                font_size = 6
            
            # Cell style - VERY IMPORTANT: proper wrapping
            cell_style = ParagraphStyle(
                'CellStyle',
                parent=styles['Normal'],
                fontSize=font_size,
                leading=font_size + 2,
                wordWrap='CJK',
                alignment=0,
                leftIndent=0,
                rightIndent=0
            )
            
            # Header style - smaller, multi-line capable
            header_style = ParagraphStyle(
                'HeaderStyle',
                parent=styles['Normal'],
                fontSize=font_size,  # Same as cell, not larger
                leading=font_size + 2,
                wordWrap='CJK',
                alignment=0,
                textColor=colors.whitesmoke,
                leftIndent=0,
                rightIndent=0
            )
            
            # Wrap ALL cells in Paragraphs - this is critical
            wrapped_data = []
            for row_idx, row in enumerate(data):
                wrapped_row = []
                for cell in row:
                    cell_str = str(cell) if cell is not None else ''
                    style = header_style if row_idx == 0 else cell_style
                    
                    # ALL cells become Paragraphs for proper wrapping
                    wrapped_row.append(Paragraph(cell_str, style))
                
                wrapped_data.append(wrapped_row)
            
            # Create table
            table = Table(
                wrapped_data,
                colWidths=col_widths,
                repeatRows=1
            )
            
            # Apply styling
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), font_size),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), font_size),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ]))
            
            # Try to add, with fallback for "too large" errors
            try:
                story.append(table)
                return True
            except Exception as table_error:
                error_msg = str(table_error).lower()
                if 'too large' in error_msg or 'flowable' in error_msg:
                    print(f"  Table too large error, reducing content further...")
                    
                    # More aggressive truncation
                    max_len = 100
                    reduced_data = []
                    for row in data:
                        reduced_row = []
                        for cell in row:
                            cell_str = str(cell) if cell is not None else ''
                            if len(cell_str) > max_len:
                                reduced_row.append(cell_str[:max_len] + '...')
                            else:
                                reduced_row.append(cell_str)
                        reduced_data.append(reduced_row)
                    
                    # Try again with reduced data
                    return self._add_single_table_all_paragraphs(story, reduced_data, col_widths, styles)
                else:
                    raise
            
        except Exception as e:
            print(f"Error creating table: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_split_table_all_paragraphs(self, story, data, col_widths, sheet_name, page_width, styles):
        """
        Split table with ALL cells as Paragraphs, including row index column.
        """
        try:
            from reportlab.platypus import Paragraph, Spacer, PageBreak
            from reportlab.lib.units import inch
            
            num_cols = len(data[0])
            
            # Row index column
            row_index_width = 50
            
            # Target comfortable width per part
            target_width = page_width * 0.80  # SPLIT EARLIER!
            
            # Determine column groupings
            cols_per_part = []
            current_part_cols = []
            current_part_width = row_index_width
            
            for col_idx, width in enumerate(col_widths):
                if current_part_width + width <= target_width:
                    current_part_cols.append(col_idx)
                    current_part_width += width
                else:
                    if current_part_cols:
                        cols_per_part.append(current_part_cols)
                    current_part_cols = [col_idx]
                    current_part_width = row_index_width + width
            
            if current_part_cols:
                cols_per_part.append(current_part_cols)
            
            num_parts = len(cols_per_part)
            print(f"  Splitting into {num_parts} parts")
            
            # Font size
            max_cols_in_part = max(len(part) for part in cols_per_part) + 1
            if max_cols_in_part <= 10:
                font_size = 7
            else:
                font_size = 6
            
            # Create each part
            for part_idx, col_indices in enumerate(cols_per_part):
                # Prepare data
                part_data = []
                for row_idx, row in enumerate(data):
                    if row_idx == 0:
                        row_label = 'Row'
                    else:
                        row_label = str(row_idx)
                    
                    part_row = [row_label] + [row[i] for i in col_indices]
                    part_data.append(part_row)
                
                # Column widths
                part_widths = [row_index_width] + [col_widths[i] for i in col_indices]
                
                # Part header
                part_title = f"Part {part_idx + 1} of {num_parts} - Columns {col_indices[0] + 1} to {col_indices[-1] + 1}"
                story.append(Paragraph(f"<i>{part_title}</i>", styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))
                
                # Add the part
                success = self._add_single_table_all_paragraphs(
                    story,
                    part_data,
                    part_widths,
                    styles
                )
                
                if not success:
                    print(f"  Warning: Part {part_idx + 1} failed")
                    story.append(Paragraph(
                        f"<i>(Part {part_idx + 1} could not be rendered)</i>",
                        styles['Normal']
                    ))
                
                # Page break between parts
                if part_idx < num_parts - 1:
                    story.append(PageBreak())
            
            return True
            
        except Exception as e:
            print(f"Error splitting table: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _convert_image_to_pdf(self, input_path: str, output_path: str) -> bool:
        """Convert image files (JPG, PNG, TIF, SVG) to PDF."""
        try:
            from PIL import Image
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            
            print(f"Converting image: {os.path.basename(input_path)}")
            
            # Open the image
            img = Image.open(input_path)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                img.save(tmp_file.name, 'JPEG', quality=95)
                temp_img_path = tmp_file.name
            
            # Get image dimensions
            img_width, img_height = img.size
            
            # Calculate page size
            max_width, max_height = A4
            scale = min(max_width / img_width, max_height / img_height, 1.0)
            page_width = img_width * scale
            page_height = img_height * scale
            
            # Create PDF
            c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
            c.drawImage(temp_img_path, 0, 0, width=page_width, height=page_height)
            c.save()
            
            # Clean up
            try:
                os.remove(temp_img_path)
            except:
                pass
            
            return os.path.exists(output_path)
            
        except Exception as e:
            print(f"Error converting image to PDF: {str(e)}")
            return False
    
    def batch_convert(
        self,
        file_paths: List[str],
        verbose: bool = True
    ) -> Dict[str, Any]:
        """Convert multiple files to PDF."""
        results = {
            'total': len(file_paths),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'results': []
        }
        
        for i, file_path in enumerate(file_paths, 1):
            if verbose:
                print(f"\n{'='*30}")
                print(f"Processing {i}/{len(file_paths)}: {os.path.basename(file_path)}")
                print(f"{'='*30}")
            
            success, output_path, message = self.convert_to_pdf(file_path)
            
            if success:
                results['successful'] += 1
            elif 'already a PDF' in message or 'Unsupported' in message or 'Malformed' in message:
                results['skipped'] += 1
            else:
                results['failed'] += 1
            
            results['results'].append((file_path, success, output_path, message))
        
        if verbose:
            print(f"\n{'='*30}")
            print(f"CONVERSION SUMMARY")
            print(f"{'='*30}")
            print(f"Total files: {results['total']}")
            print(f"Successful: {results['successful']}")
            print(f"Failed: {results['failed']}")
            print(f"Skipped: {results['skipped']}")
            print(f"{'='*30}\n")
        
        return results
    
    # Future Methods (Skeleton Implementation)
    def convert_from_db(
        self,
        file_id: str,
        azure_sql_conn: AzureSql,
        adls_conn: ADLSConnect
    ) -> Tuple[bool, Optional[str], str]:
        """Convert a file to PDF using file_id from Azure SQL database."""
        raise NotImplementedError(
            "convert_from_db() requires AzureSql and ADLSConnect classes to be implemented"
        )
    
    def save_to_adls(
        self,
        local_pdf_path: str,
        adls_conn: ADLSConnect,
        adls_target_path: str
    ) -> Tuple[bool, Optional[str], str]:
        """Save converted PDF to Azure Data Lake Storage."""
        raise NotImplementedError(
            "save_to_adls() requires ADLSConnect class to be implemented"
        )
    
    def update_db_with_pdf_path(
        self,
        file_id: str,
        pdf_path: str,
        azure_sql_conn: AzureSql
    ) -> Tuple[bool, str]:
        """Update database with path to converted PDF."""
        raise NotImplementedError(
            "update_db_with_pdf_path() requires AzureSql class to be implemented"
        )
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """Get statistics about files in output directory."""
        pdf_files = list(Path(self.output_dir).glob('*.pdf'))
        
        return {
            'output_directory': self.output_dir,
            'total_pdfs': len(pdf_files),
            'pdf_files': [f.name for f in pdf_files],
            'total_size_mb': sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
        }
