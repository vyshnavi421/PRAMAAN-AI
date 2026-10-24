"""
PRAMAAN-AI Normalization and Fuzzy Comparison Utility
Avoids treating benign spelling, punctuation, or abbreviation variations as fraud or mismatches.
"""
import re
from typing import Tuple
from rapidfuzz import fuzz

def normalize_text(text: str) -> str:
    """
    Normalizes organizational names by lowercasing, stripping punctuation,
    and removing common corporate/educational legal suffixes.
    """
    if not text:
        return ""
    
    cleaned = text.lower()
    # Remove punctuation
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    
    # Common abbreviation replacements
    replacements = {
        r"\binst\b": "institute",
        r"\btech\b": "technology",
        r"\bengg\b": "engineering",
        r"\bcol\b": "college",
        r"\bdept\b": "department",
        r"\bgovt\b": "government",
        r"\bpvt\b": "private",
        r"\bltd\b": "limited",
        r"\bsoc\b": "society",
    }
    for pattern, replacement in replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned)
        
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def compare_names(name1: str, name2: str) -> Tuple[float, str]:
    """
    Compares two organizational names and returns (similarity_ratio, classification).
    Similarity is between 0.0 and 1.0.
    
    Classification:
    - EXACT_MATCH: 1.0
    - LEGITIMATE_VARIATION: >= 0.85 (e.g., abbreviation or minor punctuation difference)
    - POTENTIAL_VARIATION: 0.70 to 0.84 (requires human officer confirmation)
    - MISMATCH: < 0.70 (substantive discrepancy)
    """
    norm1 = normalize_text(name1)
    norm2 = normalize_text(name2)
    
    if not norm1 or not norm2:
        return 0.0, "EMPTY_INPUT"
        
    if name1.strip() == name2.strip():
        return 1.0, "EXACT_MATCH"

    if norm1 == norm2:
        return 1.0, "LEGITIMATE_VARIATION"
        
    # RapidFuzz token_sort_ratio handles word order differences
    ratio = fuzz.token_sort_ratio(norm1, norm2) / 100.0
    
    if ratio >= 0.85:
        return ratio, "LEGITIMATE_VARIATION"
    elif ratio >= 0.70:
        return ratio, "POTENTIAL_VARIATION"
    else:
        return ratio, "MISMATCH"
