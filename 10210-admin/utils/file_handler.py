"""
File processing utilities for CSV/Excel handling
Supports file validation, column mapping, and data extraction
"""

import os
import logging
import pandas as pd
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
# import magic  # For file type detection - commented out to avoid issues
from datetime import datetime

logger = logging.getLogger(__name__)

class FileHandler:
    """Main file handler for CSV/Excel processing"""
    
    def __init__(self, upload_dir: str = "static/uploads/campaigns"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported file extensions
        self.supported_extensions = {'.csv', '.xlsx', '.xls'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """Validate uploaded file"""
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                return {"valid": False, "error": "File does not exist"}
            
            # Check file extension
            if file_path.suffix.lower() not in self.supported_extensions:
                return {
                    "valid": False, 
                    "error": f"Unsupported file type. Supported: {', '.join(self.supported_extensions)}"
                }
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                return {
                    "valid": False, 
                    "error": f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
                }
            
            # Try to read file structure
            try:
                if file_path.suffix.lower() == '.csv':
                    processor = CSVProcessor()
                else:
                    processor = ExcelProcessor()
                
                info = processor.get_file_info(str(file_path))
                
                return {
                    "valid": True,
                    "file_info": info,
                    "file_size": file_size,
                    "processor_type": type(processor).__name__
                }
                
            except Exception as e:
                return {"valid": False, "error": f"File format error: {str(e)}"}
                
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return {"valid": False, "error": f"Validation error: {str(e)}"}
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """Save uploaded file and return path"""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            safe_filename = f"{name}_{timestamp}{ext}"
            
            file_path = self.upload_dir / safe_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File saved: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    def get_processor(self, file_path: str):
        """Get appropriate processor for file type"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.csv':
            return CSVProcessor()
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            return ExcelProcessor()
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

class CSVProcessor:
    """CSV file processor"""
    
    def __init__(self):
        self.encoding_options = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        self.delimiter_options = [',', ';', '\t', '|']
    
    def detect_encoding(self, file_path: str) -> str:
        """Detect CSV file encoding"""
        # Try common encodings
        for encoding in self.encoding_options:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1000)  # Try reading first 1KB
                return encoding
            except UnicodeDecodeError:
                continue
        return 'utf-8'  # Default fallback
    
    def detect_delimiter(self, file_path: str, encoding: str = 'utf-8') -> str:
        """Detect CSV delimiter"""
        try:
            import csv
            
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                return delimiter
        except Exception:
            return ','
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get CSV file information"""
        try:
            # Detect encoding and delimiter
            encoding = self.detect_encoding(file_path)
            delimiter = self.detect_delimiter(file_path, encoding)
            
            # Read CSV with pandas
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                nrows=0  # Just get headers
            )
            
            headers = df.columns.tolist()
            
            # Read a few sample rows
            sample_df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                nrows=5
            )
            
            # Clean sample data - replace NaN with empty strings
            sample_df = sample_df.fillna('')
            
            # Get total row count (approximate for large files)
            total_rows = self._count_rows(file_path, encoding, delimiter)
            
            return {
                "headers": headers,
                "total_rows": total_rows,
                "sample_data": sample_df.to_dict('records'),
                "encoding": encoding,
                "delimiter": delimiter,
                "column_count": len(headers)
            }
            
        except Exception as e:
            logger.error(f"CSV info extraction error: {str(e)}")
            raise
    
    def _count_rows(self, file_path: str, encoding: str, delimiter: str) -> int:
        """Count total rows in CSV file"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Skip header
                next(f)
                return sum(1 for _ in f)
        except Exception:
            # Fallback: use pandas (slower but more reliable)
            try:
                df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
                return len(df)
            except Exception:
                return 0
    
    def read_data(self, file_path: str, start_row: int = 1, end_row: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read CSV data within specified row range"""
        try:
            encoding = self.detect_encoding(file_path)
            delimiter = self.detect_delimiter(file_path, encoding)
            
            # Calculate skiprows and nrows
            skiprows = max(0, start_row - 1)  # -1 because we don't skip header
            if end_row:
                nrows = end_row - start_row + 1
            else:
                nrows = None
            
            # Read data
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                skiprows=range(1, skiprows + 1) if skiprows > 0 else None,
                nrows=nrows
            )
            
            # Clean data
            df = df.fillna('')  # Replace NaN with empty strings
            df.columns = df.columns.str.strip()  # Strip whitespace from column names
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"CSV data reading error: {str(e)} - File: {file_path}")
            raise ValueError(f"Failed to read CSV file: {str(e)}")

