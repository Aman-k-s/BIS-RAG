from __future__ import annotations

import re
from typing import Dict, List


GRADE_RE = re.compile(r"\b(33|43|53)\s*grade\b", re.IGNORECASE)


def rerank(query: str, candidates: List[Dict[str, object]], top_k: int = 5) -> List[Dict[str, object]]:
    lower_query = query.lower()
    grade_match = GRADE_RE.search(lower_query)
    grade = grade_match.group(1) if grade_match else None

    for candidate in candidates:
        record = candidate["record"]
        text = f"{record['title']} {record['scope']}".lower()

        if grade and grade in text:
            candidate["score"] += 0.45
        if "cement" in lower_query and record["section"] == "cement":
            candidate["score"] += 0.15
        if "aggregate" in lower_query and record["section"] == "aggregates":
            candidate["score"] += 0.2
        if "pipe" in lower_query and record["section"] == "pipes":
            candidate["score"] += 0.25
        if "masonry" in lower_query and record["section"] == "masonry":
            candidate["score"] += 0.2
        if "sheet" in lower_query and record["section"] == "sheets":
            candidate["score"] += 0.2
        if "sheet" in lower_query and "fitting" in text:
            candidate["score"] -= 0.35
        if "sheet" in lower_query and "roof fittings" in text:
            candidate["score"] -= 0.45
        if "water main" in lower_query and "water mains" in text:
            candidate["score"] += 0.3
        if "white" in lower_query and "white" in text:
            candidate["score"] += 0.3
        if "slag" in lower_query and "slag" in text:
            candidate["score"] += 0.35
        if "supersulphated" in lower_query and "supersulphated" in text:
            candidate["score"] += 0.65
        if "supersulphated" in lower_query and "sulphate resisting" in text:
            candidate["score"] -= 0.45
        if "aggressive water" in lower_query and "supersulphated" in text:
            candidate["score"] += 0.2
        if "marine" in lower_query and "supersulphated" in text:
            candidate["score"] += 0.15
        if "cladding" in lower_query and "cladding" in text:
            candidate["score"] += 0.25
        if "asbestos" in lower_query and "asbestos" in text:
            candidate["score"] += 0.45
        if "corrugated" in lower_query and "corrugated" in text:
            candidate["score"] += 0.25
        if "semi-corrugated" in lower_query and "semi-corrugated" in text:
            candidate["score"] += 0.2
        if "roofing" in lower_query and "weather exposed surfaces of roofs" in text:
            candidate["score"] += 0.2
        if "asbestos" in lower_query and "fibre reinforced cement" in text:
            candidate["score"] -= 0.15

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_k]
