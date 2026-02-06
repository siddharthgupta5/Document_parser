"""
Insurance Regulatory Document Parser
=====================================

A specialized parser for extracting financial fields from IRDAI regulatory filings
and insurance company quarterly reports. Designed to handle complex tabular data,
multi-page forms, and standardized regulatory formats.

This parser targets documents like:
- IRDAI NL Forms (NL-1B, NL-35, NL-37, etc.)
- Quarterly Revenue Accounts  
- Claims Data Reports
- Business Distribution Reports
- Reinsurance Reports
- Geographical Distribution Reports
"""

import re
import PyPDF2
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class FieldCategory(Enum):
    """Categories of financial fields in regulatory documents"""
    PREMIUM = "premium"
    CLAIMS = "claims"
    REVENUE = "revenue"
    EXPENSES = "expenses"
    INVESTMENT = "investment"
    PROFIT_LOSS = "profit_loss"
    POLICY_INFO = "policy_info"
    REINSURANCE = "reinsurance"
    BUSINESS_METRICS = "business_metrics"
    GEOGRAPHICAL = "geographical"
    CHANNEL_WISE = "channel_wise"


@dataclass
class FinancialField:
    """Represents a financial field extracted from a regulatory document"""
    name: str
    value: Union[str, float, int, Dict]
    category: FieldCategory
    unit: Optional[str] = None
    period: Optional[str] = None
    confidence: float = 1.0
    context: Optional[str] = None
    page: Optional[int] = None
    form_number: Optional[str] = None
    
    def __repr__(self):
        return f"FinancialField(name='{self.name}', value={self.value}, category={self.category.value})"


