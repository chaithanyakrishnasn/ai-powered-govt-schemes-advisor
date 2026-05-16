import re

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
}

def detect_language(text: str) -> str:
    """
    Detect language of input text. Returns ISO 639-1 code.
    Simple heuristic approach — no external API needed:
    - If text contains Devanagari chars (U+0900–U+097F) → "hi"
    - If text contains Kannada chars (U+0C80–U+0CFF) → "kn"
    - Otherwise → "en"
    Falls back to "en" if uncertain.
    """
    if not text:
        return "en"
        
    # Check for Devanagari block
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
        
    # Check for Kannada block
    if re.search(r'[\u0C80-\u0CFF]', text):
        return "kn"
        
    return "en"
