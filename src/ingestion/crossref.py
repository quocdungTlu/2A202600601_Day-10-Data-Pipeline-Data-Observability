from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from core.config import Settings
from core.utils import normalize_whitespace, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"
_USER_AGENT = "Day10-DataObservability/1.0 (mailto:student@lab.local)"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities (e.g. &lt;jats:p&gt; in Crossref abstracts)."""
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = html.unescape(cleaned)
    return normalize_whitespace(cleaned)


def _parse_date_parts(date_obj: dict) -> str:
    parts = (date_obj.get("date-parts") or [[]])[0]
    if not parts:
        return ""
    year = parts[0] if len(parts) > 0 else 0
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref /works API payload into a list of PaperRecord objects."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        titles = item.get("title", [])
        title = _strip_html(titles[0]) if titles else ""
        if not title:
            continue

        abstract = _strip_html(item.get("abstract", ""))
        if not abstract:
            continue

        raw_authors = item.get("author", [])
        authors: list[str] = []
        for a in raw_authors:
            name = " ".join(filter(None, [a.get("given", ""), a.get("family", "")])).strip()
            if name:
                authors.append(name)

        categories = [s.strip() for s in item.get("subject", []) if s.strip()]
        primary_category = categories[0] if categories else ""

        pub_date = ""
        for key in ("published-print", "published-online", "created", "deposited"):
            date_obj = item.get(key)
            if date_obj:
                pub_date = _parse_date_parts(date_obj)
                if pub_date:
                    break

        upd_date = ""
        for key in ("deposited", "indexed"):
            date_obj = item.get(key)
            if date_obj:
                upd_date = _parse_date_parts(date_obj)
                if upd_date:
                    break
        if not upd_date:
            upd_date = pub_date

        abs_url = item.get("URL", f"https://doi.org/{doi}")
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=abstract,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=pub_date,
                updated=upd_date,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment="",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Call the Crossref REST API, save raw response, and return parsed records."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": ",".join([
            "DOI", "title", "abstract", "author", "subject",
            "published-print", "published-online", "created",
            "deposited", "indexed", "URL", "link",
        ]),
    }
    headers = {"User-Agent": _USER_AGENT}

    payload: dict = {}
    for attempt in range(4):
        try:
            response = requests.get(
                CROSSREF_API_URL, params=params, headers=headers, timeout=30
            )
            if response.status_code in (429, 503):
                wait = 2 ** attempt
                print(f"  Rate-limited ({response.status_code}), retrying in {wait}s ...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as exc:
            if attempt == 3:
                raise
            wait = 2 ** attempt
            print(f"  Request error ({exc}), retrying in {wait}s ...")
            time.sleep(wait)

    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    total_available = payload.get("message", {}).get("total-results", "?")
    print(f"  API total-results={total_available}, parsed={len(records)} records with abstract")

    records_data = [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        for r in records
    ]
    write_json(settings.paths.raw_records_json, records_data)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a previously-saved JSON snapshot back into PaperRecord objects."""
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        PaperRecord(
            paper_id=item["paper_id"],
            title=item["title"],
            summary=item["summary"],
            authors=item["authors"],
            categories=item["categories"],
            primary_category=item["primary_category"],
            published=item["published"],
            updated=item["updated"],
            abs_url=item["abs_url"],
            pdf_url=item["pdf_url"],
            comment=item.get("comment", ""),
        )
        for item in data
    ]
