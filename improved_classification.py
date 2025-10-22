import os

# Document labels from your code
DOCUMENT_LABELS_LEGACY_UPDATED = [
    "Email",
    "Claim Notification / Acord / Notice of Loss / Loss Report / Incident Report",
    "Notice of Claim / Complaint / Claim Letter / Acknowledgement",
    "Court Document / Legal Document",
    "Medical Document",
    "Police Report / Accident Report",
    "Bordereau",
    "Policy Schedule / Slip / Endorsement / Binder / Certificate",
    "Claimant List",
    "Adjuster Report",
    "Interim Invoice",
    "Other"
]


def classify_document_with_gpt_improved(document_content: str) -> dict:
    """
    Enhanced document classification using GPT with improved prompting strategy.
    
    This function uses a more detailed prompt with:
    - Clear structural markers and formatting cues
    - Enhanced class descriptions with key identifiers
    - Better reasoning guidance
    - Multi-stage classification approach
    
    Args:
        document_content: The extracted text content from Azure Document Intelligence
        
    Returns:
        dict: Classification result with label, score, and thinking process
    """
    
    # Enhanced label descriptions with discriminative features
    label_descriptions = {
        "Email": {
            "description": "Email correspondence with standard email structure",
            "key_markers": ["From:", "To:", "Subject:", "Sent:", "CC:", "email addresses (e.g., user@domain.com)"],
            "typical_length": "Short to medium (1-3 pages)",
            "structural_cues": "Headers with sender/recipient info at top, conversational tone",
            "vocabulary": ["forwarded", "attached", "please find", "regards", "dear", "hi", "hello"]
        },
        "Claim Notification / Acord / Notice of Loss / Loss Report / Incident Report": {
            "description": "Formal notification of an insurance claim, loss, or incident",
            "key_markers": ["claim number", "loss date", "incident date", "claimant name", "policy number", "ACORD form"],
            "typical_length": "Medium (2-6 pages)",
            "structural_cues": "Form-like structure with fields and values, formal reporting language",
            "vocabulary": ["notifying", "occurred", "damages", "injured party", "circumstances", "date of loss", "claim filing", "incident report", "loss notification"]
        },
        "Notice of Claim / Complaint / Claim Letter / Acknowledgement": {
            "description": "Legal notice or complaint about a claim, or acknowledgement of receipt",
            "key_markers": ["re:", "complaint", "claim", "acknowledgement", "plaintiff", "defendant", "formal salutation"],
            "typical_length": "Short to medium (1-4 pages)",
            "structural_cues": "Letter format with date, addresses, formal opening/closing",
            "vocabulary": ["hereby", "acknowledge receipt", "complaint filed", "grievance", "dispute", "legal action", "claim acknowledgement"]
        },
        "Court Document / Legal Document": {
            "description": "Official court filings, legal briefs, motions, or judgments",
            "key_markers": ["case number", "court name", "plaintiff v. defendant", "filed", "docket", "honorable", "motion", "order"],
            "typical_length": "Medium to long (3-20+ pages)",
            "structural_cues": "Formal legal structure with numbered paragraphs, case captions, legal citations",
            "vocabulary": ["wherefore", "pursuant to", "jurisdiction", "affidavit", "testimony", "exhibits", "petitioner", "respondent", "ruling"]
        },
        "Medical Document": {
            "description": "Medical records, doctor's notes, diagnosis reports, treatment plans",
            "key_markers": ["patient name", "date of birth", "diagnosis", "treatment", "physician", "vital signs", "medications", "ICD codes"],
            "typical_length": "Variable (1-10 pages)",
            "structural_cues": "Medical terminology throughout, clinical observations, prescribed treatments",
            "vocabulary": ["diagnosis", "prognosis", "symptoms", "examination", "prescription", "chief complaint", "medical history", "treatment plan", "physician notes"]
        },
        "Police Report / Accident Report": {
            "description": "Official police or traffic accident reports",
            "key_markers": ["report number", "officer name", "badge number", "incident location", "date/time of incident", "vehicle information", "witness statements"],
            "typical_length": "Medium (2-8 pages)",
            "structural_cues": "Official form format, narrative section, diagram or sketch, officer signature",
            "vocabulary": ["investigating officer", "accident scene", "vehicle", "collision", "citation", "witness", "statement", "traffic violation", "crash"]
        },
        "Bordereau": {
            "description": "Insurance industry document listing individual risks or claims in tabular format",
            "key_markers": ["policy numbers in rows", "premium amounts", "risk details", "column headers", "totals/subtotals"],
            "typical_length": "Medium to long (often multi-page tables)",
            "structural_cues": "Primarily tabular data with multiple entries, summary rows, often spreadsheet-like",
            "vocabulary": ["premium", "coverage", "risk", "insured", "policy period", "endorsement", "aggregate", "bordereau"]
        },
        "Policy Schedule / Slip / Endorsement / Binder / Certificate": {
            "description": "Insurance policy documents showing coverage details, terms, and conditions",
            "key_markers": ["policy number", "coverage limits", "effective dates", "premium", "insured name", "endorsement number", "certificate number"],
            "typical_length": "Variable (1-20 pages)",
            "structural_cues": "Structured sections for coverage types, limits, exclusions, often includes tables",
            "vocabulary": ["coverage", "deductible", "limits", "exclusions", "insured", "insurer", "endorsement", "binder", "certificate holder", "effective period"]
        },
        "Claimant List": {
            "description": "List or roster of claimants, typically in table or list format",
            "key_markers": ["claimant names", "claim numbers", "amounts", "list structure", "multiple entries"],
            "typical_length": "Short to medium (1-5 pages)",
            "structural_cues": "List or table format with consistent entries, column headers if tabular",
            "vocabulary": ["claimant", "claim amount", "status", "total", "list of claims"]
        },
        "Adjuster Report": {
            "description": "Insurance adjuster's assessment and findings regarding a claim",
            "key_markers": ["adjuster name", "claim investigation", "findings", "recommendations", "estimate", "inspection date"],
            "typical_length": "Medium (3-10 pages)",
            "structural_cues": "Report format with sections (summary, investigation, findings, recommendations)",
            "vocabulary": ["investigation", "inspection", "estimate", "damage assessment", "adjuster", "findings", "recommendations", "liability", "coverage determination"]
        },
        "Interim Invoice": {
            "description": "Partial or interim billing statement for services or payments",
            "key_markers": ["invoice number", "invoice date", "amount due", "line items", "payment terms", "interim"],
            "typical_length": "Short (1-3 pages)",
            "structural_cues": "Invoice format with itemized charges, totals, payment information",
            "vocabulary": ["invoice", "billing", "payment", "interim", "balance", "amount due", "line items", "subtotal"]
        },
        "Other": {
            "description": "Documents that don't fit clearly into any above category",
            "key_markers": ["Mixed content that doesn't match any specific category"],
            "typical_length": "Variable",
            "structural_cues": "No clear pattern matching other categories",
            "vocabulary": ["General business or administrative documents"]
        }
    }
    
    # Build comprehensive classification prompt
    classification_prompt = f"""You are an expert document classifier for insurance industry documents. Your task is to classify the provided document into ONE of the following categories.

CLASSIFICATION INSTRUCTIONS:
1. Read the document content carefully, paying attention to structural features (headers, tables, forms) and keywords.
2. Consider BOTH the content AND format/structure when classifying.
3. Match against the descriptions below - choose the category that BEST fits the document.
4. Your label MUST be EXACTLY as written from the list (do NOT invent new labels or use synonyms).
5. If the document contains email headers (From:, To:, Subject:, Sent:), it is likely an Email.
6. When classifying, pay special attention to document structure - tables suggest Bordereau or Claimant List; forms suggest reports or policies; letters suggest correspondence.
7. Use 'Other' ONLY if none of the above labels fit after careful consideration (use sparingly - less than 5% of cases).

DOCUMENT CATEGORIES AND THEIR CHARACTERISTICS:

"""
    
    # Add detailed category descriptions
    for i, label in enumerate(DOCUMENT_LABELS_LEGACY_UPDATED, 1):
        desc = label_descriptions.get(label, {})
        classification_prompt += f"""
{i}. {label}
   Description: {desc.get('description', 'N/A')}
   Key Markers: {', '.join(desc.get('key_markers', ['N/A']))}
   Typical Length: {desc.get('typical_length', 'N/A')}
   Structural Cues: {desc.get('structural_cues', 'N/A')}
   Common Vocabulary: {', '.join(desc.get('vocabulary', ['N/A']))}
"""
    
    classification_prompt += """

CLASSIFICATION PROCESS:
First, in your thinking, identify:
- What structural features are present (email headers, tables, formal letter format, legal formatting, etc.)?
- What key markers or vocabulary appear in the document?
- What is the apparent purpose/function of this document?
- Which category's description most closely matches these observations?

Then, output the classification result as a JSON object with the following structure:
{
    "thinking": "str, your detailed reasoning about structural features, keywords found, and why this category fits best",
    "label": "str, MUST be EXACTLY one of the category names listed above",
    "score": "float between 0 and 1, your confidence in this classification"
}

CRITICAL RULES:
- The 'label' field MUST exactly match one of the {len(DOCUMENT_LABELS_LEGACY_UPDATED)} category names above (case-sensitive).
- Do NOT use synonyms or variations. Use the exact label text.
- Provide your reasoning in 'thinking' before deciding on the label.
- When in doubt between two categories, choose the one with more matching key markers.

DOCUMENT CONTENT:
{document_content}"""
    
    # Prepare the API call data
    classification_json_data = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": classification_prompt}
                ]
            }
        ],
        "response_format": {"type": "json_object"}
    }
    
    # Note: Replace with your actual SecureGPT implementation
    # This is placeholder for the actual API call structure from your code
    try:
        # Assuming you have gpt.request function as shown in screenshot
        # gpt_classification_response = gpt.request(
        #     json_data=classification_json_data, 
        #     url=gpt.chat_completions_url
        # )
        
        # For now, return structure - replace with actual API call
        # gpt_classification_result = gpt_classification_response['choices'][0]['message']['content']
        
        # Parse and return
        # import json
        # classification_dict = json.loads(gpt_classification_result)
        # return classification_dict
        
        return {
            "prompt": classification_prompt,
            "json_data": classification_json_data,
            "note": "Replace with actual gpt.request() call"
        }
        
    except Exception as e:
        print(f"Error in classification: {e}")
        return {
            "error": str(e),
            "label": "Other",
            "score": 0.0
        }


