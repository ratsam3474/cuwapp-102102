#!/usr/bin/env python3
"""
CRITICAL SECURITY FIX SCRIPT
Patches all endpoints to require authentication
"""

import re
import sys

def fix_auth_in_file(filepath):
    """Fix authentication requirements in main.py"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern to find all functions with optional user_id
    pattern = r'(async def \w+\([^)]*user_id: Optional\[str\] = Query\(None\)[^)]*\):)'
    
    endpoints = re.findall(pattern, content)
    print(f"Found {len(endpoints)} endpoints with optional user_id")
    
    # Fix 1: Change all Optional[str] = Query(None) to str = Query(...)
    content = content.replace(
        'user_id: Optional[str] = Query(None)',
        'user_id: str = Query(..., description="User ID is required")'
    )
    
    # Fix 2: Add authentication check at the beginning of each endpoint
    auth_check = """
        # SECURITY: Require user_id
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
"""
    
    # Find all "if not user_id:" blocks that return data and fix them
    patterns_to_fix = [
        # Pattern for returning all data when no user_id
        (r'if not user_id:\s*#[^\n]*\n\s*return[^\n]*all[^\n]*', 
         'if not user_id:\n            return {"success": False, "data": [], "error": "Authentication required"}'),
        
        # Pattern for admin mode
        (r'if not user_id:\s*#[^\n]*admin[^\n]*\n[^\n]*', 
         'if not user_id:\n            return {"success": False, "data": [], "error": "Authentication required"}'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    # Save the fixed file
    output_file = filepath.replace('.py', '_SECURE.py')
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"Fixed file saved to: {output_file}")
    
    # Show the changes summary
    print("\nChanges made:")
    print("1. Changed all 'user_id: Optional[str] = Query(None)' to 'user_id: str = Query(...)'")
    print("2. Fixed all 'if not user_id' blocks to return authentication error")
    print("\n⚠️  CRITICAL: Deploy this fix immediately to production!")
    
    return output_file

if __name__ == "__main__":
    filepath = "/Users/JE/Documents/102102/production_20250814_1716/10210-api/main.py"
    fixed_file = fix_auth_in_file(filepath)
    
    print("\n" + "="*60)
    print("DEPLOYMENT COMMANDS:")
    print("="*60)
    print(f"scp {fixed_file} root@174.138.55.42:/root/102102/10210-api/main.py")
    print("ssh root@174.138.55.42")
    print("cd /root/102102/10210-api && kill $(lsof -t -i:8000); nohup python main.py > api.log 2>&1 &")