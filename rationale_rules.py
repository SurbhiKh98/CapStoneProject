"""Rules for checking Claude's risk rationale, not for deciding eligibility.

appetite_rules.json / check_appetite() decide the verdict. This module runs
a second, independent pass AFTER Claude produces its risk narrative, to
check whether that narrative is internally consistent with the verdict and
grounded in the actual extracted facts - e.g. it should never call an
Ineligible account "Low risk", and a dollar figure it cites should trace
back to something actually present in the submission. This is a safety net
against the AI silently contradicting or hallucinating on top of the
deterministic result, not a substitute for it.
"""

import re

# Keywords expected to show up in the rationale when a given appetite rule
# fires - used by RATIONALE_ADDRESSES_TRIGGERED_RULES below.
RULE_KEYWORDS = {
    "EXCLUDED_INDUSTRY": ["exclud", "prohibit", "hazard"],
    "OVER_AUTHORITY_TIV": ["tiv", "authority", "binding", "insured value"],
    "STATE_TIV_RESTRICTION": ["tiv", "coastal", "wildfire", "state", "catastrophe", "wind"],
    "MIN_YEARS_IN_BUSINESS": ["year", "tenure", "new business", "start-up", "young"],
    "MAX_LOSSES": ["loss", "claim"],
    "MIN_ANNUAL_REVENUE": ["revenue", "premium", "account size", "small"],
    "NON_RENEWED_FOR_CAUSE": ["non-renew", "prior carrier", "cause", "declined"],
    "MISSING_FIELDS": ["missing", "insufficient", "incomplete", "unconfirmed", "not provided", "unknown", "gap"],
}

_DOLLAR_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(k|m|million|thousand)?", re.IGNORECASE)


def _parse_dollar_amounts(text):
    amounts = []
    for value_str, suffix in _DOLLAR_RE.findall(text or ""):
        value = float(value_str.replace(",", ""))
        suffix = (suffix or "").lower()
        if suffix in ("k", "thousand"):
            value *= 1_000
        elif suffix in ("m", "million"):
            value *= 1_000_000
        amounts.append(value)
    return amounts


def _numbers_in_extracted(extracted):
    numbers = set()
    for key in ("tiv", "annual_revenue"):
        value = extracted.get(key)
        if isinstance(value, (int, float)):
            numbers.add(round(value))
    numbers.update(round(v) for v in _parse_dollar_amounts(extracted.get("loss_narrative") or ""))
    return numbers


def _check(rule_id, description, passed, detail):
    return {"id": rule_id, "description": description, "passed": passed, "detail": detail}


def validate_rationale(extracted: dict, appetite_result: dict, risk_result: dict) -> list:
    checks = []
    status = appetite_result["status"]
    risk_tier = risk_result.get("risk_tier")
    rationale = risk_result.get("rationale") or []
    data_gaps = risk_result.get("data_gaps") or []
    rationale_text = " ".join(rationale).lower()

    checks.append(
        _check(
            "RATIONALE_MIN_LENGTH",
            "Risk rationale gives at least 2 supporting bullet points",
            len(rationale) >= 2,
            f"{len(rationale)} bullet point(s) provided.",
        )
    )

    checks.append(
        _check(
            "TIER_CONSISTENT_WITH_INELIGIBLE",
            "An Ineligible account is never reported as anything but High risk",
            status != "Ineligible" or risk_tier == "High",
            f"Appetite status is '{status}', risk tier is '{risk_tier}'.",
        )
    )

    checks.append(
        _check(
            "TIER_NOT_LOW_ON_REFER",
            "A Refer account is never reported as Low risk",
            status != "Refer" or risk_tier != "Low",
            f"Appetite status is '{status}', risk tier is '{risk_tier}'.",
        )
    )

    missing_fields = extracted.get("missing_fields") or []
    checks.append(
        _check(
            "DATA_GAPS_COVER_MISSING",
            "If extraction found missing fields, the risk narrative flags data gaps too",
            not missing_fields or bool(data_gaps),
            f"{len(missing_fields)} missing field(s) from extraction, {len(data_gaps)} data gap(s) flagged in rationale.",
        )
    )

    cited = _parse_dollar_amounts(rationale_text)
    known = _numbers_in_extracted(extracted)
    ungrounded = [amt for amt in cited if not any(abs(amt - k) <= max(1, 0.01 * k) for k in known)]
    checks.append(
        _check(
            "RATIONALE_GROUNDED_FIGURES",
            "Every dollar figure cited in the rationale traces back to the extracted submission facts",
            not ungrounded,
            "All cited figures matched extracted data." if not ungrounded else f"Unverified figure(s): {ungrounded}",
        )
    )

    triggered_ids = [r["rule_id"] for r in appetite_result["reasons"] if r["rule_id"]]
    if triggered_ids:
        addressed = all(
            any(kw in rationale_text for kw in RULE_KEYWORDS.get(rule_id, []))
            for rule_id in triggered_ids
        )
        detail = f"Triggered rules: {', '.join(triggered_ids)}."
    else:
        addressed = True
        detail = "No appetite rules were triggered."
    checks.append(
        _check(
            "RATIONALE_ADDRESSES_TRIGGERED_RULES",
            "Rationale discusses every appetite rule that was triggered",
            addressed,
            detail,
        )
    )

    return checks