# Alternative simplified version with more focused prompt
def classify_document_with_gpt_concise(document_content: str) -> dict:
    """
    Concise version focusing on discriminative features only.
    Sometimes less is more - this version may perform better by reducing prompt complexity.
    """
    
    classification_prompt = f"""Classify this document into ONE category. Output ONLY valid JSON.

CATEGORIES (use exact label text):
1. "Email" - Has From:/To:/Subject: headers, email addresses, conversational tone
2. "Claim Notification / Acord / Notice of Loss / Loss Report / Incident Report" - Formal claim/loss notification with claim numbers, incident details, ACORD forms
3. "Notice of Claim / Complaint / Claim Letter / Acknowledgement" - Legal notice, complaint, or acknowledgement letter about a claim
4. "Court Document / Legal Document" - Court filings with case numbers, legal citations, formal legal language (plaintiff, defendant, motion, order)
5. "Medical Document" - Medical records with diagnoses, treatments, patient info, clinical terminology
6. "Police Report / Accident Report" - Official police/accident report with report number, officer info, incident details
7. "Bordereau" - Tabular listing of multiple insurance risks/claims with policy numbers and premiums in rows
8. "Policy Schedule / Slip / Endorsement / Binder / Certificate" - Insurance policy showing coverage details, limits, terms, endorsements
9. "Claimant List" - List/table of multiple claimants with names and claim amounts
10. "Adjuster Report" - Claim investigation report by adjuster with findings and recommendations
11. "Interim Invoice" - Billing statement with invoice number, line items, amounts due
12. "Other" - Doesn't fit above categories (use rarely)

INSTRUCTIONS:
- Identify key structural markers (email headers, tables, forms, legal format)
- Match vocabulary and purpose to categories above
- Choose BEST fit category using EXACT label text
- "Other" only if truly no match (<5% of cases)

OUTPUT FORMAT (valid JSON only):
{{
    "thinking": "Brief analysis of key features observed",
    "label": "Exact category label from list",
    "score": 0.95
}}

DOCUMENT:
{document_content}"""
    
    classification_json_data = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": classification_prompt}
                ]
            }
        ],
        "response_format": {"type": "json_object"}
    }
    
    return {
        "prompt": classification_prompt,
        "json_data": classification_json_data,
        "note": "Replace with actual gpt.request() call"
    }


