from datetime import datetime
from typing import Optional, Literal, Set
import re


# Month names for text-based date parsing
MONTH_NAMES = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8,
    'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

# Common date format patterns (ordered by specificity)
FORMAT_PATTERNS = [
    # ISO formats with timezone and microseconds
    (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}[+-]\d{2}:\d{2}$', '%Y-%m-%d %H:%M:%S.%f%z'),
    (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3,6}[+-]\d{2}:\d{2}$', '%Y-%m-%d %H:%M:%S.%f%z'),
    (r'^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}\.\d{6}[+-]\d{2}:\d{2}$', '%Y.%m.%d %H:%M:%S.%f%z'),
    (r'^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}\.\d{3,6}[+-]\d{2}:\d{2}$', '%Y.%m.%d %H:%M:%S.%f%z'),
    
    # ISO formats with timezone (no microseconds)
    (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$', '%Y-%m-%d %H:%M:%S%z'),
    (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$', '%Y-%m-%dT%H:%M:%S%z'),
    (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$', '%Y-%m-%dT%H:%M:%S.%fZ'),
    (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', '%Y-%m-%dT%H:%M:%SZ'),
    
    # ISO formats (no timezone)
    (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$', '%Y-%m-%d %H:%M:%S.%f'),
    (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', '%Y-%m-%d %H:%M:%S'),
    (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$', '%Y-%m-%dT%H:%M:%S'),
    (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
    
    # Dotted formats
    (r'^\d{4}\.\d{2}\.\d{2}$', '%Y.%m.%d'),
    (r'^\d{2}\.\d{2}\.\d{4}$', None),  # Ambiguous, needs locale
    
    # Slash formats
    (r'^\d{2}/\d{2}/\d{4}$', None),  # Ambiguous, needs locale
    (r'^\d{1,2}/\d{1,2}/\d{4}$', None),  # Ambiguous, needs locale
    (r'^\d{4}/\d{2}/\d{2}$', '%Y/%m/%d'),
]


def _detect_text_date(date_string: str) -> Optional[str]:
    """Detect text-based date formats like '13 October 2024' or 'July 8th 2022'."""
    # Pattern: "13 October 2024" or "October 13, 2024"
    pattern1 = r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$'
    pattern2 = r'^([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$'
    
    match = re.match(pattern1, date_string)
    if match:
        month = match.group(2).lower()
        if month in MONTH_NAMES or len(month) > 3:
            return '%d %B %Y' if len(month) > 3 else '%d %b %Y'
    
    match = re.match(pattern2, date_string)
    if match:
        month = match.group(1).lower()
        if month in MONTH_NAMES or len(month) > 3:
            return '%B %d %Y' if len(month) > 3 else '%b %d %Y'
    
    return None


def _resolve_ambiguous_format(date_string: str, locale: str) -> str:
    """Resolve ambiguous date formats based on locale."""
    # For DD/MM/YYYY (UK/EU) vs MM/DD/YYYY (US)
    if '/' in date_string:
        if locale in ['UK', 'EU']:
            if re.match(r'^\d{2}/\d{2}/\d{4}$', date_string):
                return '%d/%m/%Y'
            elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_string):
                return '%d/%m/%Y'
        else:  # US
            if re.match(r'^\d{2}/\d{2}/\d{4}$', date_string):
                return '%m/%d/%Y'
            elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_string):
                return '%m/%d/%Y'
    
    # For DD.MM.YYYY (EU) vs MM.DD.YYYY (US)
    if '.' in date_string:
        if locale in ['UK', 'EU']:
            return '%d.%m.%Y'
        else:  # US
            return '%m.%d.%Y'
    
    raise ValueError(f"Cannot resolve ambiguous format for '{date_string}'")


def _validate_format(date_string: str, format_str: str) -> bool:
    """Validate that a format string can parse the date string."""
    try:
        datetime.strptime(date_string, format_str)
        return True
    except (ValueError, TypeError):
        return False


def _infer_format_from_parsing(date_string: str, locale: str) -> str:
    """Infer format by trying various combinations."""
    # Try common delimiters
    if '-' in date_string:
        delimiter = '-'
    elif '/' in date_string:
        delimiter = '/'
    elif '.' in date_string:
        delimiter = '.'
    else:
        raise ValueError("Unknown date format")
    
    parts = date_string.split(' ')
    date_part = parts[0]
    
    # Build possible formats
    possible_formats = []
    
    if locale in ['UK', 'EU']:
        possible_formats.extend([
            f'%d{delimiter}%m{delimiter}%Y',
            f'%d{delimiter}%m{delimiter}%y',
        ])
    else:  # US
        possible_formats.extend([
            f'%m{delimiter}%d{delimiter}%Y',
            f'%m{delimiter}%d{delimiter}%y',
        ])
    
    # Try each format
    for fmt in possible_formats:
        # Add time component if present
        if len(parts) > 1:
            time_part = parts[1]
            if '.' in time_part:
                full_fmt = f'{fmt} %H:%M:%S.%f'
                if '+' in date_string or time_part.endswith('Z'):
                    full_fmt += '%z'
            else:
                full_fmt = f'{fmt} %H:%M:%S'
                if '+' in date_string:
                    full_fmt += '%z'
        else:
            full_fmt = fmt
        
        if _validate_format(date_string, full_fmt):
            return full_fmt
    
    raise ValueError("Could not infer date format")


def detect_date_format(
    date_string: str,
    formats_set: Set[str],
    locale: Literal['UK', 'EU', 'US'] = 'US'
) -> str:
    """
    Detect the date format of a given date string and add it to the formats set.
    
    Args:
        date_string: String containing a date or datetime
        formats_set: Set to store all encountered date formats (modified in-place)
        locale: Locale hint for ambiguous formats ('UK', 'EU', or 'US')
               - UK/EU: day/month/year (e.g., 27/06/2023)
               - US: month/day/year (e.g., 06/27/2023)
    
    Returns:
        String representing the date format (e.g., '%Y-%m-%d %H:%M:%S')
    
    Raises:
        ValueError: If the date format cannot be determined
    
    Example:
        >>> formats = set()
        >>> detect_date_format('27/06/2023', formats, 'UK')
        '%d/%m/%Y'
        >>> detect_date_format('2023-06-27 15:37:38+00:00', formats, 'US')
        '%Y-%m-%d %H:%M:%S%z'
        >>> len(formats)
        2
    """
    date_string = date_string.strip()
    
    # Check for text-based dates (e.g., "13 October 2024", "July 8th 2022")
    text_format = _detect_text_date(date_string)
    if text_format:
        formats_set.add(text_format)
        return text_format
    
    # Try known patterns
    for pattern, format_str in FORMAT_PATTERNS:
        if re.match(pattern, date_string):
            if format_str is None:
                # Ambiguous format, needs locale
                format_str = _resolve_ambiguous_format(date_string, locale)
            
            # Verify the format works
            if _validate_format(date_string, format_str):
                formats_set.add(format_str)
                return format_str
    
    # Fallback: try to parse and infer
    try:
        inferred_format = _infer_format_from_parsing(date_string, locale)
        formats_set.add(inferred_format)
        return inferred_format
    except Exception as e:
        raise ValueError(f"Unable to detect date format for '{date_string}': {e}")


def normalize_date(
    date_string: str,
    known_formats: Set[str],
    desired_format: str,
    locale: Literal['UK', 'EU', 'US'] = 'US'
) -> str:
    """
    Normalize a date string to a desired format using known date formats.
    
    This function tries to parse the date string using known formats first,
    then falls back to detecting the format if needed.
    
    Args:
        date_string: String containing a date or datetime to normalize
        known_formats: Set of known date formats from first pass detection
        desired_format: Target date format (e.g., '%Y-%m-%d' or '%d/%m/%Y %H:%M:%S')
        locale: Locale hint for ambiguous formats ('UK', 'EU', or 'US')
    
    Returns:
        Normalized date string in the desired format
    
    Raises:
        ValueError: If the date cannot be parsed or normalized
    
    Example:
        >>> formats = {'%d/%m/%Y', '%Y-%m-%d %H:%M:%S%z'}
        >>> normalize_date('27/06/2023', formats, '%Y-%m-%d', 'UK')
        '2023-06-27'
        >>> normalize_date('2023-06-27 15:37:38+00:00', formats, '%d/%m/%Y %H:%M', 'US')
        '27/06/2023 15:37'
    """
    date_string = date_string.strip()
    parsed_date = None
    
    # Try parsing with known formats first
    for fmt in known_formats:
        try:
            parsed_date = datetime.strptime(date_string, fmt)
            break
        except (ValueError, TypeError):
            continue
    
    # If not parsed with known formats, try to detect the format
    if parsed_date is None:
        try:
            detected_format = detect_date_format(date_string, known_formats, locale)
            parsed_date = datetime.strptime(date_string, detected_format)
        except Exception as e:
            raise ValueError(f"Unable to parse date '{date_string}': {e}")
    
    # Format the date to desired format
    try:
        normalized = parsed_date.strftime(desired_format)
        return normalized
    except Exception as e:
        raise ValueError(f"Unable to format date to '{desired_format}': {e}")


# Example usage
if __name__ == '__main__':
    # First pass: detect all formats
    test_dates = [
        ('27/06/2023', 'UK'),
        ('2023-06-27 15:37:38+00:00', 'US'),
        ('2023.06.29 17:18:03.000013+00:00', 'US'),
        ('13 October 2024', 'UK'),
        ('July 8th 2022', 'US'),
        ('2023-06-27', 'US'),
        ('06/27/2023', 'US'),
        ('15/08/2023', 'EU'),
    ]
    
    # Initialize the formats set
    all_formats = set()
    
    print("FIRST PASS - Detecting date formats:")
    print("-" * 30)
    
    for date_str, locale in test_dates:
        try:
            format_str = detect_date_format(date_str, all_formats, locale)
            print(f"Date: {date_str:40} | Format: {format_str}")
        except ValueError as e:
            print(f"Date: {date_str:40} | Error: {e}")
    
    print("\n" + "=" * 30)
    print(f"Total unique formats encountered: {len(all_formats)}")
    print("\nAll detected formats:")
    for fmt in sorted(all_formats):
        print(f"  - {fmt}")
    
    print("\n" + "=" * 30)
    print("SECOND PASS - Normalizing dates to '%Y-%m-%d %H:%M:%S':")
    print("-" * 30)
    
    # Second pass: normalize dates
    desired_format = '%Y-%m-%d %H:%M:%S'
    
    for date_str, locale in test_dates:
        try:
            normalized = normalize_date(date_str, all_formats, desired_format, locale)
            print(f"Original: {date_str:40} | Normalized: {normalized}")
        except ValueError as e:
            print(f"Original: {date_str:40} | Error: {e}")
    
    print("\n" + "=" * 30)
    print("Normalizing to UK format '%d/%m/%Y':")
    print("-" * 30)
    
    uk_format = '%d/%m/%Y'
    for date_str, locale in test_dates[:4]:
        try:
            normalized = normalize_date(date_str, all_formats, uk_format, locale)
            print(f"Original: {date_str:40} | UK Format: {normalized}")
        except ValueError as e:
            print(f"Original: {date_str:40} | Error: {e}")
