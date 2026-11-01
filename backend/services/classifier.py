import re
from typing import Tuple

SIGNALS = {
    "electricity_bill": ("electricity", "electric bill", "vidyut", "kwh", "kvah", "meter reading", "sanctioned load", "billed demand", "fppa", "lpsc", "???????", "?????", "??? ???", "????????"),
    "gas_bill": ("gas bill", "piped gas", "png", "cng", "scm", "gas connection", "??? ???"),
    "water_bill": ("water bill", "water usage", "kiloliter", "kl consumption", "?? ???", "???? ???"),
    "telecom_bill": ("telecom", "mobile bill", "broadband", "data usage", "postpaid", "????????"),
    "invoice": ("tax invoice", "invoice no", "bill to", "ship to", "gstin", "invoice"),
}


def classify_document_type(full_text: str) -> Tuple[str, float]:
    text = re.sub(r"\s+", " ", (full_text or "").casefold())
    scores = {kind: sum(1 for signal in signals if signal.casefold() in text) for kind, signals in SIGNALS.items()}
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] == 0:
        return "unknown", 0.0
    best, score = ranked[0]
    second = ranked[1][1]
    if score < 2 or score == second:
        return "unknown", 0.35 if score else 0.0
    confidence = min(0.95, 0.55 + 0.08 * score + 0.06 * (score - second))
    return best, round(confidence, 2)
