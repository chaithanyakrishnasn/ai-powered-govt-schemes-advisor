import logging

from app.services.llm.gemini import GeminiClient
from app.services.multilingual.detector import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

class QueryTranslator:
    def __init__(self, gemini_client: GeminiClient) -> None:
        self.gemini_client = gemini_client

    async def to_english(
        self,
        text: str,
        source_language: str,
    ) -> str:
        """
        Translate query to English for retrieval.
        If source_language == "en": return text unchanged (no API call).
        Uses Gemini Flash with a minimal prompt.
        """
        if not text or source_language == "en":
            return text
            
        language_name = SUPPORTED_LANGUAGES.get(source_language, source_language)
        
        prompt = f"""Translate the following from {language_name} to English. 
Preserve formatting, bullet points, and technical terms (scheme names, ministry names, amounts like ₹6,000).
Do not translate proper nouns (PM Kisan, Aadhaar, Karnataka, etc.).
Return ONLY the translated text, no preamble.

Text to translate:
{text}"""

        try:
            # Using generate_text for simple string translation
            result = await self.gemini_client.generate_text(prompt)
            return result.strip()
        except Exception as e:
            logger.warning(f"Translation to English failed: {e}. Falling back to original.")
            return text

    async def localize_text(
        self,
        text: str,
        target_language: str,
    ) -> str:
        """
        Translate English text to target language.
        If target_language == "en": return text unchanged.
        """
        if not text or target_language == "en":
            return text
            
        language_name = SUPPORTED_LANGUAGES.get(target_language, target_language)
        
        prompt = f"""Translate the following from English to {language_name}. 
Preserve formatting, bullet points, and technical terms (scheme names, ministry names, amounts like ₹6,000).
Do not translate proper nouns (PM Kisan, Aadhaar, Karnataka, etc.).
Return ONLY the translated text, no preamble.

Text to translate:
{text}"""

        try:
            result = await self.gemini_client.generate_text(prompt)
            return result.strip()
        except Exception as e:
            logger.warning(f"Localization to {target_language} failed: {e}. Falling back to original.")
            return text