def extract_key_values_with_gpt(document_content: str, keys_to_extract: list[str]) -> dict:
    """
    Extract specific key-value pairs from document content using GPT.
    
    This function precisely extracts requested keys from unstructured document text.
    Designed for high accuracy (90%+ target) through careful prompting.
    
    Args:
        document_content: The extracted text content from Azure Document Intelligence
        keys_to_extract: List of key names to extract (e.g., ["claim_number", "loss_date", "claimant_name"])
        
    Returns:
        dict: Extracted key-value pairs with metadata
            {
                "extracted_data": {
                    "key1": "value1",
                    "key2": "value2",
                    ...
                },
                "confidence_scores": {
                    "key1": 0.95,
                    "key2": 0.80,
                    ...
                },
                "extraction_notes": {
                    "key1": "Found in section X",
                    "key2": "Not found in document",
                    ...
                }
            }
    """
    
    # Build key descriptions dynamically
    keys_list_formatted = "\n".join([f'   - "{key}"' for key in keys_to_extract])
    
    extraction_prompt = f"""You are a precise data extraction specialist. Your task is to extract SPECIFIC key-value pairs from the provided document.

EXTRACTION REQUIREMENTS:
1. Extract ONLY the exact keys requested - no additional keys
2. Extract the ACTUAL value from the document - do not infer, guess, or generate values
3. If a key is not found in the document, set its value to null
4. Values must be extracted verbatim from the document when possible
5. For dates, preserve the format as written in the document
6. For names, include full names as they appear
7. For amounts/numbers, include currency symbols and formatting as written
8. Be extremely precise - accuracy is critical

KEYS TO EXTRACT:
{keys_list_formatted}

EXTRACTION GUIDELINES BY KEY TYPE:

For dates (e.g., "loss_date", "incident_date", "policy_effective_date"):
- Extract exactly as formatted in document (MM/DD/YYYY, DD-MM-YYYY, "January 15, 2024", etc.)
- If only partial date available, extract what's present
- Look for labels like "Date:", "Occurred:", "Effective:", "Incident Date:", etc.

For identifying numbers (e.g., "claim_number", "policy_number", "case_number", "report_number"):
- Extract the complete number/code including any prefixes, suffixes, or special characters
- Look for explicit labels or nearby context (e.g., "Claim #:", "Policy No:", "Case:", etc.)
- Include dashes, spaces, or other formatting as written

For names (e.g., "claimant_name", "insured_name", "policyholder", "patient_name"):
- Extract full name as written (First Last, Last, First, etc.)
- Preserve titles if included (Mr., Dr., etc.)
- Look for section headers like "Claimant:", "Insured:", "Name:", etc.

For addresses (e.g., "loss_location", "insured_address", "accident_location"):
- Extract complete address as written
- Include street, city, state, ZIP if present
- Preserve formatting (multiline, comma-separated, etc.)

For amounts (e.g., "claim_amount", "premium", "damages", "total_amount"):
- Include currency symbol ($, €, etc.)
- Preserve thousands separators and decimal places
- Look for labels like "Amount:", "Total:", "Premium:", "Damages:", etc.

For descriptions (e.g., "incident_description", "diagnosis", "cause_of_loss"):
- Extract relevant text - can be a sentence or paragraph
- Stay within the logical section for that key
- Do not extract entire document - be selective

For yes/no or categorical values:
- Extract the exact term used in document
- If box is checked or marked, note that clearly

EXTRACTION PROCESS:
1. Scan document for each requested key
2. Look for explicit labels, section headers, or contextual clues
3. Extract the value exactly as it appears
4. Note confidence level and location/context where found
5. If key not found after thorough search, mark as null

OUTPUT FORMAT (valid JSON only):
{{
    "extracted_data": {{
        "key1": "extracted value or null",
        "key2": "extracted value or null",
        ...
    }},
    "confidence_scores": {{
        "key1": 0.95,
        "key2": 0.0,
        ...
    }},
    "extraction_notes": {{
        "key1": "Found after 'Claim Number:' label in header section",
        "key2": "Not found in document",
        ...
    }}
}}

CONFIDENCE SCORING:
- 1.0: Value found with clear label/context, exact match certain
- 0.8-0.9: Value found with reasonable certainty, may lack explicit label
- 0.5-0.7: Value inferred from context, some ambiguity
- 0.3-0.4: Low confidence, multiple possible values
- 0.0: Value not found in document (null)

CRITICAL RULES:
- NEVER invent or generate values not in the document
- NEVER use placeholder values
- If unsure between multiple values, choose most likely and reduce confidence score
- Null is acceptable and preferred over incorrect extraction
- Preserve original formatting and wording from document
- Focus on precision over recall - better to return null than wrong value

DOCUMENT CONTENT:
{document_content}"""
    
    extraction_json_data = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": extraction_prompt}
                ]
            }
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        # Placeholder for actual API call
        # Replace with your SecureGPT implementation:
        # gpt_extraction_response = gpt.request(
        #     json_data=extraction_json_data,
        #     url=gpt.chat_completions_url
        # )
        # gpt_extraction_result = gpt_extraction_response['choices'][0]['message']['content']
        # 
        # import json
        # extraction_dict = json.loads(gpt_extraction_result)
        # 
        # # Validate all requested keys are present
        # for key in keys_to_extract:
        #     if key not in extraction_dict.get('extracted_data', {}):
        #         extraction_dict['extracted_data'][key] = null
        #         extraction_dict['confidence_scores'][key] = 0.0
        #         extraction_dict['extraction_notes'][key] = "Key not found in extraction"
        # 
        # return extraction_dict
        
        return {
            "prompt": extraction_prompt,
            "json_data": extraction_json_data,
            "note": "Replace with actual gpt.request() call"
        }
        
    except Exception as e:
        print(f"Error in key-value extraction: {e}")
        # Return structure with nulls for all keys
        return {
            "error": str(e),
            "extracted_data": {key: None for key in keys_to_extract},
            "confidence_scores": {key: 0.0 for key in keys_to_extract},
            "extraction_notes": {key: f"Extraction failed: {e}" for key in keys_to_extract}
        }


