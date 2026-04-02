from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def parse_html(html: str, selectors: dict) -> list[dict]:
    """
    Parse HTML with BeautifulSoup using CSS selectors.

    The selectors dict maps field names to CSS selectors.
    For example: {"title": "h2.title", "price": "span.price", "link": "a.product-link@href"}

    Supports @attribute suffix to extract an attribute instead of text.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Determine the number of items by finding the max number of matches
    field_elements = {}
    max_count = 0

    for field_name, selector in selectors.items():
        # Check for attribute extraction (e.g., "a.link@href")
        attr = None
        css_selector = selector
        if "@" in selector:
            parts = selector.rsplit("@", 1)
            css_selector = parts[0]
            attr = parts[1]

        elements = soup.select(css_selector)
        field_elements[field_name] = (elements, attr)
        if len(elements) > max_count:
            max_count = len(elements)

    results = []
    for i in range(max_count):
        row = {}
        for field_name, (elements, attr) in field_elements.items():
            if i < len(elements):
                element = elements[i]
                if attr:
                    row[field_name] = element.get(attr, "")
                else:
                    row[field_name] = element.get_text(strip=True)
            else:
                row[field_name] = None
        results.append(row)

    return results


def extract_pagination_url(
    html: str,
    pagination_config: dict,
    base_url: str,
) -> Optional[str]:
    """
    Find next page URL based on pagination config.

    pagination_config can contain:
    - next_selector: CSS selector for the "next" link/button
    - url_pattern: URL pattern with {page} placeholder
    - current_page: current page number (used with url_pattern)
    - max_pages: maximum number of pages to scrape
    """
    if not pagination_config:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Method 1: CSS selector for next link
    next_selector = pagination_config.get("next_selector")
    if next_selector:
        next_el = soup.select_one(next_selector)
        if next_el:
            href = next_el.get("href")
            if href:
                return urljoin(base_url, href)
        return None

    # Method 2: URL pattern with page number
    url_pattern = pagination_config.get("url_pattern")
    current_page = pagination_config.get("current_page", 1)
    max_pages = pagination_config.get("max_pages", 10)

    if url_pattern and current_page < max_pages:
        next_page = current_page + 1
        return url_pattern.replace("{page}", str(next_page))

    return None
