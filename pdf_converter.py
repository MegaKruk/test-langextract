"""
PDFConverter Class for converting various document formats to PDF.

This class handles conversion of documents (DOC, DOCX, RTF), spreadsheets (XLS, XLSX),
and images (JPG, JPEG, PNG, TIF, SVG) to PDF format.

Current Implementation: Works with files from volumes
Future: Will integrate with AzureSql and ADLSConnect
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFConverter:
    """
    A class to convert various file formats to PDF.
    
    Supported formats:
    - Documents: doc, docx, rtf
    - Spreadsheets: xls, xlsx
    - Images: jpg, jpeg, png, tif, svg
    
    Files that are already PDF or have unsupported extensions are skipped.
    """
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        'doc', 'docx', 'rtf',  # Documents
        'xls', 'xlsx',          # Spreadsheets
        'jpg', 'jpeg', 'png', 'tif', 'svg'  # Images
    }
    
    DOCUMENT_EXTENSIONS = {'doc', 'docx', 'rtf'}
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
        logger.info(f"PDFConverter initialized with output directory: {self.output_dir}")
        
        # Check if LibreOffice is available for document conversion
        self._check_libreoffice()
        
    def _check_libreoffice(self) -> bool:
        """
        Check if LibreOffice is installed and available.
        
        Returns:
        --------
        bool : True if LibreOffice is available, False otherwise
        """
        try:
            result = subprocess.run(
                ['libreoffice', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"LibreOffice found: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("LibreOffice not found. Document/spreadsheet conversion may fail.")
        return False
    
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
            logger.info(f"Skipping {input_path}: {reason}")
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
            if ext in self.DOCUMENT_EXTENSIONS or ext in self.SPREADSHEET_EXTENSIONS:
                success = self._convert_office_to_pdf(input_path, output_path)
            elif ext in self.IMAGE_EXTENSIONS:
                success = self._convert_image_to_pdf(input_path, output_path)
            else:
                return False, None, f"Unsupported file type: {ext}"
            
            if success:
                logger.info(f"Successfully converted {input_path} to {output_path}")
                return True, output_path, "Conversion successful"
            else:
                return False, None, "Conversion failed"
                
        except Exception as e:
            logger.error(f"Error converting {input_path}: {str(e)}")
            return False, None, f"Error: {str(e)}"
    
    def _convert_office_to_pdf(self, input_path: str, output_path: str) -> bool:
        """
        Convert Microsoft Office documents (DOC, DOCX, RTF, XLS, XLSX) to PDF using LibreOffice.
        
        Parameters:
        -----------
        input_path : str
            Path to input document
        output_path : str
            Path where PDF should be saved
            
        Returns:
        --------
        bool : True if conversion succeeded, False otherwise
        """
        try:
            # LibreOffice command for conversion
            cmd = [
                'libreoffice',
                '--headless',  # Run without GUI
                '--convert-to', 'pdf',
                '--outdir', os.path.dirname(output_path),
                input_path
            ]
            
            logger.info(f"Running LibreOffice conversion: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                logger.error(f"LibreOffice conversion failed: {result.stderr}")
                return False
            
            # LibreOffice creates file with same base name as input
            temp_output = os.path.join(
                os.path.dirname(output_path),
                os.path.splitext(os.path.basename(input_path))[0] + '.pdf'
            )
            
            # Rename if needed
            if temp_output != output_path and os.path.exists(temp_output):
                os.rename(temp_output, output_path)
            
            return os.path.exists(output_path)
            
        except subprocess.TimeoutExpired:
            logger.error(f"LibreOffice conversion timed out for {input_path}")
            return False
        except Exception as e:
            logger.error(f"Error in LibreOffice conversion: {str(e)}")
            return False
    
    def _convert_image_to_pdf(self, input_path: str, output_path: str) -> bool:
        """
        Convert image files (JPG, PNG, TIF, SVG) to PDF.
        
        Parameters:
        -----------
        input_path : str
            Path to input image
        output_path : str
            Path where PDF should be saved
            
        Returns:
        --------
        bool : True if conversion succeeded, False otherwise
        """
        try:
            from PIL import Image
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            from reportlab.lib.pagesizes import letter, A4
            
            # Open the image
            img = Image.open(input_path)
            
            # Convert to RGB if necessary (for PNG with transparency, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to temporary file if we modified the image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                img.save(tmp_file.name, 'JPEG', quality=95)
                temp_img_path = tmp_file.name
            
            # Get image dimensions
            img_width, img_height = img.size
            
            # Calculate page size to fit image (with some margin)
            # Use A4 as max size for reasonable file sizes
            max_width, max_height = A4
            
            # Calculate scaling to fit within A4 while maintaining aspect ratio
            scale = min(max_width / img_width, max_height / img_height, 1.0)
            page_width = img_width * scale
            page_height = img_height * scale
            
            # Create PDF
            c = canvas.Canvas(output_path, pagesize=(page_width, page_height))
            
            # Draw image to fill the page
            c.drawImage(temp_img_path, 0, 0, width=page_width, height=page_height)
            
            c.save()
            
            # Clean up temporary file
            try:
                os.remove(temp_img_path)
            except:
                pass
            
            return os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"Error converting image to PDF: {str(e)}")
            return False
    
    def batch_convert(
        self,
        file_paths: List[str],
        verbose: bool = True
    ) -> dict:
        """
        Convert multiple files to PDF.
        
        Parameters:
        -----------
        file_paths : List[str]
            List of file paths to convert
        verbose : bool
            If True, print progress information
            
        Returns:
        --------
        dict : Summary of conversion results
            {
                'total': total files,
                'successful': number of successful conversions,
                'failed': number of failed conversions,
                'skipped': number of skipped files,
                'results': list of tuples (file_path, success, output_path, message)
            }
        """
        results = {
            'total': len(file_paths),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'results': []
        }
        
        for i, file_path in enumerate(file_paths, 1):
            if verbose:
                print(f"Processing {i}/{len(file_paths)}: {os.path.basename(file_path)}")
            
            success, output_path, message = self.convert_to_pdf(file_path)
            
            if success:
                results['successful'] += 1
            elif 'already a PDF' in message or 'Unsupported' in message or 'Malformed' in message:
                results['skipped'] += 1
            else:
                results['failed'] += 1
            
            results['results'].append((file_path, success, output_path, message))
        
        if verbose:
            print(f"\n=== Conversion Summary ===")
            print(f"Total files: {results['total']}")
            print(f"Successful: {results['successful']}")
            print(f"Failed: {results['failed']}")
            print(f"Skipped: {results['skipped']}")
        
        return results
    
    # ========== Future Methods (Skeleton Implementation) ==========
    
    def convert_from_db(
        self,
        file_id: str,
        azure_sql_conn: 'AzureSql',  # type: ignore
        adls_conn: 'ADLSConnect'      # type: ignore
    ) -> Tuple[bool, Optional[str], str]:
        """
        Convert a file to PDF using file_id from Azure SQL database.
        
        NOTE: This is a skeleton implementation. Requires:
        - AzureSql class to be implemented
        - ADLSConnect class to be implemented
        - Database schema with file_header table
        
        Parameters:
        -----------
        file_id : str
            ID of the file in the database
        azure_sql_conn : AzureSql
            Connection to Azure SQL database
        adls_conn : ADLSConnect
            Connection to Azure Data Lake Storage
            
        Returns:
        --------
        Tuple[bool, Optional[str], str] : (success, adls_path, message)
        """
        # TODO: Implement when AzureSql and ADLSConnect are ready
        # Workflow:
        # 1. Query file_header table for file metadata using file_id
        # 2. Download file from ADLS using path from database
        # 3. Convert to PDF using convert_to_pdf()
        # 4. Upload PDF to ADLS
        # 5. Update file_header table with pdf_version_path
        # 6. Return success status and ADLS path
        
        raise NotImplementedError(
            "convert_from_db() requires AzureSql and ADLSConnect classes to be implemented"
        )
    
    def save_to_adls(
        self,
        local_pdf_path: str,
        adls_conn: 'ADLSConnect',  # type: ignore
        adls_target_path: str
    ) -> Tuple[bool, Optional[str], str]:
        """
        Save converted PDF to Azure Data Lake Storage.
        
        NOTE: This is a skeleton implementation. Requires:
        - ADLSConnect class to be implemented
        
        Parameters:
        -----------
        local_pdf_path : str
            Path to the PDF file on local filesystem
        adls_conn : ADLSConnect
            Connection to Azure Data Lake Storage
        adls_target_path : str
            Target path in ADLS where file should be saved
            
        Returns:
        --------
        Tuple[bool, Optional[str], str] : (success, adls_path, message)
        """
        # TODO: Implement when ADLSConnect is ready
        # Workflow:
        # 1. Upload local PDF to ADLS at target path
        # 2. Verify upload succeeded
        # 3. Return ADLS path
        
        raise NotImplementedError(
            "save_to_adls() requires ADLSConnect class to be implemented"
        )
    
    def update_db_with_pdf_path(
        self,
        file_id: str,
        pdf_path: str,
        azure_sql_conn: 'AzureSql'  # type: ignore
    ) -> Tuple[bool, str]:
        """
        Update database with path to converted PDF.
        
        NOTE: This is a skeleton implementation. Requires:
        - AzureSql class to be implemented
        - Database schema with file_header table and pdf_version_path field
        
        Parameters:
        -----------
        file_id : str
            ID of the file in the database
        pdf_path : str
            Path to the PDF in ADLS
        azure_sql_conn : AzureSql
            Connection to Azure SQL database
            
        Returns:
        --------
        Tuple[bool, str] : (success, message)
        """
        # TODO: Implement when AzureSql is ready
        # Workflow:
        # 1. Update file_header table
        # 2. Set pdf_version_path = pdf_path WHERE file_id = file_id
        # 3. Verify update succeeded
        
        raise NotImplementedError(
            "update_db_with_pdf_path() requires AzureSql class to be implemented"
        )
    
    def get_conversion_stats(self) -> dict:
        """
        Get statistics about files in output directory.
        
        Returns:
        --------
        dict : Statistics about converted files
        """
        pdf_files = list(Path(self.output_dir).glob('*.pdf'))
        
        return {
            'output_directory': self.output_dir,
            'total_pdfs': len(pdf_files),
            'pdf_files': [f.name for f in pdf_files],
            'total_size_mb': sum(f.stat().st_size for f in pdf_files) / (1024 * 1024)
        }
