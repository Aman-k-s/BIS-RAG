from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import pdfplumber


ENTRY_HEADER_RE = re.compile(
    r"IS\s+(?P<number>\d+)\s*(?:\((?:PART|Part)\s*(?P<part>\d+)\))?\s*:\s*(?P<year>\d{4})\s+(?P<rest>.*)",
    re.IGNORECASE | re.DOTALL,
)
SCOPE_RE = re.compile(r"1\.\s*Scope\s*[—-]\s*(.*?)(?=\n\s*2\.\s|\Z)", re.IGNORECASE | re.DOTALL)
TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_text(text: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2019": "'",
        "\u2018": "'",
        "\u00ad": "",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\xa0": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def page_texts(pdf_path: Path) -> List[str]:
    pages: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text:
                pages.append(normalize_text(text))
    return pages


def split_blocks(pages: List[str]) -> List[str]:
    blocks: List[str] = []
    current: Optional[str] = None

    for page in pages:
        segments = page.split("SUMMARY OF")
        if len(segments) == 1:
            if current:
                current += "\n" + segments[0]
            continue

        prefix = segments[0]
        if current:
            current += "\n" + prefix
            blocks.append(current)
            current = None

        for segment in segments[1:]:
            if current is not None:
                blocks.append(current)
            current = "SUMMARY OF\n" + segment

    if current:
        blocks.append(current)

    return blocks


def extract_title(header_rest: str) -> str:
    title = re.split(r"\n\s*1\.\s*Scope", header_rest, maxsplit=1, flags=re.IGNORECASE)[0]
    title = re.split(r"\((?:First|Second|Third|Fourth|Fifth).*?Revision\)", title, maxsplit=1, flags=re.IGNORECASE)[0]
    title = re.sub(r"\s+", " ", title)
    return title.strip(" -")


def detect_section(title: str, scope: str) -> str:
    text = f"{title} {scope}".lower()
    if "cement" in text:
        return "cement"
    if "aggregate" in text or "sand " in f"{text} ":
        return "aggregates"
    if "pipe" in text:
        return "pipes"
    if "block" in text or "masonry" in text:
        return "masonry"
    if "sheet" in text or "cladding" in text or "roof" in text:
        return "sheets"
    if "concrete" in text:
        return "concrete"
    return "other"


def extract_keywords(title: str, scope: str) -> List[str]:
    tokens = TOKEN_RE.findall(f"{title.lower()} {scope.lower()}")
    unique: List[str] = []
    seen = set()
    for token in tokens:
        if len(token) < 3:
            continue
        if token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return unique[:40]


def parse_block(block: str) -> Optional[Dict[str, object]]:
    block = normalize_text(block)
    match = ENTRY_HEADER_RE.search(block)
    if not match:
        return None

    number = match.group("number")
    part = match.group("part")
    year = match.group("year")
    header_rest = match.group("rest")
    title = extract_title(header_rest)

    scope_match = SCOPE_RE.search(block)
    scope = normalize_text(scope_match.group(1)) if scope_match else ""

    full_id = f"IS {number}"
    if part:
        full_id += f" (Part {part})"
    full_id += f": {year}"

    body = re.sub(r"\s+", " ", block)
    body = body[:3000]
    section = detect_section(title, scope)
    keywords = extract_keywords(title, scope)
    embedding_text = " ".join(
        piece for piece in [full_id, title, scope, " ".join(keywords), section] if piece
    )

    return {
        "full_id": full_id,
        "is_number": number,
        "part": part,
        "year": year,
        "title": title,
        "scope": scope,
        "section": section,
        "keywords": keywords,
        "embedding_text": embedding_text,
        "source_text": body,
    }


def dedupe_records(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    deduped: Dict[str, Dict[str, object]] = {}
    for record in records:
        existing = deduped.get(record["full_id"])
        if existing is None or len(str(record.get("scope", ""))) > len(str(existing.get("scope", ""))):
            deduped[str(record["full_id"])] = record
    return list(deduped.values())


def build_database(pdf_path: Path) -> List[Dict[str, object]]:
    pages = page_texts(pdf_path)
    blocks = split_blocks(pages)
    records = [record for block in blocks if (record := parse_block(block))]
    records = dedupe_records(records)
    records.sort(key=lambda item: (int(item["is_number"]), int(item["part"] or 0), int(item["year"])))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse BIS dataset PDF into structured JSON.")
    parser.add_argument("--pdf", required=True, help="Path to the BIS dataset PDF.")
    parser.add_argument("--output", required=True, help="Path to write the parsed JSON database.")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_path = Path(args.output)

    records = build_database(pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} records to {output_path}")


if __name__ == "__main__":
    main()