class ExcelProcessor:
    """Excel file processor"""
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get Excel file information"""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            # Get first sheet by default
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=0)
            
            headers = df.columns.tolist()
            
            # Read sample data
            sample_df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5)
            
            # Clean sample data - replace NaN with empty strings
            sample_df = sample_df.fillna('')
            
            # Get total row count
            full_df = pd.read_excel(file_path, sheet_name=sheet_name)
            total_rows = len(full_df)
            
            return {
                "headers": headers,
                "total_rows": total_rows,
                "sample_data": sample_df.to_dict('records'),
                "sheet_names": excel_file.sheet_names,
                "active_sheet": sheet_name,
                "column_count": len(headers)
            }
            
        except Exception as e:
            logger.error(f"Excel info extraction error: {str(e)}")
            raise
    
    def read_data(self, file_path: str, start_row: int = 1, end_row: Optional[int] = None, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read Excel data within specified row range"""
        try:
            # Determine sheet
            if not sheet_name:
                excel_file = pd.ExcelFile(file_path)
                sheet_name = excel_file.sheet_names[0]
            
            # Calculate skiprows and nrows
            skiprows = max(0, start_row - 1)
            if end_row:
                nrows = end_row - start_row + 1
            else:
                nrows = None
            
            # Read data
            if skiprows > 0:
                # Read header first
                header_df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=0)
                # Then read data with skiprows
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    skiprows=range(1, skiprows + 1),
                    nrows=nrows
                )
                # Ensure we use the original headers
                df.columns = header_df.columns
            else:
                # No rows to skip, read normally
                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    nrows=nrows
                )
            
            # Clean data
            df = df.fillna('')  # Replace NaN with empty strings
            df.columns = df.columns.str.strip()  # Strip whitespace from column names
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Excel data reading error: {str(e)} - File: {file_path}, Sheet: {sheet_name}")
            raise ValueError(f"Failed to read Excel file: {str(e)}")

class DataPreprocessor:
    """Data preprocessing and validation"""
    
    @staticmethod
    def clean_phone_number(phone: str) -> str:
        """Clean and standardize phone number"""
        if not phone:
            return ""
        
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, str(phone)))
        
        # Remove leading country codes if present
        if cleaned.startswith('1') and len(cleaned) == 11:  # US format
            cleaned = cleaned[1:]
        elif cleaned.startswith('234') and len(cleaned) == 13:  # Nigeria format
            cleaned = cleaned[3:]
        
        return cleaned
    
    @staticmethod
    def validate_required_columns(data: List[Dict[str, Any]], required_columns: List[str]) -> List[str]:
        """Validate that required columns exist in data"""
        if not data:
            return ["No data provided"]
        
        available_columns = set(data[0].keys())
        missing_columns = [col for col in required_columns if col not in available_columns]
        
        return missing_columns
    
    @staticmethod
    def detect_column_mapping(headers: List[str]) -> Dict[str, str]:
        """Auto-detect column mapping based on common patterns"""
        mapping = {}
        
        # Common phone number patterns
        phone_patterns = ['phone', 'mobile', 'number', 'tel', 'contact']
        for header in headers:
            header_lower = header.lower()
            if any(pattern in header_lower for pattern in phone_patterns):
                mapping['phone_number'] = header
                break
        
        # Common name patterns
        name_patterns = ['name', 'first_name', 'firstname', 'full_name', 'fullname']
        for header in headers:
            header_lower = header.lower()
            if any(pattern in header_lower for pattern in name_patterns):
                mapping['name'] = header
                break
        
        # Message samples pattern
        for header in headers:
            header_lower = header.lower()
            if 'message' in header_lower and 'sample' in header_lower:
                mapping['message_samples'] = header
                break
        
        return mapping
    
    @staticmethod
    def preview_processed_data(data: List[Dict[str, Any]], column_mapping: Dict[str, str], limit: int = 5) -> List[Dict[str, Any]]:
        """Preview how data will be processed with given column mapping"""
        processed = []
        
        for i, row in enumerate(data[:limit]):
            processed_row = {"row_number": i + 1}
            
            # Map columns
            for target_col, source_col in column_mapping.items():
                if source_col in row:
                    value = row[source_col]
                    
                    # Apply preprocessing
                    if target_col == 'phone_number':
                        value = DataPreprocessor.clean_phone_number(value)
                    elif target_col == 'name':
                        value = str(value).strip()
                    
                    processed_row[target_col] = value
            
            # Include original data for reference
            processed_row['original_data'] = row
            processed.append(processed_row)
        
        return processed
