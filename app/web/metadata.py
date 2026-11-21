import re
import urllib.parse
from html.parser import HTMLParser
import aiohttp
from typing import Dict, Any, Optional

class OpenGraphParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: Dict[str, str] = {}
        self.title: Optional[str] = None
        self._in_title = False
        self._title_chunks = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        prop = attrs_dict.get("property") or attrs_dict.get("name")
        content = attrs_dict.get("content")
        
        if prop and content:
            prop_lower = prop.lower()
            if prop_lower not in self.tags:
                self.tags[prop_lower] = content
                
        if tag.lower() == "title":
            self._in_title = True
            self._title_chunks = []

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False
            self.title = "".join(self._title_chunks).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title_chunks.append(data)

async def extract_url_metadata(url: str) -> Dict[str, Any]:
    """
    Asynchronously fetches a URL and parses its title, OpenGraph image, description and price.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                if resp.status >= 400:
                    return {"url": url}
                
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return {"url": url}

                # Read only up to 256KB to avoid memory bloat
                html_bytes = await resp.content.read(256 * 1024)
                
                charset = resp.charset or "utf-8"
                try:
                    html_text = html_bytes.decode(charset, errors="replace")
                except Exception:
                    html_text = html_bytes.decode("utf-8", errors="replace")

                parser = OpenGraphParser()
                parser.feed(html_text)

                og_title = (
                    parser.tags.get("og:title")
                    or parser.tags.get("twitter:title")
                    or parser.title
                )
                og_image = (
                    parser.tags.get("og:image")
                    or parser.tags.get("twitter:image")
                )
                og_description = (
                    parser.tags.get("og:description")
                    or parser.tags.get("twitter:description")
                    or parser.tags.get("description")
                )
                
                # Check price tags
                raw_price = (
                    parser.tags.get("og:price:amount")
                    or parser.tags.get("product:price:amount")
                    or parser.tags.get("price")
                )
                price = None
                if raw_price:
                    match = re.search(r"[\d\s.,]+", raw_price)
                    if match:
                        try:
                            clean_price = match.group(0).replace(" ", "").replace(",", ".")
                            price = float(clean_price)
                        except ValueError:
                            pass

                # Resolve relative image URLs
                if og_image and not og_image.startswith(("http://", "https://")):
                    og_image = urllib.parse.urljoin(url, og_image)

                return {
                    "url": url,
                    "title": og_title.strip() if og_title else None,
                    "image_url": og_image.strip() if og_image else None,
                    "description": og_description.strip() if og_description else None,
                    "price": price
                }
    except Exception:
        return {"url": url}
