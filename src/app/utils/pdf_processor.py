"""
PDF Processing Utilities

Utilities for extracting text content from PDF files for policy analysis.
"""

import logging
from typing import Union
import io

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("PyPDF2 not available. PDF processing will be limited.")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. Using fallback PDF processing.")


def extract_text_from_pdf(pdf_content: Union[bytes, io.BytesIO]) -> str:
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_content: PDF file content as bytes or BytesIO object
        
    Returns:
        Extracted text content as string
        
    Raises:
        Exception: If PDF processing fails
    """
    
    if isinstance(pdf_content, bytes):
        pdf_content = io.BytesIO(pdf_content)
    
    # Try PyMuPDF first (better text extraction)
    if PYMUPDF_AVAILABLE:
        try:
            return _extract_with_pymupdf(pdf_content)
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {str(e)}, trying PyPDF2")
    
    # Fallback to PyPDF2
    if PDF_AVAILABLE:
        try:
            return _extract_with_pypdf2(pdf_content)
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    raise Exception("No PDF processing libraries available. Please install PyPDF2 or PyMuPDF.")


def _extract_with_pymupdf(pdf_content: io.BytesIO) -> str:
    """Extract text using PyMuPDF (fitz)."""
    
    pdf_content.seek(0)
    pdf_bytes = pdf_content.read()
    
    # Open PDF document
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    text_content = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        if text.strip():
            text_content.append(f"--- Page {page_num + 1} ---")
            text_content.append(text.strip())
    
    doc.close()
    
    full_text = "\n\n".join(text_content)
    
    if not full_text.strip():
        raise Exception("No text content found in PDF")
    
    logger.info(f"Extracted {len(full_text)} characters from PDF using PyMuPDF")
    return full_text


def _extract_with_pypdf2(pdf_content: io.BytesIO) -> str:
    """Extract text using PyPDF2."""
    
    pdf_content.seek(0)
    
    # Create PDF reader
    pdf_reader = PyPDF2.PdfReader(pdf_content)
    
    text_content = []
    
    for page_num, page in enumerate(pdf_reader.pages):
        try:
            text = page.extract_text()
            
            if text.strip():
                text_content.append(f"--- Page {page_num + 1} ---")
                text_content.append(text.strip())
        except Exception as e:
            logger.warning(f"Failed to extract text from page {page_num + 1}: {str(e)}")
            continue
    
    full_text = "\n\n".join(text_content)
    
    if not full_text.strip():
        raise Exception("No text content found in PDF")
    
    logger.info(f"Extracted {len(full_text)} characters from PDF using PyPDF2")
    return full_text


def validate_pdf_content(pdf_content: Union[bytes, io.BytesIO]) -> bool:
    """
    Validate that the content is a valid PDF file.
    
    Args:
        pdf_content: PDF file content
        
    Returns:
        True if valid PDF, False otherwise
    """
    try:
        if isinstance(pdf_content, bytes):
            pdf_content = io.BytesIO(pdf_content)
        
        pdf_content.seek(0)
        header = pdf_content.read(8)
        pdf_content.seek(0)
        
        # Check PDF header
        return header.startswith(b'%PDF-')
        
    except Exception:
        return False


def get_pdf_info(pdf_content: Union[bytes, io.BytesIO]) -> dict:
    """
    Get basic information about a PDF file.
    
    Args:
        pdf_content: PDF file content
        
    Returns:
        Dictionary with PDF information
    """
    info = {
        "is_valid": False,
        "page_count": 0,
        "text_length": 0,
        "extraction_method": None,
        "error": None
    }
    
    try:
        if not validate_pdf_content(pdf_content):
            info["error"] = "Invalid PDF format"
            return info
        
        info["is_valid"] = True
        
        if isinstance(pdf_content, bytes):
            pdf_content = io.BytesIO(pdf_content)
        
        # Try to get page count
        if PYMUPDF_AVAILABLE:
            try:
                pdf_content.seek(0)
                pdf_bytes = pdf_content.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                info["page_count"] = len(doc)
                doc.close()
                info["extraction_method"] = "PyMuPDF"
            except Exception as e:
                logger.warning(f"PyMuPDF info extraction failed: {str(e)}")
        
        if info["page_count"] == 0 and PDF_AVAILABLE:
            try:
                pdf_content.seek(0)
                pdf_reader = PyPDF2.PdfReader(pdf_content)
                info["page_count"] = len(pdf_reader.pages)
                info["extraction_method"] = "PyPDF2"
            except Exception as e:
                logger.warning(f"PyPDF2 info extraction failed: {str(e)}")
        
        # Try to extract text to get length
        try:
            text = extract_text_from_pdf(pdf_content)
            info["text_length"] = len(text)
        except Exception as e:
            info["error"] = f"Text extraction failed: {str(e)}"
        
    except Exception as e:
        info["error"] = str(e)
    
    return info
