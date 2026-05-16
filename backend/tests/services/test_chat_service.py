import pytest
from app.services.chat.chat_service import should_search_schemes

@pytest.mark.parametrize("message, expected", [
    ("show me farming schemes", True),
    ("what schemes are available for students?", True),
    ("find me a pension plan", True),
    ("mujhe yojana dikhao", True),
    ("ನನಗೆ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಿ", True),
    ("I need a scholarship", True),
    ("what is pm kisan", False),
    ("hello there", False),
    ("how do I apply?", False),
    ("thank you", False),
])
def test_should_search_schemes(message, expected):
    assert should_search_schemes(message) == expected
