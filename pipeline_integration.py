"""
Complete Pipeline Integration Example
Ready to drop into your Azure Databricks project
"""

import json
import time
from typing import Dict, List, Optional


# ============================================================================
# PART 1: ENHANCED CLASSIFICATION FUNCTIONS
# ============================================================================

def classify_document_with_gpt_concise(document_content: str, gpt_client) -> dict:
    """
    Streamlined classification function - RECOMMENDED TO TRY FIRST
    
    Args:
        document_content: Text extracted from Azure Document Intelligence
        gpt_client: Your SecureGPT client object (with .request() method)
        
    Returns:
        dict with keys: label, score, thinking
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
                "content": [{"type": "text", "text": classification_prompt}]
            }
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        # YOUR SECURE GPT API CALL HERE
        gpt_response = gpt_client.request(
            json_data=classification_json_data,
            url=gpt_client.chat_completions_url
        )
        
        gpt_result = gpt_response['choices'][0]['message']['content']
        classification_dict = json.loads(gpt_result)
        
        return classification_dict
        
    except Exception as e:
        print(f"Error in classification: {e}")
        return {
            "label": "Other",
            "score": 0.0,
            "thinking": f"Error: {e}",
            "error": True
        }


def extract_key_values_with_gpt(document_content: str, keys_to_extract: List[str], gpt_client) -> dict:
    """
    Extract specific key-value pairs from document with high precision
    
    Args:
        document_content: Text extracted from Azure Document Intelligence
        keys_to_extract: List of keys to extract (e.g., ["claim_number", "loss_date"])
        gpt_client: Your SecureGPT client object
        
    Returns:
        dict with extracted_data, confidence_scores, extraction_notes
    """
    
    keys_list_formatted = "\n".join([f'   - "{key}"' for key in keys_to_extract])
    
    extraction_prompt = f"""You are a precise data extraction specialist. Extract SPECIFIC key-value pairs from the document.

EXTRACTION REQUIREMENTS:
1. Extract ONLY the exact keys requested - no additional keys
2. Extract the ACTUAL value from the document - do not infer, guess, or generate values
3. If a key is not found in the document, set its value to null
4. Values must be extracted verbatim from the document when possible
5. For dates, preserve the format as written
6. For names, include full names as they appear
7. For amounts/numbers, include currency symbols and formatting
8. Be extremely precise - accuracy is critical

KEYS TO EXTRACT:
{keys_list_formatted}

EXTRACTION GUIDELINES:

Dates (e.g., loss_date, incident_date):
- Extract exactly as formatted (MM/DD/YYYY, "January 15, 2024", etc.)
- Look for labels like "Date:", "Occurred:", "Effective:", "Incident Date:"

Numbers (e.g., claim_number, policy_number, case_number):
- Extract complete number including prefixes, suffixes, special characters
- Look for "Claim #:", "Policy No:", "Case:" labels

Names (e.g., claimant_name, insured_name):
- Extract full name as written
- Preserve titles (Mr., Dr.) if included
- Look for "Claimant:", "Insured:", "Name:" sections

Addresses (e.g., loss_location, insured_address):
- Extract complete address
- Include street, city, state, ZIP
- Preserve formatting

Amounts (e.g., claim_amount, premium, damages):
- Include currency symbol
- Preserve thousands separators and decimals
- Look for "Amount:", "Total:", "Premium:" labels

Descriptions (e.g., incident_description):
- Extract relevant text (sentence or paragraph)
- Stay within logical section
- Be selective, don't extract entire document

OUTPUT FORMAT (valid JSON):
{{
    "extracted_data": {{
        "key1": "extracted value or null",
        "key2": "extracted value or null"
    }},
    "confidence_scores": {{
        "key1": 0.95,
        "key2": 0.0
    }},
    "extraction_notes": {{
        "key1": "Found after 'Claim Number:' label",
        "key2": "Not found in document"
    }}
}}

CONFIDENCE SCORING:
- 1.0: Value found with clear label, exact match certain
- 0.8-0.9: Value found with reasonable certainty
- 0.5-0.7: Value inferred from context, some ambiguity
- 0.3-0.4: Low confidence, multiple possible values
- 0.0: Value not found (null)

CRITICAL RULES:
- NEVER invent values not in document
- NEVER use placeholder values
- Null is preferred over incorrect extraction
- Preserve original formatting
- Precision over recall

DOCUMENT CONTENT:
{document_content}"""
    
    extraction_json_data = {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": extraction_prompt}]
            }
        ],
        "response_format": {"type": "json_object"}
    }
    
    try:
        # YOUR SECURE GPT API CALL HERE
        gpt_response = gpt_client.request(
            json_data=extraction_json_data,
            url=gpt_client.chat_completions_url
        )
        
        gpt_result = gpt_response['choices'][0]['message']['content']
        extraction_dict = json.loads(gpt_result)
        
        # Validate all requested keys are present
        for key in keys_to_extract:
            if key not in extraction_dict.get('extracted_data', {}):
                extraction_dict.setdefault('extracted_data', {})[key] = None
                extraction_dict.setdefault('confidence_scores', {})[key] = 0.0
                extraction_dict.setdefault('extraction_notes', {})[key] = "Key not found"
        
        return extraction_dict
        
    except Exception as e:
        print(f"Error in extraction: {e}")
        return {
            "extracted_data": {key: None for key in keys_to_extract},
            "confidence_scores": {key: 0.0 for key in keys_to_extract},
            "extraction_notes": {key: f"Extraction failed: {e}" for key in keys_to_extract},
            "error": True
        }


# ============================================================================
# PART 2: DOCUMENT-TYPE SPECIFIC EXTRACTION SCHEMAS
# ============================================================================

EXTRACTION_SCHEMAS = {
    "Claim Notification / Acord / Notice of Loss / Loss Report / Incident Report": [
        "claim_number",
        "loss_date",
        "incident_date",
        "claimant_name",
        "policy_number",
        "loss_location",
        "incident_description",
        "estimated_damages",
        "cause_of_loss",
        "insured_name",
        "date_reported"
    ],
    
    "Medical Document": [
        "patient_name",
        "date_of_birth",
        "date_of_service",
        "physician_name",
        "diagnosis",
        "treatment",
        "medications",
        "icd_codes",
        "chief_complaint",
        "medical_record_number"
    ],
    
    "Policy Schedule / Slip / Endorsement / Binder / Certificate": [
        "policy_number",
        "insured_name",
        "effective_date",
        "expiration_date",
        "coverage_type",
        "coverage_limits",
        "premium",
        "deductible",
        "endorsement_number"
    ],
    
    "Police Report / Accident Report": [
        "report_number",
        "officer_name",
        "badge_number",
        "incident_date",
        "incident_time",
        "incident_location",
        "vehicle_info",
        "driver_name",
        "witness_names",
        "citation_issued"
    ],
    
    "Court Document / Legal Document": [
        "case_number",
        "court_name",
        "filing_date",
        "plaintiff",
        "defendant",
        "judge_name",
        "case_type",
        "docket_number"
    ],
    
    "Adjuster Report": [
        "adjuster_name",
        "claim_number",
        "inspection_date",
        "loss_date",
        "claimant_name",
        "damage_estimate",
        "liability_determination",
        "coverage_recommendation"
    ],
    
    "Interim Invoice": [
        "invoice_number",
        "invoice_date",
        "due_date",
        "total_amount",
        "vendor_name",
        "payment_terms",
        "invoice_period"
    ],
    
    "Email": [
        "sender",
        "recipient",
        "subject",
        "date_sent",
        "email_body"
    ]
}


# ============================================================================
# PART 3: ENHANCED PIPELINE INTEGRATION
# ============================================================================

def execute_enhanced_pipeline(idx: int, file_path: str, gpt_client, expected_label: Optional[str] = None) -> dict:
    """
    Complete enhanced pipeline with classification and extraction
    
    This integrates seamlessly with your existing code structure.
    
    Args:
        idx: Document index
        file_path: Path to PDF file
        gpt_client: Your SecureGPT client
        expected_label: Optional ground truth label for validation
        
    Returns:
        dict: Complete results including classification and extraction
    """
    
    print(f"\n{'='*50}")
    print(f"Processing document {idx}: {file_path}")
    print(f"{'='*50}")
    
    # Initialize result structure
    result = {
        'idx': idx,
        'file_path': file_path,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        # STEP 1: Azure Document Intelligence Extraction
        # (Using your existing function)
        print("\n[1/4] Extracting content with Azure Document Intelligence...")
        
        # Replace with your actual function call:
        # adi_results = call_doc_intel_extraction_results(file_path, first_n_pages=None)
        
        # For this example, assuming adi_results structure:
        # adi_results = {
        #     'content': 'extracted text...',
        #     'is_scanned': True/False,
        #     'pages': [...],
        #     'tables': [...]
        # }
        
        # Placeholder - replace with actual call
        adi_results = {'content': 'document content here', 'is_scanned': False}
        
        document_content = adi_results['content']
        result['is_scanned'] = adi_results.get('is_scanned', False)
        result['content_length'] = len(document_content)
        
        print(f"   Extracted {len(document_content)} characters")
        print(f"   Is scanned: {result['is_scanned']}")
        
        # STEP 2: Document Classification
        print("\n[2/4] Classifying document...")
        
        classification = classify_document_with_gpt_concise(document_content, gpt_client)
        
        predicted_label = classification['label']
        confidence = classification['score']
        thinking = classification.get('thinking', '')
        
        result['classification'] = {
            'predicted_label': predicted_label,
            'confidence': confidence,
            'thinking': thinking
        }
        
        print(f"   Predicted: {predicted_label}")
        print(f"   Confidence: {confidence:.2f}")
        
        # Validation if expected label provided
        if expected_label:
            is_correct = (predicted_label == expected_label)
            result['expected_label'] = expected_label
            result['classification']['is_correct'] = is_correct
            print(f"   Expected: {expected_label}")
            print(f"   {'✓ CORRECT' if is_correct else '✗ INCORRECT'}")
        
        # STEP 3: Key-Value Extraction (based on document type)
        print("\n[3/4] Extracting key-value pairs...")
        
        keys_to_extract = EXTRACTION_SCHEMAS.get(predicted_label, [])
        
        if keys_to_extract:
            print(f"   Extracting {len(keys_to_extract)} keys for document type: {predicted_label}")
            
            extraction_result = extract_key_values_with_gpt(
                document_content=document_content,
                keys_to_extract=keys_to_extract,
                gpt_client=gpt_client
            )
            
            result['extraction'] = extraction_result
            
            # Summary statistics
            non_null_count = sum(
                1 for v in extraction_result['extracted_data'].values() 
                if v is not None
            )
            high_conf_count = sum(
                1 for score in extraction_result['confidence_scores'].values()
                if score >= 0.8
            )
            
            print(f"   Extracted: {non_null_count}/{len(keys_to_extract)} keys")
            print(f"   High confidence (≥0.8): {high_conf_count}/{len(keys_to_extract)}")
            
            # Show sample extractions
            print("\n   Sample extracted values:")
            for key in list(keys_to_extract)[:3]:  # Show first 3
                value = extraction_result['extracted_data'].get(key)
                conf = extraction_result['confidence_scores'].get(key, 0)
                if value:
                    print(f"      {key}: {value} (conf: {conf:.2f})")
        else:
            print(f"   No extraction schema defined for: {predicted_label}")
            result['extraction'] = None
        
        # STEP 4: Final Status
        print("\n[4/4] Pipeline complete")
        result['status'] = 'success'
        result['error'] = None
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


# ============================================================================
# PART 4: BATCH PROCESSING & EVALUATION
# ============================================================================

def process_batch_with_evaluation(files_with_labels: List[tuple], gpt_client) -> dict:
    """
    Process multiple documents and calculate performance metrics
    
    Args:
        files_with_labels: List of (file_path, expected_label) tuples
        gpt_client: Your SecureGPT client
        
    Returns:
        dict: Comprehensive results and metrics
    """
    
    results = []
    classification_correct = 0
    classification_total = 0
    
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING: {len(files_with_labels)} documents")
    print(f"{'='*70}")
    
    for idx, (file_path, expected_label) in enumerate(files_with_labels):
        result = execute_enhanced_pipeline(idx, file_path, gpt_client, expected_label)
        results.append(result)
        
        # Track classification accuracy
        if result.get('status') == 'success' and expected_label:
            classification_total += 1
            if result['classification'].get('is_correct', False):
                classification_correct += 1
    
    # Calculate overall metrics
    overall_accuracy = (classification_correct / classification_total * 100 
                       if classification_total > 0 else 0)
    
    # Per-class metrics
    from collections import defaultdict
    class_metrics = defaultdict(lambda: {'correct': 0, 'total': 0, 'confidences': []})
    
    for result in results:
        if result.get('status') == 'success' and 'expected_label' in result:
            expected = result['expected_label']
            class_metrics[expected]['total'] += 1
            class_metrics[expected]['confidences'].append(result['classification']['confidence'])
            
            if result['classification'].get('is_correct', False):
                class_metrics[expected]['correct'] += 1
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*70}")
    print(f"\nOVERALL CLASSIFICATION ACCURACY: {overall_accuracy:.1f}% ({classification_correct}/{classification_total})")
    
    print(f"\nPER-CLASS PERFORMANCE:")
    print(f"{'='*70}")
    
    for label in sorted(class_metrics.keys()):
        metrics = class_metrics[label]
        accuracy = (metrics['correct'] / metrics['total'] * 100 
                   if metrics['total'] > 0 else 0)
        avg_confidence = (sum(metrics['confidences']) / len(metrics['confidences'])
                         if metrics['confidences'] else 0)
        
        print(f"\n{label}:")
        print(f"   Accuracy: {accuracy:.1f}% ({metrics['correct']}/{metrics['total']})")
        print(f"   Avg Confidence: {avg_confidence:.2f}")
    
    return {
        'results': results,
        'overall_accuracy': overall_accuracy,
        'classification_correct': classification_correct,
        'classification_total': classification_total,
        'class_metrics': dict(class_metrics)
    }


# ============================================================================
# PART 5: USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    """
    Example usage - adapt to your environment
    """
    
    # Initialize your SecureGPT client
    # gpt_client = YourSecureGPTClient(...)
    
    # Example: Single document
    print("\n" + "="*70)
    print("EXAMPLE 1: Single Document Processing")
    print("="*70)
    
    # result = execute_enhanced_pipeline(
    #     idx=1,
    #     file_path="/path/to/document.pdf",
    #     gpt_client=gpt_client,
    #     expected_label="Email"  # Optional, for validation
    # )
    
    # Example: Batch processing
    print("\n" + "="*70)
    print("EXAMPLE 2: Batch Processing with Evaluation")
    print("="*70)
    
    # validation_set = [
    #     ("/path/to/doc1.pdf", "Email"),
    #     ("/path/to/doc2.pdf", "Claim Notification / Acord / Notice of Loss / Loss Report / Incident Report"),
    #     ("/path/to/doc3.pdf", "Medical Document"),
    #     # ... more documents
    # ]
    
    # batch_results = process_batch_with_evaluation(validation_set, gpt_client)
    
    print("\nIntegration template ready!")
    print("Replace the placeholder gpt_client and file paths with your actual implementation.")
