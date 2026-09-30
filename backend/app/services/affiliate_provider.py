"""Affiliate provider abstractions.

V1.4 deliberately uses only public URLs and official/authorized APIs already configured.
It does not call private affiliate-panel endpoints or fabricate commission data.
"""
from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

import httpx

MLB_RE = re.compile(r"\bMLB[0-9]{6,20}\b", re.I)
ALLOWED_HOSTS = {
    "meli.la",
    "mercadolivre.com.br",
    "www.mercadolivre.com.br",
    "produto.mercadolivre.com.br",
    "lista.mercadolivre.com.br",
}


def _safe_https(url: str) -> str:
    value = url.strip()
    p = urlparse(value)
    if p.scheme != "https" or not p.hostname or p.hostname.lower() not in ALLOWED_HOSTS:
        raise ValueError("Use um link HTTPS oficial do Mercado Livre ou meli.la")
    if p.username or p.password or p.port or len(value) > 2000:
        raise ValueError("URL inválida")
    return value


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        data = {str(k).lower(): str(v) for k, v in attrs if k and v is not None}
        if tag.lower() == "meta":
            key = (data.get("property") or data.get("name") or "").lower()
            content = data.get("content", "").strip()
            if key and content and len(content) <= 4000:
                self.meta[key] = unescape(content)
        elif tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title and len("".join(self.title_parts)) < 500:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return unescape("".join(self.title_parts)).strip()


async def analyze_mercadolivre_url(raw_url: str) -> dict:
    """Resolve an official URL and extract only metadata actually exposed by the page."""
    start = _safe_https(raw_url)
    current = start
    response = None
    async with httpx.AsyncClient(
        timeout=12,
        follow_redirects=False,
        headers={"User-Agent": "AffiliateIntelligence/1.4 (+product-link-analyzer)"},
    ) as client:
        for _ in range(6):
            response = await client.get(current)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location", "")
                if not location:
                    break
                next_url = str(httpx.URL(current).join(location))
                current = _safe_https(next_url)
                continue
            break

    final_url = current
    parsed = urlparse(final_url)
    text_for_id = unquote(start + " " + final_url)
    match = MLB_RE.search(text_for_id)
    external_id = match.group(0).upper() if match else None
    is_affiliate = urlparse(start).hostname == "meli.la" or "/social/" in parsed.path

    result = {
        "input_url": start,
        "resolved_url": final_url,
        "marketplace": "Mercado Livre",
        "external_id": external_id,
        "title": None,
        "image_url": None,
        "price": None,
        "affiliate_url": start if is_affiliate else None,
        "affiliate_detected": is_affiliate,
        "data_source": "url_resolution",
        "warnings": [],
    }
    if response is None:
        result["warnings"].append("Não foi possível consultar a página.")
        return result

    ctype = response.headers.get("content-type", "")
    if response.status_code == 200 and "text/html" in ctype and len(response.content) <= 3_000_000:
        parser = _MetaParser()
        try:
            parser.feed(response.text[:3_000_000])
        except Exception:
            pass
        title = parser.meta.get("og:title") or parser.title or None
        image = parser.meta.get("og:image") or None
        price_raw = parser.meta.get("product:price:amount") or parser.meta.get("og:price:amount")
        price = None
        if price_raw:
            try:
                candidate = float(price_raw.replace(",", "."))
                price = candidate if candidate > 0 else None
            except ValueError:
                pass
        result.update(title=title[:300] if title else None, image_url=image[:2000] if image else None, price=price, data_source="public_page_metadata")
    elif response.status_code != 200:
        result["warnings"].append(f"A página respondeu HTTP {response.status_code}; alguns dados precisarão ser confirmados.")

    if not result["external_id"]:
        result["warnings"].append("O ID MLB não ficou exposto no link analisado.")
    if not result["title"]:
        result["warnings"].append("Título não disponível automaticamente.")
    if not result["affiliate_detected"]:
        result["warnings"].append("Este parece ser um link de produto, não um link remunerado.")
    return result
