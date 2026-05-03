"""Query expansion helpers for BIS building materials queries."""

from __future__ import annotations

from typing import Dict, List


SYNONYM_MAP: Dict[str, List[str]] = {
    "opc": ["ordinary portland cement"],
    "ordinary portland cement": ["opc cement", "33 grade cement", "43 grade cement", "53 grade cement"],
    "33 grade": ["opc 33", "ordinary portland cement 33"],
    "43 grade": ["opc 43", "ordinary portland cement 43"],
    "53 grade": ["opc 53", "ordinary portland cement 53"],
    "portland slag cement": ["psc cement", "slag cement"],
    "portland pozzolana cement": ["ppc cement", "pozzolana cement"],
    "fly ash": ["part 1", "portland pozzolana cement fly ash based"],
    "calcined clay": ["part 2", "portland pozzolana cement calcined clay based"],
    "masonry cement": ["mortar cement", "cement for masonry"],
    "supersulphated cement": ["marine cement", "cement for aggressive water"],
    "white portland cement": ["white cement", "decorative cement", "architectural cement"],
    "hydrophobic cement": ["water repellent cement"],
    "low heat portland cement": ["low heat cement", "mass concrete cement"],
    "rapid hardening portland cement": ["rapid hardening cement", "high early strength cement"],
    "high alumina cement": ["refractory cement", "aluminous cement"],
    "coarse aggregates": ["coarse aggregate", "stone aggregate"],
    "fine aggregates": ["fine aggregate", "sand aggregate"],
    "aggregates": ["coarse and fine aggregates", "aggregate for concrete"],
    "structural concrete": ["concrete work", "concrete construction"],
    "precast concrete pipes": ["concrete pipe", "reinforced concrete pipe", "water main pipe"],
    "concrete masonry blocks": ["concrete blocks", "masonry units", "cement blocks"],
    "lightweight concrete masonry blocks": ["lightweight masonry blocks", "hollow lightweight concrete blocks"],
    "hollow blocks": ["hollow concrete blocks"],
    "solid blocks": ["solid concrete blocks"],
    "roofing sheets": ["corrugated sheets", "semi corrugated sheets", "cladding sheets"],
    "asbestos cement sheets": ["corrugated asbestos cement sheets", "roofing and cladding sheets"],
}


def expand_query(query: str) -> str:
    """Appends domain synonyms that increase retrieval recall for BIS vocabulary."""

    lower_query = query.lower()
    expansions: List[str] = []

    for key, values in SYNONYM_MAP.items():
        if key in lower_query:
            expansions.extend(values)
        else:
            for value in values:
                if value in lower_query:
                    expansions.append(key)
                    expansions.extend(values)
                    break

    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query
