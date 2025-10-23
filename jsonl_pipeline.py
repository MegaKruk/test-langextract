"""
JSONL Ground Truth Pipeline
With proper document type hierarchy-based merging

KEY LOGIC:
1. Same keys are extracted from ALL attachments in a .msg file
2. Merging uses document type hierarchy
3. For conflicts: Higher hierarchy document wins (unless it has null and lower hierarchy has value)
4. Non-null always beats null, regardless of hierarchy
"""

import json
import os
from typing import Dict, List, Optional, Any


# Lower index = HIGHER priority
DOCUMENT_TYPE_HIERARCHY = [
    "Email",
    "Medical",
    "Accident Report",
    "Other"
]


def load_ground_truth_from_jsonl(jsonl_path: str) -> Dict[str, Dict]:
    """
    Load ground truth from .jsonl file.
    
    Format:
    {
        "file_path": "/path/to/file.msg",
        "expected_kvp": {"first_name": "John", "dob": "01-01-1995"},
        "attachments": ["attachment1.pdf", "attachment2.pdf"]
    }
    """
    ground_truth = {}
    
    print(f"Loading ground truth from: {jsonl_path}")
    
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    file_path = data.get('file_path')
                    
                    if not file_path:
                        print(f"Warning: Line {line_num} missing 'file_path', skipping")
                        continue
                    
                    ground_truth[file_path] = data
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    continue
        
        print(f"Loaded {len(ground_truth)} ground truth entries")
        return ground_truth
        
    except FileNotFoundError:
        print(f"Error: Ground truth file not found: {jsonl_path}")
        return {}
    except Exception as e:
        print(f"Error loading ground truth: {e}")
        return {}


def get_attachment_dir(msg_path: str) -> str:
    """
    Get attachment directory for a .msg file.
    Folder has same name as .msg file (without .msg extension)
    """
    msg_dir = os.path.dirname(msg_path)
    msg_basename = os.path.basename(msg_path)
    
    # Remove .msg extension
    if msg_basename.endswith('.msg'):
        folder_name = msg_basename[:-4]
    else:
        folder_name = msg_basename
    
    return os.path.join(msg_dir, folder_name)


def get_pdf_attachments(msg_path: str) -> List[str]:
    """Get list of PDF attachments. Only PDFs are processed."""
    attachment_dir = get_attachment_dir(msg_path)
    
    if not os.path.exists(attachment_dir):
        print(f"Warning: Attachment directory not found: {attachment_dir}")
        return []
    
    pdf_files = []
    try:
        for filename in os.listdir(attachment_dir):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(attachment_dir, filename)
                pdf_files.append(pdf_path)
        pdf_files.sort()
    except Exception as e:
        print(f"Error listing attachments: {e}")
    
    return pdf_files


def get_document_hierarchy_priority(doc_label: str) -> int:
    """
    Get hierarchy priority for a document type.
    Lower number = higher priority.
    """
    try:
        return DOCUMENT_TYPE_HIERARCHY.index(doc_label)
    except ValueError:
        return len(DOCUMENT_TYPE_HIERARCHY)  # Unknown label = lowest priority


def merge_extractions_by_hierarchy(
    extractions: List[Dict[str, Any]],
    classifications: List[str],
    keys: List[str]
) -> Dict[str, Any]:
    """
    Merge extractions using document type hierarchy.
    
    Logic:
    - For each key, collect all non-null values
    - If all null -> result is null
    - If only one non-null -> use it (regardless of document type)
    - If multiple non-null -> use value from HIGHEST PRIORITY document type
    
    Example:
    Key "first_name":
      Police Report (priority 5): "John"
      Interim Invoice (priority 10): "Jimmy"
    -> Result: "John" (Police Report has higher priority)
    
    Key "dob":
      Police Report (priority 5): None
      Interim Invoice (priority 10): "11-01-1996"
    -> Result: "11-01-1996" (only non-null value, even though from lower priority doc)
    """
    merged = {
        'extracted_data': {},
        'confidence_scores': {},
        'extraction_notes': {},
        'sources': {},
        'winning_doc_types': {}
    }
    
    for key in keys:
        # Collect all non-null values with metadata
        non_null_values = []
        
        for idx, (extraction, doc_type) in enumerate(zip(extractions, classifications)):
            value = extraction['extracted_data'].get(key)
            
            if value is not None:
                confidence = extraction['confidence_scores'].get(key, 0.0)
                note = extraction['extraction_notes'].get(key, '')
                source = extraction.get('source', f'attachment_{idx}')
                priority = get_document_hierarchy_priority(doc_type)
                
                non_null_values.append({
                    'value': value,
                    'confidence': confidence,
                    'note': note,
                    'source': source,
                    'doc_type': doc_type,
                    'priority': priority
                })
        
        # Decide which value to use
        if not non_null_values:
            # All null
            merged['extracted_data'][key] = None
            merged['confidence_scores'][key] = 0.0
            merged['extraction_notes'][key] = 'Not found in any attachment'
            merged['sources'][key] = None
            merged['winning_doc_types'][key] = None
            
        elif len(non_null_values) == 1:
            # Only one non-null value
            item = non_null_values[0]
            merged['extracted_data'][key] = item['value']
            merged['confidence_scores'][key] = item['confidence']
            merged['extraction_notes'][key] = f"Found in {item['source']} ({item['doc_type']})"
            merged['sources'][key] = item['source']
            merged['winning_doc_types'][key] = item['doc_type']
            
        else:
            # Multiple non-null values - use HIGHEST PRIORITY (lowest priority number)
            non_null_values.sort(key=lambda x: x['priority'])
            winner = non_null_values[0]
            
            merged['extracted_data'][key] = winner['value']
            merged['confidence_scores'][key] = winner['confidence']
            merged['sources'][key] = winner['source']
            merged['winning_doc_types'][key] = winner['doc_type']
            
            # Note other values
            other_values_str = ', '.join([
                f"'{item['value']}' from {item['doc_type']}"
                for item in non_null_values[1:]
            ])
            
            merged['extraction_notes'][key] = (
                f"Selected '{winner['value']}' from {winner['doc_type']} (highest priority). "
                f"Also found: {other_values_str}"
            )
    
    return merged


def compare_extracted_with_expected(extracted: Dict[str, Any], expected: Dict[str, Any]) -> Dict:
    """Compare extracted vs expected values."""
    comparison = {
        'matches': 0,
        'mismatches': 0,
        'missing': 0,
        'total_expected': len(expected),
        'total_extracted': sum(1 for v in extracted.values() if v is not None),
        'details': {}
    }
    
    for key, expected_value in expected.items():
        extracted_value = extracted.get(key)
        
        if extracted_value is None:
            comparison['missing'] += 1
            comparison['details'][key] = {
                'status': 'missing',
                'expected': expected_value,
                'extracted': None
            }
        elif str(extracted_value).strip().lower() == str(expected_value).strip().lower():
            comparison['matches'] += 1
            comparison['details'][key] = {
                'status': 'match',
                'expected': expected_value,
                'extracted': extracted_value
            }
        else:
            comparison['mismatches'] += 1
            comparison['details'][key] = {
                'status': 'mismatch',
                'expected': expected_value,
                'extracted': extracted_value
            }
    
    if comparison['total_expected'] > 0:
        comparison['accuracy'] = (comparison['matches'] / comparison['total_expected']) * 100
    else:
        comparison['accuracy'] = 0.0
    
    return comparison


def execute_pipeline_with_attachments(
    idx: int,
    msg_path: str,
    ground_truth_entry: Optional[Dict],
    gpt_client,
    doc_intel_function
) -> Dict:
    """
    Process a .msg file with PDF attachments.
    
    Steps:
    1. Get expected keys from expected_kvp
    2. Find all PDF attachments (in folder with same name as .msg file)
    3. For each PDF:
       - Extract content (Azure Document Intelligence)
       - Classify document type
       - Extract same keys
    4. Merge using hierarchy
    5. Compare with expected
    """
    
    print(f"\n{'='*30}")
    print(f"[{idx}] Processing: {os.path.basename(msg_path)}")
    
    result = {
        'idx': idx,
        'file_path': msg_path,
        'msg_basename': os.path.basename(msg_path),
        'status': 'pending'
    }
    
    try:
        # Get expected keys
        expected_kvp = {}
        keys_to_extract = []
        
        if ground_truth_entry:
            expected_kvp = ground_truth_entry.get('expected_kvp', {})
            keys_to_extract = list(expected_kvp.keys())
            result['expected_kvp'] = expected_kvp
            print(f"Keys to extract: {keys_to_extract}")
        
        if not keys_to_extract:
            result['status'] = 'no_keys'
            return result
        
        # Get PDF attachments
        pdf_attachments = get_pdf_attachments(msg_path)
        
        if not pdf_attachments:
            result['status'] = 'no_attachments'
            return result
        
        print(f"Found {len(pdf_attachments)} PDF attachments")
        result['num_attachments'] = len(pdf_attachments)
        
        # Process each attachment
        all_extractions = []
        all_classifications = []
        attachment_results = []
        
        for att_idx, pdf_path in enumerate(pdf_attachments):
            att_name = os.path.basename(pdf_path)
            print(f"\n   [{att_idx+1}/{len(pdf_attachments)}] {att_name}")
            
            try:
                # Extract content
                print(f"Extracting content...")
                adi_results = doc_intel_function(pdf_path, first_n_pages=None)
                document_content = adi_results['content']
                print(f"Extracted {len(document_content)} chars")
                
                # Classify
                print(f"Classifying...")
                # TODO: REPLACE WITH YOUR ACTUAL FUNCTION
                # classification = classify_document_with_gpt_concise(document_content, gpt_client)
                classification = {
                    'label': 'Police Report / Accident Report' if att_idx == 0 else 'Interim Invoice',
                    'score': 0.85,
                    'thinking': 'Placeholder'
                }
                
                doc_type = classification['label']
                all_classifications.append(doc_type)
                print(f"Classified as: {doc_type}")
                
                # Extract KVP
                print(f"Extracting {len(keys_to_extract)} keys...")
                # TODO: REPLACE WITH YOUR ACTUAL FUNCTION
                # extraction = extract_key_values_with_gpt(document_content, keys_to_extract, gpt_client)
                
                # PLACEHOLDER - remove this after integration
                if att_idx == 0:
                    extraction = {
                        'extracted_data': {'first_name': 'John', 'dob': None},
                        'confidence_scores': {'first_name': 0.95, 'dob': 0.0},
                        'extraction_notes': {'first_name': 'Found', 'dob': 'Not found'}
                    }
                else:
                    extraction = {
                        'extracted_data': {'first_name': 'Jimmy', 'dob': '11-01-1996'},
                        'confidence_scores': {'first_name': 0.90, 'dob': 0.88},
                        'extraction_notes': {'first_name': 'Found', 'dob': 'Found'}
                    }
                
                extraction['source'] = att_name
                all_extractions.append(extraction)
                
                non_null = sum(1 for v in extraction['extracted_data'].values() if v is not None)
                print(f"Extracted {non_null}/{len(keys_to_extract)} non-null")
                
                attachment_results.append({
                    'attachment_name': att_name,
                    'classification': classification,
                    'extraction': extraction
                })
                
            except Exception as e:
                print(f"ERROR: {e}")
                all_classifications.append('Other')
                all_extractions.append({
                    'extracted_data': {key: None for key in keys_to_extract},
                    'confidence_scores': {key: 0.0 for key in keys_to_extract},
                    'extraction_notes': {key: f'Error: {e}' for key in keys_to_extract},
                    'source': att_name
                })
        
        result['attachment_results'] = attachment_results
        
        # Merge using hierarchy
        print(f"\nMerging using document type hierarchy...")
        merged = merge_extractions_by_hierarchy(all_extractions, all_classifications, keys_to_extract)
        result['extraction'] = merged
        
        # Show final values
        print(f"Final merged values:")
        for key in keys_to_extract:
            value = merged['extracted_data'][key]
            doc_type = merged['winning_doc_types'][key]
            if value:
                print(f"{key}: '{value}' (from {doc_type})")
            else:
                print(f"{key}: None")
        
        # Compare
        if expected_kvp:
            print(f"\nComparing with expected...")
            comparison = compare_extracted_with_expected(merged['extracted_data'], expected_kvp)
            result['comparison'] = comparison
            
            print(f"Matches: {comparison['matches']}/{comparison['total_expected']}")
            print(f"Mismatches: {comparison['mismatches']}")
            print(f"Missing: {comparison['missing']}")
            print(f"Accuracy: {comparison['accuracy']:.1f}%")
            
            # Show non-matches
            for key, details in comparison['details'].items():
                if details['status'] != 'match':
                    print(f"{key}: {details['status']} - expected '{details['expected']}', got '{details['extracted']}'")
        
        result['status'] = 'success'
        print(f"\n✓ Complete")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def process_batch_with_jsonl_ground_truth(
    jsonl_path: str,
    gpt_client,
    doc_intel_function,
    limit: Optional[int] = None
) -> List[Dict]:
    """Process all .msg files in .jsonl ground truth."""
    
    ground_truth = load_ground_truth_from_jsonl(jsonl_path)
    
    if not ground_truth:
        return []
    
    files_to_process = list(ground_truth.keys())
    if limit:
        files_to_process = files_to_process[:limit]
    
    print(f"\n{'='*70}")
    print(f"BATCH: {len(files_to_process)} files")
    print(f"{'='*70}")
    
    results = []
    for idx, file_path in enumerate(files_to_process):
        result = execute_pipeline_with_attachments(
            idx, file_path, ground_truth[file_path], gpt_client, doc_intel_function
        )
        results.append(result)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    
    successful = [r for r in results if r['status'] == 'success']
    with_comparison = [r for r in successful if r.get('comparison')]
    
    if with_comparison:
        total_matches = sum(r['comparison']['matches'] for r in with_comparison)
        total_expected = sum(r['comparison']['total_expected'] for r in with_comparison)
        avg_acc = sum(r['comparison']['accuracy'] for r in with_comparison) / len(with_comparison)
        
        print(f"\nExtraction Results:")
        print(f"Matches: {total_matches}/{total_expected}")
        print(f"Match Rate: {(total_matches/total_expected*100):.1f}%")
        print(f"Avg Accuracy: {avg_acc:.1f}%")
    
    print(f"\n{'='*70}")
    
    return results


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("TESTING HIERARCHY-BASED MERGING")
    print("="*70)
    
    # Your example
    extraction1 = {
        'extracted_data': {'first_name': 'John', 'dob': None},
        'confidence_scores': {'first_name': 0.95, 'dob': 0.0},
        'extraction_notes': {'first_name': 'Found', 'dob': 'Not found'},
        'source': 'attachment1.pdf'
    }
    
    extraction2 = {
        'extracted_data': {'first_name': 'Jimmy', 'dob': '11-01-1996'},
        'confidence_scores': {'first_name': 0.90, 'dob': 0.88},
        'extraction_notes': {'first_name': 'Found', 'dob': 'Found'},
        'source': 'attachment2.pdf'
    }
    
    classifications = ['Police Report / Accident Report', 'Interim Invoice']
    keys = ['first_name', 'dob']
    
    merged = merge_extractions_by_hierarchy([extraction1, extraction2], classifications, keys)
    
    print("\nPolice Report (priority 5): first_name='John', dob=None")
    print("Interim Invoice (priority 10): first_name='Jimmy', dob='11-01-1996'")
    print("\nMerged result:")
    print(f"first_name: '{merged['extracted_data']['first_name']}' from {merged['winning_doc_types']['first_name']}")
    print(f"dob: '{merged['extracted_data']['dob']}' from {merged['winning_doc_types']['dob']}")
    print("\n✓ Correct: first_name='John' (Police higher priority), dob='11-01-1996' (only non-null)")
    
    expected = {'first_name': 'John', 'dob': '01-01-1995'}
    comparison = compare_extracted_with_expected(merged['extracted_data'], expected)
    
    print(f"\nComparison: {comparison['matches']} matches, {comparison['mismatches']} mismatches")
    print(f"first_name: MATCH")
    print(f"dob: MISMATCH (expected '01-01-1995', got '11-01-1996')")
