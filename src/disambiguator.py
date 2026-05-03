from __future__ import annotations

from typing import Dict, List


def apply_disambiguation(query: str, candidates: List[Dict[str, object]]) -> List[Dict[str, object]]:
    lower_query = query.lower()

    for candidate in candidates:
        record = candidate["record"]
        full_id = str(record["full_id"]).lower()

        if "1489" in full_id:
            if "calcined clay" in lower_query and "(part 2)" in full_id:
                candidate["score"] += 0.6
            if "calcined clay" in lower_query and "(part 1)" in full_id:
                candidate["score"] -= 0.4
            if "fly ash" in lower_query and "(part 1)" in full_id:
                candidate["score"] += 0.6
            if "fly ash" in lower_query and "(part 2)" in full_id:
                candidate["score"] -= 0.4

        if "2185" in full_id:
            if "lightweight" in lower_query and "(part 2)" in full_id:
                candidate["score"] += 0.6
            if "lightweight" in lower_query and "(part 1)" in full_id:
                candidate["score"] -= 0.3
            if "hollow" in lower_query and "(part 1)" in full_id:
                candidate["score"] += 0.2

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates
