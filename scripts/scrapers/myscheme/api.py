from collections.abc import AsyncIterator

from scrapers.myscheme.client import MySchemeClient

_PAGE_SIZE = 20


async def iter_listing_items(
    client: MySchemeClient,
    limit: int,
    state_filter: str | None = None,
) -> AsyncIterator[dict]:  # type: ignore[type-arg]
    """Yield listing-endpoint items (fields dict) up to `limit` total.

    When state_filter is set, all pages are scanned and items are filtered
    client-side by beneficiaryState (server-side state filtering is not
    supported by the myScheme v6 API).
    """
    collected = 0
    page = 0
    while collected < limit:
        # In scan mode always fetch full pages; otherwise cap to remaining.
        size = _PAGE_SIZE if state_filter else min(_PAGE_SIZE, limit - collected)
        data = await client.get(
            "/search/v6/schemes",
            lang="en",
            q="",
            keyword="",
            sort="",
            **{"from": str(page * _PAGE_SIZE), "size": str(size)},
        )
        items = data["data"]["hits"]["items"]
        if not items:
            break
        for item in items:
            if state_filter:
                states: list[str] = item["fields"].get("beneficiaryState") or []
                if state_filter not in states:
                    continue
            yield item["fields"]
            collected += 1
            if collected >= limit:
                return
        total_pages: int = data["data"]["hits"]["page"]["totalPages"]
        page += 1
        if page >= total_pages:
            break


async def fetch_detail(client: MySchemeClient, slug: str) -> dict:  # type: ignore[type-arg]
    """Fetch full scheme detail for a single slug. Returns the raw `data` dict."""
    resp = await client.get("/schemes/v6/public/schemes", slug=slug, lang="en")
    return resp["data"]  # type: ignore[no-any-return]
