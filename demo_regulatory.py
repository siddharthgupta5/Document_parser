"""
Demo Script for Insurance Regulatory Document Parser
====================================================

This script demonstrates the usage of the Insurance Regulatory Parser
on IRDAI regulatory filings and quarterly reports.

Usage:
    python demo_regulatory.py
"""

from insurance_regulatory_parser import InsuranceRegulatoryParser
import os
import json
from pathlib import Path
import sys


# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def main():
    print("=" * 120)
    print("INSURANCE REGULATORY DOCUMENT PARSER - DEMO")
    print("=" * 120)
    print()
    
    # Initialize parser
    parser = InsuranceRegulatoryParser()
    
    # Path to sample documents
    sample_dir = Path("sample_documents")
    
    # Find all PDF files in the sample_documents directory
    pdf_files = list(sample_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("[ERROR] No PDF files found in sample_documents directory")
        print(f"   Please place insurance regulatory PDF documents in: {sample_dir.absolute()}")
        return
    
    print(f"Found {len(pdf_files)} PDF document(s) to parse:\n")
    
    for pdf_file in pdf_files:
        print(f"\n{'='*120}")
        print(f"Processing: {pdf_file.name}")
        print(f"{'='*120}\n")
        
        try:
            # Parse the document
            print("[*] Extracting data from PDF...")
            results = parser.parse_pdf(str(pdf_file))
            
            # Display formatted results
            print("\n" + parser.format_results(results))
            
            # Export to JSON
            json_output_path = pdf_file.with_suffix('.json')
            parser.export_to_json(results, str(json_output_path))
            print(f"\n[*] Results exported to: {json_output_path.name}")
            
            # Print key highlights
            print("\n" + "=" * 120)
            print("KEY FINANCIAL HIGHLIGHTS")
            print("=" * 120)
            
            metadata = results.get('document_metadata', {})
            summary = results.get('summary_statistics', {})
            
            if metadata:
                print(f"\n[*] Insurer: {metadata.get('insurer_name', 'N/A')}")
                print(f"[*] Registration No: {metadata.get('registration_number', 'N/A')}")
                print(f"[*] Period: {metadata.get('reporting_period', 'N/A')}")
            
            if summary:
                print(f"\n[*] Total Premium: Rs. {summary.get('total_premium_lakhs', 0):,.2f} Lakhs")
                print(f"[*] Total Claims Paid: Rs. {summary.get('total_claims_paid_lakhs', 0):,.2f} Lakhs")
                if 'loss_ratio_percent' in summary:
                    print(f"[*] Loss Ratio: {summary.get('loss_ratio_percent')}%")
            
            # Count extracted fields by category
            print(f"\n[*] Fields Extracted by Category:")
            for category in ['premiums', 'claims', 'revenue_account', 'expenses', 
                           'investments', 'channel_wise_distribution']:
                count = len(results.get(category, []))
                if count > 0:
                    print(f"   - {category.replace('_', ' ').title()}: {count} fields")
            
            print("\n" + "=" * 120)
            print(f"[SUCCESS] Successfully parsed {pdf_file.name}")
            print("=" * 120)
            
        except Exception as e:
            print(f"\n[ERROR] Error processing {pdf_file.name}:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 120)
    print("PARSING COMPLETE")
    print("=" * 120)
    print()
    print("[*] Output files have been generated in the sample_documents directory")
    print("   - *.json files contain structured data in JSON format")
    print()


if __name__ == "__main__":
    main()
