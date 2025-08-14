import pandas as pd
import sys

if len(sys.argv) > 1:
    file_path = sys.argv[1]
else:
    file_path = "static/uploads/campaigns/Anon Arbers_participants (4)_20250803_015619.xlsx"

try:
    df = pd.read_excel(file_path, nrows=5)
    print(f"File: {file_path}")
    print(f"\nHeaders ({len(df.columns)} columns):")
    for i, col in enumerate(df.columns):
        print(f"  {i+1}. '{col}'")
    
    print(f"\nData rows: {len(df)}")
    print("\nFirst row data:")
    if len(df) > 0:
        for col in df.columns:
            value = df.iloc[0][col]
            print(f"  {col}: {value}")
    else:
        print("  No data rows found")
        
except Exception as e:
    print(f"Error reading file: {e}")