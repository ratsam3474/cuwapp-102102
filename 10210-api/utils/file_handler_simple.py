"""
Mock file handler for testing without python-magic
"""
import os
import pandas as pd
import json
from typing import Dict, List, Any, Optional

class FileHandler:
    """Simple file handler that works without python-magic"""
    
    def __init__(self):
        self.upload_dir = "static/uploads"
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def save_upload(self, file) -> str:
        """Save uploaded file and return path"""
        file_path = os.path.join(self.upload_dir, file.filename)
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        await file.seek(0)  # Reset file pointer
        return file_path
    
    def read_csv(self, file_path: str) -> pd.DataFrame:
        """Read CSV file"""
        return pd.read_csv(file_path)
    
    def read_excel(self, file_path: str) -> pd.DataFrame:
        """Read Excel file"""
        return pd.read_excel(file_path)
    
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """Basic file validation"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.csv':
            df = self.read_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            df = self.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        
        return {
            "total_rows": len(df),
            "headers": list(df.columns),
            "file_path": file_path,
            "preview": df.head(5).to_dict('records')
        }
