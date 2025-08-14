"""
Check server logs for detailed error information
"""

import pandas as pd
import os

# Read the CSV file locally to understand its structure
csv_file = r"C:\Users\leg\Downloads\new_leads_complete.csv"

print("📊 Analyzing CSV file structure...\n")

try:
    # Read with different encodings
    for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(csv_file, encoding=encoding, nrows=5)
            print(f"✅ Successfully read with encoding: {encoding}")
            break
        except Exception as e:
            print(f"❌ Failed with {encoding}: {str(e)[:50]}...")
    
    print(f"\nFile info:")
    print(f"- Shape: {df.shape}")
    print(f"- Columns: {list(df.columns)}")
    print(f"\nColumn details:")
    for col in df.columns:
        print(f"  - {col}: {df[col].dtype}")
    
    # Check for problematic characters
    print(f"\nFirst row data:")
    for col in df.columns:
        value = df.iloc[0][col]
        print(f"  - {col}: {repr(value)}")
    
    # Check for any null/missing values
    print(f"\nMissing values per column:")
    print(df.isnull().sum())
    
    # Create a cleaned test file
    print("\n📝 Creating cleaned test file...")
    
    # Select just a few essential columns
    essential_cols = ['phone_number', 'saved_name', 'country_code']
    available_cols = [col for col in essential_cols if col in df.columns]
    
    if available_cols:
        test_df = df[available_cols].head(5)
        test_df.to_csv("cleaned_test.csv", index=False, encoding='utf-8')
        print("✅ Created cleaned_test.csv with essential columns")
        print(f"   Columns: {available_cols}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)}")

print("\n💡 If upload still fails, check the server console for detailed error messages.")
print("   The server logs will show the exact line where the error occurs.")
