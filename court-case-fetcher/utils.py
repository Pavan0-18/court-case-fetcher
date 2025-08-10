"""
Utility functions for Court Case Fetcher
Common helper functions used throughout the application
"""

import os
import hashlib
import re
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger(__name__)

def validate_case_number(case_number: str) -> bool:
    """
    Validate case number format
    
    Args:
        case_number: The case number to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not case_number or not isinstance(case_number, str):
        return False
    
    # Remove whitespace
    case_number = case_number.strip()
    
    # Basic validation - should contain alphanumeric characters and common separators
    if len(case_number) < 3 or len(case_number) > 50:
        return False
    
    # Should contain at least one letter and one number
    if not re.search(r'[A-Za-z]', case_number) or not re.search(r'\d', case_number):
        return False
    
    return True

def validate_filing_year(year: str) -> bool:
    """
    Validate filing year
    
    Args:
        year: The year to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        year_int = int(year)
        current_year = datetime.now().year
        
        # Year should be between 1900 and next year
        if year_int < 1900 or year_int > current_year + 1:
            return False
        
        return True
    except (ValueError, TypeError):
        return False

def validate_case_type(case_type: str) -> bool:
    """
    Validate case type format
    
    Args:
        case_type: The case type to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not case_type or not isinstance(case_type, str):
        return False
    
    case_type = case_type.strip()
    
    # Common case type patterns
    valid_patterns = [
        r'^[A-Z]{1,4}\([A-Z]\)$',  # WP(C), CRL(A), etc.
        r'^[A-Z]{1,4}$',           # WP, CRL, etc.
        r'^[A-Z]{1,4}\d+$',        # WP123, CRL456, etc.
    ]
    
    for pattern in valid_patterns:
        if re.match(pattern, case_type):
            return True
    
    return False

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    if not filename:
        return ""
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def generate_pdf_filename(case_type: str, case_number: str, filing_year: str, url: str) -> str:
    """
    Generate a unique filename for PDF downloads
    
    Args:
        case_type: The case type
        case_number: The case number
        filing_year: The filing year
        url: The PDF URL
        
    Returns:
        str: Generated filename
    """
    # Create base filename
    base_name = f"{case_type}_{case_number}_{filing_year}"
    
    # Add URL hash for uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    
    # Combine and sanitize
    filename = f"{base_name}_{url_hash}.pdf"
    return sanitize_filename(filename)

def is_valid_url(url: str) -> bool:
    """
    Check if URL is valid
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def is_safe_url(url: str, allowed_domains: list = None) -> bool:
    """
    Check if URL is safe to access
    
    Args:
        url: The URL to check
        allowed_domains: List of allowed domains
        
    Returns:
        bool: True if safe, False otherwise
    """
    if not is_valid_url(url):
        return False
    
    if allowed_domains is None:
        allowed_domains = ['delhihighcourt.nic.in']
    
    parsed = urlparse(url)
    return parsed.netloc in allowed_domains

def download_file_safe(url: str, filepath: str, timeout: int = 30, max_size: int = None) -> bool:
    """
    Safely download a file with size and security checks
    
    Args:
        url: The URL to download from
        filepath: Local filepath to save to
        timeout: Request timeout in seconds
        max_size: Maximum file size in bytes
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if URL is safe
        if not is_safe_url(url):
            logger.warning(f"Unsafe URL attempted: {url}")
            return False
        
        # Make request with timeout
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('application/pdf'):
            logger.warning(f"Non-PDF content type: {content_type}")
            return False
        
        # Check file size
        content_length = response.headers.get('content-length')
        if content_length and max_size:
            if int(content_length) > max_size:
                logger.warning(f"File too large: {content_length} bytes")
                return False
        
        # Download file
        downloaded_size = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Check size during download
                    if max_size and downloaded_size > max_size:
                        logger.warning(f"File size exceeded during download: {downloaded_size} bytes")
                        f.close()
                        os.unlink(filepath)
                        return False
        
        logger.info(f"File downloaded successfully: {filepath} ({downloaded_size} bytes)")
        return True
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading {url}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error downloading {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")
        return False

def extract_text_from_pdf_safe(filepath: str) -> str:
    """
    Safely extract text from PDF file
    
    Args:
        filepath: Path to the PDF file
        
    Returns:
        str: Extracted text or empty string if failed
    """
    try:
        if not os.path.exists(filepath):
            logger.warning(f"PDF file not found: {filepath}")
            return ""
        
        # Check file size
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            logger.warning(f"PDF file is empty: {filepath}")
            return ""
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            logger.warning(f"PDF file too large: {file_size} bytes")
            return ""
        
        # Import pypdf here to avoid import errors if not installed
        try:
            import pypdf
        except ImportError:
            logger.error("pypdf not installed, cannot extract text")
            return ""
        
        with open(filepath, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            
            # Check number of pages
            if len(pdf_reader.pages) > 1000:  # Reasonable page limit
                logger.warning(f"PDF has too many pages: {len(pdf_reader.pages)}")
                return ""
            
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Limit text length per page
                    if len(text) > 1000000:  # 1MB text limit
                        logger.warning("Text extraction stopped due to size limit")
                        break
                        
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {e}")
                    continue
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting PDF text from {filepath}: {e}")
        return ""

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    return text.strip()


