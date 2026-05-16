import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.multilingual.detector import detect_language
from app.services.multilingual.translator import QueryTranslator


def test_detect_hindi():
    assert detect_language("किसानों के लिए योजनाएं") == "hi"

def test_detect_kannada():
    assert detect_language("ರೈತರಿಗೆ ಯೋಜನೆಗಳು") == "kn"

def test_detect_english():
    assert detect_language("schemes for farmers") == "en"

def test_detect_mixed_hinglish():
    # Hinglish (Latin + Devanagari) → detect as "hi" if any Devanagari present
    assert detect_language("PM kisan के लिए apply कैसे करें") == "hi"

def test_detect_empty():
    assert detect_language("") == "en"

@pytest.fixture
def mock_gemini():
    client = MagicMock()
    client.generate_text = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_english_passthrough(mock_gemini):
    # language=en → no Gemini call, returns original
    translator = QueryTranslator(mock_gemini)
    result = await translator.to_english("schemes for farmers", "en")
    assert result == "schemes for farmers"
    mock_gemini.generate_text.assert_not_called()

@pytest.mark.asyncio
async def test_translation_called_for_hindi(mock_gemini):
    mock_gemini.generate_text.return_value = "schemes for farmers"
    translator = QueryTranslator(mock_gemini)
    result = await translator.to_english("किसानों के लिए योजनाएं", "hi")
    
    assert result == "schemes for farmers"
    mock_gemini.generate_text.assert_called_once()
    call_args = mock_gemini.generate_text.call_args[0][0]
    assert "Translate the following from Hindi to English" in call_args
    assert "किसानों के लिए योजनाएं" in call_args

@pytest.mark.asyncio
async def test_translation_called_for_kannada(mock_gemini):
    mock_gemini.generate_text.return_value = "schemes for farmers"
    translator = QueryTranslator(mock_gemini)
    result = await translator.to_english("ರೈತರಿಗೆ ಯೋಜನೆಗಳು", "kn")
    
    assert result == "schemes for farmers"
    mock_gemini.generate_text.assert_called_once()
    call_args = mock_gemini.generate_text.call_args[0][0]
    assert "Translate the following from Kannada to English" in call_args

@pytest.mark.asyncio
async def test_localize_text_english_passthrough(mock_gemini):
    translator = QueryTranslator(mock_gemini)
    result = await translator.localize_text("schemes for farmers", "en")
    assert result == "schemes for farmers"
    mock_gemini.generate_text.assert_not_called()

@pytest.mark.asyncio
async def test_localize_text_hindi(mock_gemini):
    mock_gemini.generate_text.return_value = "किसानों के लिए योजनाएं"
    translator = QueryTranslator(mock_gemini)
    result = await translator.localize_text("schemes for farmers", "hi")
    
    assert result == "किसानों के लिए योजनाएं"
    mock_gemini.generate_text.assert_called_once()

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("RUN_LIVE_EVAL"), reason="Live eval disabled")
async def test_live_hindi_translation():
    from app.services.llm.gemini import GeminiClient
    client = GeminiClient()
    translator = QueryTranslator(client)
    result = await translator.to_english("किसानों के लिए योजनाएं", "hi")
    assert "farm" in result.lower() or "kisan" in result.lower()