class InsuranceRegulatoryParser:
    """
    Parser for IRDAI regulatory insurance documents.
    
    Extraction Strategies:
    1. Form-based extraction for standard IRDAI forms
    2. Table structure recognition for tabular data
    3. Pattern matching for standardized financial entries
    4. Context-aware extraction for narrative sections
    5. Cross-referencing between related forms
    """
    
    def __init__(self):
        self._init_patterns()
        
    def _init_patterns(self):
        """Initialize regex patterns for regulatory document fields"""
        
        # Amount patterns (in Lakhs - Indian financial format)
        self.amount_pattern = r'([\d,]+(?:\.\d{1,2})?)'
        
        # Form identification patterns
        self.form_patterns = {
            'NL-1B': r'FORM NL-1B.*?REVENUE ACCOUNT',
            'NL-35': r'FORM NL-35.*?QUARTERLY BUSINESS RETURNS',
            'NL-36': r'FORM NL-36.*?BUSINESS.*?CHANNELS',
            'NL-37': r'FORM NL-37.*?CLAIMS DATA',
            'NL-39': r'FORM NL-39.*?AGEING OF CLAIMS',
            'NL-33': r'FORM NL-33.*?REINSURANCE',
            'NL-34': r'FORM NL-34.*?GEOGRAPHICAL DISTRIBUTION',
        }
        
        # Company identification
        self.company_pattern = r'Name of the Insurer:\s*([A-Za-z\s&]+(?:Limited|Ltd\.?))'
        self.registration_pattern = r'Registration\s+(?:No|Number)[.:]*\s*(\d+)'
        self.date_pattern = r'(?:Date:|ending on)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main parsing function - extracts all financial fields from regulatory PDF.
        
        Args:
            pdf_path: Path to the PDF regulatory filing
            
        Returns:
            Dictionary containing categorized financial fields
        """
        # Extract text from PDF
        full_text, page_texts = self._extract_pdf_text(pdf_path)
        
        # Initialize results structure
        results = {
            'document_metadata': self._extract_metadata(full_text),
            'premiums': [],
            'claims': [],
            'revenue_account': [],
            'expenses': [],
            'investments': [],
            'profit_loss': [],
            'business_distribution': [],
            'geographical_distribution': [],
            'channel_wise_distribution': [],
            'reinsurance': [],
            'policy_metrics': [],
            'summary_statistics': {}
        }
        
        # Identify and extract from specific forms
        forms_found = self._identify_forms(full_text)
        
        # Extract based on found forms
        if 'NL-1B' in forms_found:
            results['revenue_account'] = self._extract_nl_1b(full_text, page_texts)
            
        if 'NL-35' in forms_found:
            business_data = self._extract_nl_35(full_text, page_texts)
            results['premiums'].extend(business_data['premiums'])
            results['policy_metrics'].extend(business_data['policies'])
            
        if 'NL-36' in forms_found:
            channel_data = self._extract_nl_36(full_text, page_texts)
            results['channel_wise_distribution'] = channel_data
            
        if 'NL-37' in forms_found:
            claims_data = self._extract_nl_37(full_text, page_texts)
            results['claims'].extend(claims_data)
            
        if 'NL-34' in forms_found:
            geo_data = self._extract_nl_34(full_text, page_texts)
            results['geographical_distribution'] = geo_data
            
        if 'NL-33' in forms_found:
            reins_data = self._extract_nl_33(full_text, page_texts)
            results['reinsurance'] = reins_data
        
        # Calculate summary statistics
        results['summary_statistics'] = self._calculate_summary(results)
        
        return results
    
    def _extract_pdf_text(self, pdf_path: str) -> Tuple[str, Dict[int, str]]:
        """Extract text from PDF page by page"""
        full_text = ""
        page_texts = {}
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                page_texts[page_num + 1] = page_text
                full_text += f"\n--- Page {page_num + 1} ---\n" + page_text
        
        return full_text, page_texts
    
    def _extract_metadata(self, text: str) -> Dict[str, str]:
        """Extract document metadata"""
        metadata = {}
        
        # Company name
        company_match = re.search(self.company_pattern, text, re.IGNORECASE)
        if company_match:
            metadata['insurer_name'] = company_match.group(1).strip()
        
        # Registration number
        reg_match = re.search(self.registration_pattern, text, re.IGNORECASE)
        if reg_match:
            metadata['registration_number'] = reg_match.group(1)
        
        # Date/Period
        date_match = re.search(self.date_pattern, text, re.IGNORECASE)
        if date_match:
            metadata['reporting_period'] = date_match.group(1)
        
        return metadata
    
    def _identify_forms(self, text: str) -> List[str]:
        """Identify which IRDAI forms are present in the document"""
        found_forms = []
        for form_name, pattern in self.form_patterns.items():
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                found_forms.append(form_name)
        return found_forms
    
    def _extract_nl_1b(self, text: str, page_texts: Dict[int, str]) -> List[FinancialField]:
        """Extract Revenue Account data (Form NL-1B)"""
        fields = []
        
        # Find Revenue Account section
        revenue_match = re.search(r'REVENUE ACCOUNT FOR THE PERIOD.*?Total \(C\)', text, re.DOTALL | re.IGNORECASE)
        
        if revenue_match:
            section = revenue_match.group()
            
            # Extract key revenue items with context
            patterns = {
                'Premiums Earned (Net)': r'Premiums earned.*?Miscellaneous.*?(\d[\d,]+(?:\.\d{2})?)',
                'Claims Incurred (Net)': r'Claims Incurred.*?Miscellaneous.*?(\d[\d,]+(?:\.\d{2})?)',
                'Commission (Net)': r'Commission.*?Miscellaneous.*?(\d[\d,]+(?:\.\d{2})?)',
                'Operating Expenses': r'Operating expenses related to Insurance Business.*?(\d[\d,]+(?:\.\d{2})?)',
                'Profit on Sale of Investments': r'Profit.*?sale.*?Investments.*?Miscellaneous.*?(\d[\d,]+(?:\.\d{2})?)',
                'Interest Dividend & Rent': r'Interest, Dividend & Rent.*?Miscellaneous.*?(\d[\d,]+(?:\.\d{2})?)',
                'Total Income': r'Total \(A\).*?(\d[\d,]+(?:\.\d{2})?)',
                'Total Expenses': r'Total \(B\).*?(\d[\d,]+(?:\.\d{2})?)',
                'Operating Profit': r'Operating Profit.*?(\d[\d,]+(?:\.\d{2})?)',
            }
            
            for name, pattern in patterns.items():
                match = re.search(pattern, section, re.IGNORECASE | re.DOTALL)
                if match:
                    value = self._parse_number(match.group(1))
                    
                    # Determine category
                    if 'Premium' in name:
                        category = FieldCategory.PREMIUM
                    elif 'Claims' in name:
                        category = FieldCategory.CLAIMS
                    elif 'Commission' in name or 'Expenses' in name:
                        category = FieldCategory.EXPENSES
                    elif 'Investment' in name or 'Interest' in name:
                        category = FieldCategory.INVESTMENT
                    elif 'Profit' in name:
                        category = FieldCategory.PROFIT_LOSS
                    else:
                        category = FieldCategory.REVENUE
                    
                    fields.append(FinancialField(
                        name=name,
                        value=value,
                        category=category,
                        unit="Rs. Lakhs",
                        period="Quarter",
                        form_number="NL-1B"
                    ))
        
        return fields
    
    def _extract_nl_35(self, text: str, page_texts: Dict[int, str]) -> Dict[str, List[FinancialField]]:
        """Extract Quarterly Business Returns (Form NL-35)"""
        result = {'premiums': [], 'policies': []}
        
        # Find NL-35 section
        nl35_match = re.search(r'FORM NL-35.*?(?=FORM NL-|$)', text, re.DOTALL | re.IGNORECASE)
        
        if nl35_match:
            section = nl35_match.group()
            
            # Extract line of business data
            lines_of_business = [
                ('Fire', 'fire'),
                ('Marine Cargo', 'marine_cargo'),
                ('Motor OD', 'motor_od'),
                ('Motor TP', 'motor_tp'),
                ('Health', 'health'),
                ('Personal Accident', 'personal_accident'),
                ('Travel', 'travel'),
                ('Public/ Product Liability', 'public_liability'),
            ]
            
            for business_name, key in lines_of_business:
                # Pattern to match premium and policy count
                pattern = rf'{re.escape(business_name)}.*?(\d[\d,]+)\s+(\d[\d,]+)'
                match = re.search(pattern, section, re.IGNORECASE)
                
                if match:
                    premium = self._parse_number(match.group(1))
                    policies = self._parse_number(match.group(2))
                    
                    if premium > 0:  # Only add if there's actual business
                        result['premiums'].append(FinancialField(
                            name=f"{business_name} Premium",
                            value=premium,
                            category=FieldCategory.PREMIUM,
                            unit="Rs. Lakhs",
                            period="Quarter",
                            form_number="NL-35"
                        ))
                        
                        result['policies'].append(FinancialField(
                            name=f"{business_name} Policies",
                            value=int(policies),
                            category=FieldCategory.BUSINESS_METRICS,
                            unit="Number of Policies",
                            period="Quarter",
                            form_number="NL-35"
                        ))
        
        return result
    
    def _extract_nl_36(self, text: str, page_texts: Dict[int, str]) -> List[FinancialField]:
        """Extract Business Channels data (Form NL-36)"""
        fields = []
        
        # Find NL-36 section
        nl36_match = re.search(r'FORM NL-36.*?(?=FORM NL-|$)', text, re.DOTALL | re.IGNORECASE)
        
        if nl36_match:
            section = nl36_match.group()
            
            # Extract channel-wise distribution
            channels = [
                ('Corporate Agents-Banks', 'corporate_agents_banks'),
                ('Corporate Agents -Others', 'corporate_agents_others'),
                ('Brokers', 'brokers'),
                ('Direct Business', 'direct_business'),
            ]
            
            for channel_name, key in channels:
                pattern = rf'{re.escape(channel_name)}.*?(\d[\d,]+)\s+(\d[\d,]+)'
                match = re.search(pattern, section, re.IGNORECASE)
                
                if match:
                    policies = self._parse_number(match.group(1))
                    premium = self._parse_number(match.group(2))
                    
                    fields.append(FinancialField(
                        name=f"{channel_name} - Policies",
                        value=int(policies),
                        category=FieldCategory.CHANNEL_WISE,
                        unit="Number of Policies",
                        form_number="NL-36"
                    ))
                    
                    fields.append(FinancialField(
                        name=f"{channel_name} - Premium",
                        value=premium,
                        category=FieldCategory.CHANNEL_WISE,
                        unit="Rs. Lakhs",
                        form_number="NL-36"
                    ))
            
            # Extract grand total
            grand_total_match = re.search(r'Grand Total.*?(\d[\d,]+)\s+(\d[\d,]+)', section, re.IGNORECASE)
            if grand_total_match:
                total_policies = self._parse_number(grand_total_match.group(1))
                total_premium = self._parse_number(grand_total_match.group(2))
                
                fields.append(FinancialField(
                    name="Total Policies (All Channels)",
                    value=int(total_policies),
                    category=FieldCategory.BUSINESS_METRICS,
                    unit="Number of Policies",
                    form_number="NL-36"
                ))
                
                fields.append(FinancialField(
                    name="Total Premium (All Channels)",
                    value=total_premium,
                    category=FieldCategory.PREMIUM,
                    unit="Rs. Lakhs",
                    form_number="NL-36"
                ))
        
        return fields
    
    def _extract_nl_37(self, text: str, page_texts: Dict[int, str]) -> List[FinancialField]:
        """Extract Claims Data (Form NL-37)"""
        fields = []
        
        # Find NL-37 section
        nl37_match = re.search(r'FORM NL-37.*?(?=FORM NL-|$)', text, re.DOTALL | re.IGNORECASE)
        
        if nl37_match:
            section = nl37_match.group()
            
            # Extract claims metrics from the total column
            claims_metrics = {
                'Claims Outstanding (Beginning)': r'Claims O/S at the beginning.*?Total.*?(\d[\d,]+)',
                'Claims Reported (Count)': r'Claims reported during the period.*?Total.*?(\d[\d,]+)',
                'Claims Settled (Count)': r'Claims Settled during the period.*?Total.*?(\d[\d,]+)',
                'Claims Paid (Amount)': r'paid during the period.*?Total.*?(\d[\d,]+)',
                'Claims Repudiated': r'Claims Repudiated during the period.*?Total.*?(\d[\d,]+)',
                'Claims Outstanding (End)': r'Claims O/S at End of the period.*?Total.*?(\d[\d,]+)',
            }
            
            for name, pattern in claims_metrics.items():
                match = re.search(pattern, section, re.IGNORECASE)
                if match:
                    value = self._parse_number(match.group(1))
                    
                    # Determine if it's count or amount
                    if 'Count' in name or 'Repudiated' in name or value > 10000:
                        unit = "Number of Claims"
                    else:
                        unit = "Rs. Lakhs"
                    
                    fields.append(FinancialField(
                        name=name,
                        value=value if 'Count' in name else value,
                        category=FieldCategory.CLAIMS,
                        unit=unit,
                        form_number="NL-37"
                    ))
        
        return fields
    
    def _extract_nl_34(self, text: str, page_texts: Dict[int, str]) -> List[FinancialField]:
        """Extract Geographical Distribution (Form NL-34)"""
        fields = []
        
        # Find NL-34 section
        nl34_match = re.search(r'FORM NL-34.*?(?=FORM NL-|$)', text, re.DOTALL | re.IGNORECASE)
        
        if nl34_match:
            section = nl34_match.group()
            
            # Extract state-wise premium (top 5 states by premium)
            states = ['Karnataka', 'Maharashtra', 'Delhi', 'Tamil Nadu', 'Telangana', 'Haryana', 'Gujarat']
            
            for state in states:
                # Look for total premium for the state
                pattern = rf'{state}.*?(\d[\d,]+)\s+(\d[\d,]+)\s+(\d[\d,]+)' 
                match = re.search(pattern, section, re.IGNORECASE)
                
                if match:
                    try:
                        premium = self._parse_number(match.group(3))
                        if premium > 500:  # Only add significant business
                            fields.append(FinancialField(
                                name=f"{state} - Total Premium",
                                value=premium,
                                category=FieldCategory.GEOGRAPHICAL,
                                unit="Rs. Lakhs",
                                form_number="NL-34"
                            ))
                    except:
                        pass
        
        return fields
    
    def _extract_nl_33(self, text: str, page_texts: Dict[int, str]) -> List[FinancialField]:
        """Extract Reinsurance data (Form NL-33)"""
        fields = []
        
        # Find NL-33 section
        nl33_match = re.search(r'FORM NL-33.*?(?=FORM NL-|$)', text, re.DOTALL | re.IGNORECASE)
        
        if nl33_match:
            section = nl33_match.group()
            
            # Extract premium ceded
            patterns = {
                'Total Premium Ceded': r'Total.*?(\d[\d,]+(?:\.\d{2})?)\s+[\d,]+\s+\d+',
                'GIC Re Premium Share': r'GIC Re.*?(\d+)%',
                'FRBs Premium Share': r'FRBs.*?(\d+)%',
            }
            
            for name, pattern in patterns.items():
                match = re.search(pattern, section, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    if '%' in name:
                        fields.append(FinancialField(
                            name=name,
                            value=f"{value}%",
                            category=FieldCategory.REINSURANCE,
                            unit="Percentage",
                            form_number="NL-33"
                        ))
                    else:
                        fields.append(FinancialField(
                            name=name,
                            value=self._parse_number(value),
                            category=FieldCategory.REINSURANCE,
                            unit="Rs. Lakhs",
                            form_number="NL-33"
                        ))
        
        return fields
    
    def _calculate_summary(self, results: Dict) -> Dict[str, float]:
        """Calculate summary statistics from extracted data"""
        summary = {}
        
        # Total premium across all sources
        total_premium = 0
        for field in results.get('premiums', []):
            if isinstance(field.value, (int, float)):
                total_premium += field.value
        summary['total_premium_lakhs'] = total_premium
        
        # Total claims
        total_claims_paid = 0
        for field in results.get('claims', []):
            if 'Paid' in field.name and isinstance(field.value, (int, float)):
                total_claims_paid = field.value
        summary['total_claims_paid_lakhs'] = total_claims_paid
        
        # Loss ratio if both available
        if total_premium > 0 and total_claims_paid > 0:
            summary['loss_ratio_percent'] = round((total_claims_paid / total_premium) * 100, 2)
        
        return summary
    
    def _parse_number(self, num_str: str) -> float:
        """Convert Indian number format string to float"""
        cleaned = re.sub(r'[,\s]', '', str(num_str))
        try:
            return float(cleaned)
        except:
            return 0.0
    
    def format_results(self, results: Dict[str, Any]) -> str:
        """Format extraction results as readable text"""
        output = []
        output.append("=" * 120)
        output.append("INSURANCE REGULATORY DOCUMENT PARSER - EXTRACTION RESULTS")
        output.append("=" * 120)
        
        # Document metadata
        if results.get('document_metadata'):
            output.append("\nDOCUMENT METADATA")
            output.append("-" * 120)
            for key, value in results['document_metadata'].items():
                output.append(f"  {key.replace('_', ' ').title():<40} : {value}")
        
        # Summary statistics
        if results.get('summary_statistics'):
            output.append("\nSUMMARY STATISTICS")
            output.append("-" * 120)
            for key, value in results['summary_statistics'].items():
                key_formatted = key.replace('_', ' ').title()
                if isinstance(value, float):
                    output.append(f"  {key_formatted:<40} : {value:>20,.2f}")
                else:
                    output.append(f"  {key_formatted:<40} : {value}")
        
        # All categories
        categories = [
            ('revenue_account', 'REVENUE ACCOUNT (NL-1B)'),
            ('premiums', 'PREMIUMS'),
            ('claims', 'CLAIMS DATA'),
            ('expenses', 'EXPENSES'),
            ('investments', 'INVESTMENT INCOME'),
            ('profit_loss', 'PROFIT & LOSS'),
            ('channel_wise_distribution', 'CHANNEL-WISE DISTRIBUTION'),
            ('geographical_distribution', 'GEOGRAPHICAL DISTRIBUTION'),
            ('reinsurance', 'REINSURANCE'),
            ('policy_metrics', 'POLICY METRICS'),
        ]
        
        for cat_key, cat_title in categories:
            fields = results.get(cat_key, [])
            if fields:
                output.append(f"\n{cat_title}")
                output.append("-" * 120)
                for field in fields:
                    if isinstance(field.value, (int, float)):
                        if field.unit:
                            output.append(f"  {field.name:<60} : {field.value:>20,.2f} {field.unit}")
                        else:
                            output.append(f"  {field.name:<60} : {field.value:>20,.2f}")
                    else:
                        output.append(f"  {field.name:<60} : {field.value}")
        
        output.append("\n" + "=" * 120)
        return "\n".join(output)
    
    def export_to_json(self, results: Dict[str, Any], output_path: str):
        """Export results to JSON file"""
        json_results = {
            'document_metadata': results.get('document_metadata', {}),
            'summary_statistics': results.get('summary_statistics', {}),
        }
        
        # Convert FinancialField objects to dictionaries
        for category in results:
            if category not in ['document_metadata', 'summary_statistics']:
                json_results[category] = [
                    {
                        'name': field.name,
                        'value': field.value,
                        'category': field.category.value if hasattr(field, 'category') else None,
                        'unit': field.unit if hasattr(field, 'unit') else None,
                        'form_number': field.form_number if hasattr(field, 'form_number') else None,
                    }
                    for field in results[category]
                ] if isinstance(results[category], list) else results[category]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)
        
        return json_results