# Example usage
if __name__ == "__main__":
    # Example document content
    sample_content = """
    From: john.doe@example.com
    To: claims@insurance.com
    Subject: Claim Notification - Policy #ABC123
    Date: October 20, 2025
    
    Dear Claims Department,
    
    I am writing to notify you of a loss that occurred on October 15, 2025.
    
    Claim Details:
    - Policy Number: ABC123
    - Loss Date: 10/15/2025
    - Claimant Name: John Doe
    - Loss Location: 123 Main Street, Springfield, IL 62701
    - Estimated Damages: $5,250.00
    - Description: Water damage from burst pipe in basement
    
    Please contact me at your earliest convenience.
    
    Sincerely,
    John Doe
    """
    
    # Test classification
    print("=== CLASSIFICATION TEST ===")
    result1 = classify_document_with_gpt_improved(sample_content)
    print(f"Detailed version prompt length: {len(result1['prompt'])} chars")
    
    result2 = classify_document_with_gpt_concise(sample_content)
    print(f"Concise version prompt length: {len(result2['prompt'])} chars")
    
    # Test key-value extraction
    print("\n=== KEY-VALUE EXTRACTION TEST ===")
    keys = ["policy_number", "loss_date", "claimant_name", "loss_location", "estimated_damages"]
    result3 = extract_key_values_with_gpt(sample_content, keys)
    print(f"Extraction prompt length: {len(result3['prompt'])} chars")
    print(f"\nKeys to extract: {keys}")
