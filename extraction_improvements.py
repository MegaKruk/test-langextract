"""
KEY-VALUE EXTRACTION IMPROVEMENTS
Target: 79% -> 90%+ accuracy

Implementation priority:
1. Date normalization
2. Fuzzy string matching
3. Enhanced extraction prompt
4. Multi-pass extraction
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from difflib import SequenceMatcher


# ============================================================================
# IMPROVEMENT 1: DATE NORMALIZATION
# ============================================================================

def normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize dates to YYYY-MM-DD format for consistent comparison.
    
    Handles formats like:
    - "27-05-2023", "27.05.2023", "27/05/2023"
    - "May 27, 2023", "27 May 2023"
    - "20th of May 2023"
    - "2023-05-27"
    
    Returns:
        str: Date in YYYY-MM-DD format, or None if parsing fails
    """
    if not date_str or date_str in ['', 'null', 'None', 'N/A']:
        return None
    
    # Clean the string
    date_str = str(date_str).strip()
    
    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
    
    # Remove words like "of"
    date_str = re.sub(r'\bof\b', '', date_str, flags=re.IGNORECASE)
    
    # Common date formats to try
    formats = [
        '%Y-%m-%d',           # 2023-05-27
        '%d-%m-%Y',           # 27-05-2023
        '%m-%d-%Y',           # 05-27-2023
        '%d.%m.%Y',           # 27.05.2023
        '%m.%d.%Y',           # 05.27.2023
        '%d/%m/%Y',           # 27/05/2023
        '%m/%d/%Y',           # 05/27/2023
        '%Y/%m/%d',           # 2023/05/27
        '%B %d, %Y',          # May 27, 2023
        '%d %B %Y',           # 27 May 2023
        '%b %d, %Y',          # May 27, 2023
        '%d %b %Y',           # 27 May 2023
        '%m/%d/%y',           # 05/27/23
        '%d-%m-%y',           # 27-05-23
        '%d.%m.%y',           # 27.05.23
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Try with month names in other positions
    # Handle "May 27 2023" (no comma)
    for separator in [' ', ', ']:
        try:
            parts = date_str.split(separator)
            if len(parts) >= 3:
                # Try "Month Day Year"
                dt = datetime.strptime(f"{parts[0]} {parts[1]} {parts[-1]}", '%B %d %Y')
                return dt.strftime('%Y-%m-%d')
        except:
            pass
    
    # If all else fails, return None
    return None


def dates_match(date1: str, date2: str) -> bool:
    """
    Check if two date strings represent the same date.
    
    Returns True if:
    - Both normalize to the same date
    - Both are null/None
    - Raw strings match (fallback)
    """
    if not date1 and not date2:
        return True
    
    if not date1 or not date2:
        return False
    
    # Try normalization
    norm1 = normalize_date(date1)
    norm2 = normalize_date(date2)
    
    if norm1 and norm2:
        return norm1 == norm2
    
    # Fallback to string comparison
    return str(date1).strip().lower() == str(date2).strip().lower()


# ============================================================================
# IMPROVEMENT 2: FUZZY STRING MATCHING
# ============================================================================

def fuzzy_string_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings.
    Returns value between 0.0 (no match) and 1.0 (perfect match).
    """
    if not str1 and not str2:
        return 1.0
    if not str1 or not str2:
        return 0.0
    
    # Normalize
    s1 = str(str1).strip().lower()
    s2 = str(str2).strip().lower()
    
    # Exact match
    if s1 == s2:
        return 1.0
    
    # Use SequenceMatcher for fuzzy comparison
    return SequenceMatcher(None, s1, s2).ratio()


def strings_fuzzy_match(
    str1: str,
    str2: str,
    threshold: float = 0.85,
    check_substring: bool = True
) -> bool:
    """
    Check if two strings match with fuzzy logic.
    
    Args:
        str1, str2: Strings to compare
        threshold: Minimum similarity ratio (0.0-1.0)
        check_substring: If True, also accept if one is substring of other
    
    Returns:
        bool: True if strings match within threshold
    """
    if not str1 and not str2:
        return True
    if not str1 or not str2:
        return False
    
    # Normalize
    s1 = str(str1).strip().lower()
    s2 = str(str2).strip().lower()
    
    # Exact match
    if s1 == s2:
        return True
    
    # Fuzzy similarity
    similarity = fuzzy_string_similarity(s1, s2)
    if similarity >= threshold:
        return True
    
    # Substring check (for cases like "ABC Corp" vs "ABC Corporation Ltd")
    if check_substring:
        if s1 in s2 or s2 in s1:
            # Only accept if shorter string is at least 60% of longer
            min_len = min(len(s1), len(s2))
            max_len = max(len(s1), len(s2))
            if min_len / max_len >= 0.6:
                return True
    
    return False


def normalize_value_for_comparison(value: Any, field_name: str = "") -> Any:
    """
    Normalize a value before comparison based on field type.
    
    Args:
        value: The value to normalize
        field_name: Optional field name to infer type
    
    Returns:
        Normalized value
    """
    if value is None or value in ['', 'null', 'None', 'N/A']:
        return None
    
    # Convert to string
    value_str = str(value).strip()
    
    # Check if it's a date field
    date_keywords = ['date', 'received', 'incident', 'effective', 'expiry', 'birth', 'dob']
    is_date = any(kw in field_name.lower() for kw in date_keywords)
    
    if is_date:
        normalized = normalize_date(value_str)
        return normalized if normalized else value_str
    
    # Check if it's a number/amount field
    amount_keywords = ['amount', 'premium', 'limit', 'deductible', 'price', 'cost']
    is_amount = any(kw in field_name.lower() for kw in amount_keywords)
    
    if is_amount:
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$£€¥,]', '', value_str)
        try:
            return float(cleaned)
        except:
            return value_str
    
    # Default: return as-is
    return value_str


# ============================================================================
# IMPROVEMENT 3: ENHANCED COMPARISON FUNCTION
# Combines date normalization + fuzzy matching
# ============================================================================

def compare_extracted_with_expected_IMPROVED(
    extracted: Dict[str, Any],
    expected: Dict[str, Any],
    date_fields: Optional[List[str]] = None,
    fuzzy_threshold: float = 0.85
) -> Dict:
    """
    Enhanced comparison with date normalization and fuzzy matching.
    
    Args:
        extracted: Extracted key-value pairs
        expected: Expected key-value pairs
        date_fields: Optional list of fields that contain dates
        fuzzy_threshold: Similarity threshold for fuzzy matching (0.85 = 85%)
    
    Returns:
        dict: Comparison results with improved matching
    """
    # Auto-detect date fields if not provided
    if date_fields is None:
        date_fields = []
        date_keywords = ['date', 'received', 'incident', 'effective', 'expiry', 'birth', 'dob']
        for key in expected.keys():
            if any(kw in key.lower() for kw in date_keywords):
                date_fields.append(key)
    
    comparison = {
        'matches': 0,
        'mismatches': 0,
        'missing': 0,
        'total_expected': len(expected),
        'total_extracted': sum(1 for v in extracted.values() if v is not None),
        'details': {},
        'match_types': {}  # Track how each match was achieved
    }
    
    for key, expected_value in expected.items():
        extracted_value = extracted.get(key)
        
        # Both null
        if extracted_value is None and expected_value is None:
            comparison['matches'] += 1
            comparison['details'][key] = {
                'status': 'match',
                'expected': None,
                'extracted': None,
                'match_method': 'both_null'
            }
            comparison['match_types'][key] = 'both_null'
            continue
        
        # Extracted is null
        if extracted_value is None:
            comparison['missing'] += 1
            comparison['details'][key] = {
                'status': 'missing',
                'expected': expected_value,
                'extracted': None
            }
            continue
        
        # Expected is null but extracted has value
        if expected_value is None:
            comparison['mismatches'] += 1
            comparison['details'][key] = {
                'status': 'mismatch',
                'expected': None,
                'extracted': extracted_value,
                'reason': 'expected_null_but_extracted'
            }
            continue
        
        # Both have values - try different matching strategies
        match_found = False
        match_method = None
        
        # Strategy 1: Exact match (after normalization)
        norm_extracted = normalize_value_for_comparison(extracted_value, key)
        norm_expected = normalize_value_for_comparison(expected_value, key)
        
        if norm_extracted == norm_expected:
            match_found = True
            match_method = 'exact_match_normalized'
        
        # Strategy 2: Date matching (if it's a date field)
        elif key in date_fields or any(kw in key.lower() for kw in ['date', 'dob', 'birth']):
            if dates_match(str(extracted_value), str(expected_value)):
                match_found = True
                match_method = 'date_match'
        
        # Strategy 3: Fuzzy string matching
        elif strings_fuzzy_match(str(extracted_value), str(expected_value), fuzzy_threshold):
            match_found = True
            match_method = 'fuzzy_match'
            similarity = fuzzy_string_similarity(str(extracted_value), str(expected_value))
            match_method = f'fuzzy_match_{similarity:.2f}'
        
        # Record result
        if match_found:
            comparison['matches'] += 1
            comparison['details'][key] = {
                'status': 'match',
                'expected': expected_value,
                'extracted': extracted_value,
                'match_method': match_method
            }
            comparison['match_types'][key] = match_method
        else:
            comparison['mismatches'] += 1
            similarity = fuzzy_string_similarity(str(extracted_value), str(expected_value))
            comparison['details'][key] = {
                'status': 'mismatch',
                'expected': expected_value,
                'extracted': extracted_value,
                'similarity': similarity
            }
    
    # Calculate accuracy
    if comparison['total_expected'] > 0:
        comparison['accuracy'] = (comparison['matches'] / comparison['total_expected']) * 100
    else:
        comparison['accuracy'] = 0.0
    
    return comparison


# ============================================================================
# IMPROVEMENT 4: ENHANCED EXTRACTION PROMPT
# Focus on addresses and scattered information
# ============================================================================

def get_enhanced_extraction_prompt(keys_to_extract: List[str]) -> str:
    """
    Generate enhanced extraction prompt with better guidance for addresses
    and scattered information.
    """
    
    keys_formatted = '", "'.join(keys_to_extract)
    
    prompt = f"""You are a precision data extraction specialist. Extract SPECIFIC key-value pairs from the document.

CRITICAL RULES:
1. Extract ONLY the requested keys - no additional keys
2. NEVER invent, guess, or generate values
3. If key not found, set value to null
4. Extract EXACTLY as written in document when possible
5. For dates, preserve the format from document
6. For amounts, include currency symbols and formatting
7. Be THOROUGH - scan ENTIRE document including:
   - Headers and footers
   - Tables and forms
   - Signatures and contact blocks
   - Quoted text and references
   - Multiple pages

KEYS TO EXTRACT:
{keys_formatted}

==================================
EXTRACTION GUIDELINES BY KEY TYPE:
==================================

DATE FIELDS (e.g., "loss_date", "incident_date", "date_received", "dob"):
   - Extract EXACTLY as formatted in document (MM/DD/YYYY, DD-MM-YYYY, "January 15, 2024", etc.)
   - Look for: section headers, form fields, date stamps, email headers
   - Common locations: Top of page, form fields labeled "Date:", timestamps
   - If only partial date present, extract what's available
   - Accept: "Occurred:", "Effective:", "Incident Date:", etc.

IDENTIFYING NUMBERS (e.g., "claim_number", "policy_number", "case_number"):
   - Extract complete number including any prefixes, suffixes, or special characters
   - Look for: explicit labels, reference numbers, tracking IDs
   - Common locations: Headers, subject lines, reference fields
   - Include dashes, slashes, and letter prefixes (e.g., "POL-2023-12345")
   - Watch for: "Claim #:", "Policy No:", "Ref:", "Case ID:"

NAME FIELDS (e.g., "claimant_name", "insured_name", "patient_name"):
   - Extract FULL name as written (First Last, Last First, First Middle Last, etc.)
   - Look in: form fields, signatures, contact info, headers
   - Common locations: 
     * "Name:" or "Full Name:" fields
     * Signature blocks
     * Contact information sections
     * "Regarding:", "Re:", "Subject:" lines
   - Include titles if present (Mr., Dr., etc.)
   - For organizations: extract complete legal name

ADDRESS FIELDS - CRITICAL (e.g., "loss_location", "claimant_address", "property_address"):
   ADDRESSES ARE OFTEN SCATTERED - LOOK CAREFULLY:
   
   For STREET addresses (e.g., "claimant_street", "loss_street"):
   - Look for: house number + street name + type (St, Ave, Rd, Blvd)
   - Common locations:
     * Dedicated "Address:" or "Street:" fields
     * Contact information blocks
     * Property description sections
     * "Location of loss:" fields
     * Headers with letterhead
   - Examples: "123 Main Street", "45 Oak Avenue", "2 Mid America Plaza, Suite 200"
   
   For CITY fields (e.g., "claimant_city", "loss_city"):
   - Look in: Address blocks, usually after street, before state/zip
   - May be on same line as street OR separate line
   - Check: "City:", "Municipality:", form fields
   
   For STATE/PROVINCE fields (e.g., "claimant_state", "loss_state"):
   - Look for: Full name OR 2-letter abbreviation (CA, NY, IL, ON, BC)
   - Common formats: "State:", "Province:", "State/Province:"
   - May be: Separate field OR combined with city (e.g., "Chicago, Illinois")
   
   For COUNTRY fields (e.g., "loss_country", "claimant_country"):
   - Look for: Full country name OR abbreviation (USA, US, Canada, Mexico)
   - Often in: International forms, letterhead, contact blocks
   - May be: Implied (if US address, country is "USA" or "United States")
   
   For ZIP/POSTAL CODE fields:
   - Look for: 5-digit (US), 5+4 (US extended), alphanumeric (Canada), etc.
   - Common locations: End of address, "Zip:", "Postal Code:"
   
   MULTI-LINE ADDRESSES:
   If address spans multiple lines, you may need to extract from:
   Line 1: Street
   Line 2: City, State Zip
   Line 3: Country (if present)

AMOUNTS (e.g., "claim_amount", "premium", "damages", "total_amount"):
   - Include currency symbols (Use ACTUAL document symbols, like $, €, £, ¥)
   - Preserve thousands separators and decimal places
   - Look for: Explicit labels, totals in tables, premium schedules
   - Common locations: "Amount:", "Total:", "Premium:", financial tables
   - Watch for: Labels like "Claim:", "Damages:", "Loss:", "Premium:", "Deductible:"

ORGANIZATION NAMES (e.g., "insured_name", "carrier_name", "adjuster_company"):
   - Extract complete legal/trade name
   - Look in: Letterhead, policy holder fields, signatures, contact blocks
   - Include: "Inc.", "LLC", "Ltd.", "Company", etc.
   - Common locations: Top of document, "Insured:", "Company:", signatures

DESCRIPTIONS (e.g., "incident_description", "diagnosis", "cause_of_loss"):
   - Extract relevant text - can be a sentence or paragraph
   - Look in: Narrative sections, description fields, comments
   - Stay within logical section for that key
   - Common locations: "Description:", "Details:", "Incident:", "Narrative:"
   - Do NOT extract entire document - be selective
   - Limit to 1-3 sentences unless more is clearly needed

YES/NO or CATEGORICAL values:
   - Extract exact term used in document
   - Look for: Checkboxes, radio buttons, dropdown values
   - If box is checked or marked, note that clearly

==================================
EXTRACTION PROCESS:
==================================

For EACH requested key:

STEP 1: IDENTIFY KEY TYPE
   - What type of information is this? (date, name, address, amount, etc.)
   - What are common labels or section headers for this type?

STEP 2: SCAN DOCUMENT THOROUGHLY
   - Look for explicit labels first ("Name:", "Address:", "Date:")
   - Check section headers matching key context
   - Scan tables and form fields
   - Check headers, footers, signatures
   - For addresses: Look in contact blocks, property descriptions, loss locations

STEP 3: EXTRACT VALUE
   - Extract EXACTLY as it appears (preserve format)
   - If found multiple places, use the MOST COMPLETE and RELEVANT value
   - For scattered info (addresses): COMBINE from multiple locations if needed

STEP 4: VERIFY
   - Does this value make sense for this key?
   - Is it the MOST RELEVANT value in the document?
   - For addresses: Did I check ALL possible locations?

If key not found after thorough search -> mark as null

==================================
EXAMPLE EXTRACTION:
==================================

Document excerpt:
"Date: May 27, 2023
Claim Number: CLM-2023-45678
Insured: Acme Corporation

LOSS DETAILS:
Location: 123 Main Street
City: Chicago
State: Illinois
Zip: 60601

Description: Water damage due to burst pipe on third floor"

For keys ["date_received", "claim_number", "insured_name", "loss_street", "loss_city", "loss_state", "loss_zip", "loss_description"]:

{{
  "date_received": "May 27, 2023",
  "claim_number": "CLM-2023-45678",
  "insured_name": "Acme Corporation",
  "loss_street": "123 Main Street",
  "loss_city": "Chicago",
  "loss_state": "Illinois",
  "loss_zip": "60601",
  "loss_description": "Water damage due to burst pipe on third floor"
}}

==================================

OUTPUT FORMAT (valid JSON only):
{{{{
  "extracted_data": {{{{
    "key1": "extracted value or null",
    "key2": "extracted value or null",
    ...
  }}}}
}}}}

DOCUMENT CONTENT:
{{document_content}}

Extract the requested keys NOW. Return ONLY valid JSON."""

    return prompt


# ============================================================================
# IMPROVEMENT 5: MULTI-PASS EXTRACTION FOR MISSING FIELDS
# ============================================================================

def extract_missing_fields_multipass(
    document_content: str,
    initial_extraction: Dict[str, Any],
    keys_to_extract: List[str],
    gpt_client,
    max_passes: int = 2
) -> Dict[str, Any]:
    """
    Perform additional extraction passes for fields that were null in initial pass.
    Uses more focused prompts for specific field types.
    
    Args:
        document_content: Original document text
        initial_extraction: Results from first extraction
        keys_to_extract: All keys that should be extracted
        gpt_client: GPT client
        max_passes: Maximum number of additional passes
    
    Returns:
        dict: Enhanced extraction results
    """
    enhanced = initial_extraction.copy()
    
    # Find null fields
    null_fields = [k for k in keys_to_extract if enhanced['extracted_data'].get(k) is None]
    
    if not null_fields:
        return enhanced  # All fields found!
    
    print(f"   Attempting multi-pass extraction for {len(null_fields)} missing fields...")
    
    # Group fields by type for focused extraction
    field_groups = {
        'addresses': [],
        'dates': [],
        'names': [],
        'numbers': [],
        'amounts': [],
        'other': []
    }
    
    for field in null_fields:
        field_lower = field.lower()
        if any(x in field_lower for x in ['street', 'city', 'state', 'province', 'zip', 'postal', 'country', 'address', 'location']):
            field_groups['addresses'].append(field)
        elif any(x in field_lower for x in ['date', 'dob', 'birth', 'effective', 'expiry', 'incident']):
            field_groups['dates'].append(field)
        elif any(x in field_lower for x in ['name', 'insured', 'claimant', 'patient']):
            field_groups['names'].append(field)
        elif any(x in field_lower for x in ['number', 'policy', 'claim', 'case', 'id', 'reference']):
            field_groups['numbers'].append(field)
        elif any(x in field_lower for x in ['amount', 'premium', 'limit', 'deductible', 'cost', 'price']):
            field_groups['amounts'].append(field)
        else:
            field_groups['other'].append(field)
    
    # Try focused extraction for each group
    for group_name, fields in field_groups.items():
        if not fields:
            continue
        
        print(f"      Focused extraction pass for {group_name}: {len(fields)} fields")
        
        focused_prompt = get_focused_extraction_prompt(document_content, fields, group_name)
        
        try:
            focused_extraction = extract_with_gpt(focused_prompt, gpt_client)
            
            # Update enhanced results with newly found fields
            for field in fields:
                if field in focused_extraction['extracted_data']:
                    value = focused_extraction['extracted_data'][field]
                    if value is not None:
                        enhanced['extracted_data'][field] = value
                        enhanced['extraction_notes'][field] = f'Found in multi-pass ({group_name})'
                        enhanced['confidence_scores'][field] = 0.7  # Lower confidence for multi-pass
                        print(f"Found {field}: {value}")
        
        except Exception as e:
            print(f"Error in focused extraction for {group_name}: {e}")
    
    return enhanced


def get_focused_extraction_prompt(document_content: str, fields: List[str], field_type: str) -> str:
    """
    Generate a highly focused prompt for specific field types.
    """
    
    type_instructions = {
        'addresses': """
FOCUSED TASK: Extract ADDRESS fields only.

These fields are CRITICAL and often scattered across the document:
- Street addresses: Look for house/building number + street name + type (St, Ave, Rd)
- Cities: Usually follow street address, may be on separate line
- States/Provinces: Look for full name OR 2-letter code (IL, CA, NY, ON)
- Countries: Look for full country name (United States, Mexico, Canada)
- ZIP/Postal codes: 5-digit numbers (US) or alphanumeric (Canada)

WHERE TO LOOK:
1. Letterhead and headers (company address often at top)
2. Contact information blocks
3. "Location of loss:" or "Property address:" sections
4. Signature blocks (claimant address often near signature)
5. Form fields labeled "Address:", "Location:", "Premises:"
6. After "Insured:", "Claimant:", "Property Owner:"

IMPORTANT: Addresses may span multiple lines. Combine information as needed.""",
        
        'dates': """
FOCUSED TASK: Extract DATE fields only.

Look for dates in ANY format:
- MM/DD/YYYY, DD-MM-YYYY, YYYY-MM-DD
- "January 15, 2024", "15 Jan 2024", "Jan 15, 2024"
- Timestamps, received dates, incident dates

WHERE TO LOOK:
1. Top of document (date received, document date)
2. Email headers and timestamps
3. Form fields labeled "Date:", "Effective:", "Incident Date:"
4. After "Occurred on:", "Date of Loss:", "Date Received:"
5. Near signatures (date signed)""",
        
        'names': """
FOCUSED TASK: Extract NAME fields only.

Look for person names, company names, organization names.

WHERE TO LOOK:
1. Letterhead (company names)
2. Form fields labeled "Name:", "Insured:", "Claimant:"
3. Signature blocks
4. "Regarding:", "Re:", "Subject:" lines
5. Contact information
6. After "Patient:", "Injured Party:", "Policyholder:"

Extract FULL names including titles, middle names, suffixes.""",
        
        'numbers': """
FOCUSED TASK: Extract POLICY/CLAIM/CASE NUMBERS only.

Look for alphanumeric identifiers.

WHERE TO LOOK:
1. Top of document, headers
2. Subject lines
3. Reference fields
4. After "Policy #:", "Claim No:", "Case ID:", "Reference:"
5. Barcode numbers, tracking numbers

Include ALL parts: prefixes, dashes, suffixes.""",
        
        'amounts': """
FOCUSED TASK: Extract MONETARY AMOUNTS only.

Look for currency values with symbols.

WHERE TO LOOK:
1. Financial tables
2. Premium schedules
3. After "Amount:", "Total:", "Premium:", "Limit:", "Deductible:"
4. Loss amounts, claim amounts, policy limits

Include currency symbols ($, €, £) and formatting."""
    }
    
    instruction = type_instructions.get(field_type, "Extract the following fields carefully:")
    fields_str = '", "'.join(fields)
    
    prompt = f"""{instruction}

FIELDS TO EXTRACT:
"{fields_str}"

DOCUMENT:
{document_content}

Return ONLY valid JSON:
{{{{
  "extracted_data": {{{{
    "field1": "value or null",
    "field2": "value or null",
    ...
  }}}}
}}}}"""
    
    return prompt


def extract_with_gpt(prompt: str, gpt_client) -> Dict:
    """
    Wrapper for GPT extraction with error handling.
    """
    # This should call your actual GPT extraction function
    # For now, returning placeholder
    # Replace with: return your_gpt_extraction_function(prompt, gpt_client)
    
    # Placeholder
    return {
        'extracted_data': {},
        'confidence_scores': {},
        'extraction_notes': {}
    }


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    """
    Example showing how improvements work together
    """
    
    # Test date normalization
    print("="*70)
    print("TESTING DATE NORMALIZATION")
    print("="*70)
    
    test_dates = [
        ("27-05-2023", "May 27, 2023"),
        ("05/27/2023", "2023-05-27"),
        ("20th of May 2023", "20.05.2023"),
        ("January 15, 2024", "15-01-2024")
    ]
    
    for date1, date2 in test_dates:
        match = dates_match(date1, date2)
        norm1 = normalize_date(date1)
        norm2 = normalize_date(date2)
        print(f"\n{date1} vs {date2}")
        print(f"  Normalized: {norm1} vs {norm2}")
        print(f"  Match: {match} " if match else f"  Match: {match} ✗")
    
    # Test fuzzy matching
    print("\n" + "="*70)
    print("TESTING FUZZY STRING MATCHING")
    print("="*70)
    
    test_strings = [
        ("4 Ever Life Insurance Company", "4 Ever Life Insurance Company / Global Atlantic Financial Group"),
        ("ABC Corporation", "ABC Corp"),
        ("G11687785-23", "G11687785"),
        ("Breach of contract", "breach of contract")
    ]
    
    for str1, str2 in test_strings:
        match = strings_fuzzy_match(str1, str2, threshold=0.85)
        similarity = fuzzy_string_similarity(str1, str2)
        print(f"\n'{str1}' vs")
        print(f"  '{str2}'")
        print(f"  Similarity: {similarity:.2f}")
        print(f"  Match (threshold=0.85): {match} " if match else f"  Match: {match} ✗")
    
    # Test improved comparison
    print("\n" + "="*70)
    print("TESTING IMPROVED COMPARISON")
    print("="*70)
    
    extracted = {
        'date_received': 'May 27, 2023',
        'policy_number': 'G11687785',
        'insured_name': '4 Ever Life Insurance Company / Global Atlantic',
        'loss_city': None
    }
    
    expected = {
        'date_received': '27-05-2023',
        'policy_number': 'G11687785-23',
        'insured_name': '4 Ever Life Insurance Company',
        'loss_city': 'Chicago'
    }
    
    comparison = compare_extracted_with_expected_IMPROVED(extracted, expected)
    
    print(f"\nComparison Results:")
    print(f"Matches: {comparison['matches']}/{comparison['total_expected']}")
    print(f"Accuracy: {comparison['accuracy']:.1f}%")
    print(f"\nDetails:")
    for key, details in comparison['details'].items():
        print(f"- {key}: {details['status']}")
        if 'match_method' in details:
            print(f"- Method: {details['match_method']}")
