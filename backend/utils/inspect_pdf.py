import pypdf
import sys

pdf_path = r"C:\Users\401pr\Downloads\all_india_stock_companies.pdf"

try:
    reader = pypdf.PdfReader(pdf_path)
    print(f"Number of pages: {len(reader.pages)}")
    
    # Print first page text to understand layout
    page1 = reader.pages[0]
    text = page1.extract_text()
    print("--- PAGE 1 TEXT SAMPLE ---")
    print(text[:2000])
    print("--------------------------")
    
except Exception as e:
    print(f"Error reading PDF: {e}")
