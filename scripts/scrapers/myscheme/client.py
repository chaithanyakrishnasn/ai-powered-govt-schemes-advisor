from scrapers._common.http import AsyncHTTPClient

_API_KEY = "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc"
_BASE_URL = "https://api.myscheme.gov.in"
_HEADERS = {
    "x-api-key": _API_KEY,
    "Origin": "https://www.myscheme.gov.in",
    "Referer": "https://www.myscheme.gov.in/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}


class MySchemeClient(AsyncHTTPClient):
    def __init__(self, rate_limit: float = 2.0, concurrency: int = 4) -> None:
        super().__init__(_BASE_URL, _HEADERS, rate_limit, concurrency)
