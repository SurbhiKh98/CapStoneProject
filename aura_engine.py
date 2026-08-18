"""AURA pipeline: Claude-powered extraction/risk/drafting + deterministic appetite rules.

Design note: eligibility against the carrier's appetite rules (appetite_rules.json)
is decided by plain Python logic, NOT by the LLM. This keeps the hard underwriting
gate auditable and consistent. Claude is used for the parts that genuinely need
language understanding: turning messy submission text into structured data,
writing a risk narrative that weighs soft factors, and drafting the broker reply.

Implementation note: Claude is called via a direct REST request to the
Anthropic Messages API using only the Python standard library (urllib/json),
rather than the `anthropic` SDK. This project intentionally has zero
third-party dependencies so it runs anywhere Python runs, with no pip install
required.
"""

import json
import os
import re
import urllib.error
import urllib.request

MODEL_NAME = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def call_claude(prompt: str, max_tokens: int = 1024) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it as an environment variable "
            "before running the app (see .env.example)."
        )

    payload = json.dumps(
        {
            "model": MODEL_NAME,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=payload,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API error {e.code}: {detail}") from e

    return body["content"][0]["text"]


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from a Claude text response."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


# ---------------------------------------------------------------------------
# Stage 1: Extraction
#
# EXTRACTED_FIELDS is the single source of truth for what AURA pulls out of a
# submission: the prompt's JSON shape is generated from it below, so the
# fields shown to the user (via /api/reference) can never drift from what is
# actually sent to Claude.
# ---------------------------------------------------------------------------

EXTRACTED_FIELDS = [
    {"id": "named_insured", "type_hint": "string or null", "description": "Legal name of the business being insured"},
    {"id": "industry_description", "type_hint": "string or null", "description": "What the business does / its industry or operations"},
    {"id": "state", "type_hint": "string or null (2-letter US state code if determinable, else the raw location text)", "description": "State or jurisdiction where the business/property is located"},
    {"id": "years_in_business", "type_hint": "number or null", "description": "How long the business has been operating"},
    {"id": "tiv", "type_hint": "number or null (numeric dollars, no symbols)", "description": "Total Insured Value — the dollar value of property/assets to be insured"},
    {"id": "annual_revenue", "type_hint": "number or null", "description": "The business's annual revenue"},
    {"id": "coverage_requested", "type_hint": "array of strings", "description": "Which lines of coverage the broker is requesting (e.g. General Liability, Property)"},
    {"id": "losses_last_3_years", "type_hint": "number or null (count of claims mentioned)", "description": "Number of claims/losses reported in the last 3 years"},
    {"id": "loss_narrative", "type_hint": "string or null", "description": "Summary of any claims described in the submission"},
    {"id": "prior_carrier_status", "type_hint": "string or null", "description": "What happened with the prior carrier (renewed, declined, non-renewed, and why)"},
    {"id": "requested_effective_date", "type_hint": "string or null", "description": "The date the broker wants coverage to start"},
    {"id": "missing_fields", "type_hint": "array of strings", "description": "Which of the above fields Claude could not find in the submission text"},
]


def _extraction_json_shape():
    lines = [f'  "{f["id"]}": {f["type_hint"]}' for f in EXTRACTED_FIELDS]
    return "{\n" + ",\n".join(lines) + "\n}"


EXTRACTION_PROMPT = """You are an underwriting assistant. Read the raw broker \
submission below and extract the key facts into strict JSON only (no prose, \
no markdown fences). Use null for any field that is not present in the text \
- do not guess or invent values.

Return exactly this JSON shape:
{shape}

Submission:
---
{submission}
---
"""


def extract_submission(raw_text: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(shape=_extraction_json_shape(), submission=raw_text)
    text = call_claude(prompt, max_tokens=1024)
    return _extract_json(text)


# ---------------------------------------------------------------------------
# Stage 2: Deterministic appetite / eligibility check
#
# Each rule in appetite_rules.json["rules"] is evaluated by its "type". This
# is a small rules engine, not a fixed sequence of if-statements, so the
# verdict is always traceable to a named rule id - useful for audit and for
# the rationale-consistency checks in rationale_rules.py.
# ---------------------------------------------------------------------------

def _eval_industry_exclusion(rule, extracted):
    industry = (extracted.get("industry_description") or "").lower()
    for kw in rule["keywords"]:
        if kw in industry:
            return f"Industry matches excluded class: '{kw}'."
    return None


def _eval_max_value(rule, extracted):
    value = extracted.get(rule["field"])
    if value is not None and value > rule["max"]:
        return f"{rule['field']} of {value:,.0f} exceeds maximum of {rule['max']:,.0f}."
    return None


def _eval_min_value(rule, extracted):
    value = extracted.get(rule["field"])
    if value is not None and value < rule["min"]:
        return f"{rule['field']} of {value:,.0f} is below minimum of {rule['min']:,.0f}."
    return None


def _eval_state_max_value(rule, extracted):
    state = (extracted.get("state") or "").upper()
    value = extracted.get(rule["field"])
    state_rule = rule["states"].get(state)
    if state_rule and value is not None and value > state_rule["max"]:
        return (
            f"State {state} {rule['field']} of {value:,.0f} exceeds state threshold "
            f"{state_rule['max']:,.0f} ({state_rule['note']})."
        )
    return None


def _eval_text_contains(rule, extracted):
    text = (extracted.get(rule["field"]) or "").lower()
    for excl in rule.get("exclude_keywords", []):
        if excl.lower() in text:
            return None
    for kw in rule["keywords"]:
        if kw.lower() in text:
            return f"{rule['field']} indicates: '{kw}'."
    return None


def _eval_missing_fields_threshold(rule, extracted):
    missing = extracted.get("missing_fields") or []
    if len(missing) >= rule["min_missing"]:
        return f"Submission is missing key fields: {', '.join(missing)}."
    return None


RULE_EVALUATORS = {
    "industry_exclusion": _eval_industry_exclusion,
    "max_value": _eval_max_value,
    "min_value": _eval_min_value,
    "state_max_value": _eval_state_max_value,
    "text_contains": _eval_text_contains,
    "missing_fields_threshold": _eval_missing_fields_threshold,
}

_SEVERITY_ORDER = {"Eligible": 0, "Refer": 1, "Ineligible": 2}


def check_appetite(extracted: dict, rules: dict) -> dict:
    status = "Eligible"
    reasons = []  # list of {"rule_id": str, "message": str}

    for rule in rules.get("rules", []):
        evaluator = RULE_EVALUATORS.get(rule["type"])
        if evaluator is None:
            continue
        message = evaluator(rule, extracted)
        if message is None:
            continue
        reasons.append({"rule_id": rule["id"], "message": message})
        if _SEVERITY_ORDER[rule["severity"]] > _SEVERITY_ORDER[status]:
            status = rule["severity"]

    if not reasons:
        reasons.append({"rule_id": None, "message": "No appetite rule violations found against current rule set."})

    return {"status": status, "reasons": reasons}


# ---------------------------------------------------------------------------
# Stage 3: Risk triage narrative
#
# RISK_CRITERIA is the single source of truth for what Claude is told to
# weigh when producing the Low/Medium/High tier - shown to the user via
# /api/reference, and rendered directly into the prompt below, so the two
# can never drift apart. The appetite result is deliberately listed as an
# authoritative floor, not just another criterion: the rationale-consistency
# checks in rationale_rules.py enforce that Claude never contradicts it.
# ---------------------------------------------------------------------------

RISK_CRITERIA = [
    {"id": "LOSS_NARRATIVE_SEVERITY", "description": "Nature, frequency, and cost of past claims described in the submission"},
    {"id": "INDUSTRY_HAZARD", "description": "Inherent hazard level of the business's industry or operations"},
    {"id": "DATA_COMPLETENESS", "description": "How much required underwriting information is missing, ambiguous, or unconfirmed"},
    {"id": "THIRD_PARTY_EXPOSURE", "description": "Reliance on subcontracted labor or third parties that adds exposure outside direct control, where applicable"},
    {"id": "BUSINESS_TENURE", "description": "Years in business as a proxy for operational stability and risk-management maturity"},
    {"id": "APPETITE_RESULT_FLOOR", "description": "The deterministic eligibility verdict is an authoritative floor: Ineligible must map to High risk, Refer must not map to Low risk"},
]


def _risk_criteria_text():
    return "\n".join(f"- {c['id']}: {c['description']}" for c in RISK_CRITERIA)


RISK_PROMPT = """You are a senior commercial P&C underwriter assistant. You are \
given structured facts extracted from a broker submission and the result of a \
deterministic appetite/eligibility check. The appetite check result is \
authoritative for eligibility - do not override it. Your job is to add the \
judgment a hard rule engine can't, by weighing these criteria (skip any that \
don't apply to this submission):

{criteria}

Respond in strict JSON only (no markdown fences):
{{
  "risk_tier": "Low" | "Medium" | "High",
  "rationale": [string, ...]  (2-4 short bullet points explaining the tier),
  "data_gaps": [string, ...]  (fields missing or ambiguous that a human underwriter should chase down; empty list if none)
}}

Extracted facts:
{extracted}

Appetite check result:
{appetite}
"""


def assess_risk(extracted: dict, appetite_result: dict) -> dict:
    prompt = RISK_PROMPT.format(
        criteria=_risk_criteria_text(),
        extracted=json.dumps(extracted, indent=2),
        appetite=json.dumps(appetite_result, indent=2),
    )
    text = call_claude(prompt, max_tokens=1024)
    return _extract_json(text)


# ---------------------------------------------------------------------------
# Stage 4: Draft broker response
# ---------------------------------------------------------------------------

RESPONSE_PROMPT = """You are drafting a professional, concise email reply to an \
insurance broker regarding their commercial P&C submission. Use the underwriting \
outcome below to decide the tone and content:

- If appetite status is "Ineligible": politely decline, state the general reason \
  category (do not sound bureaucratic), and avoid inviting resubmission unless facts change.
- If appetite status is "Refer": tell the broker the submission is under review \
  by a senior underwriter, and if there are data gaps, ask for the specific \
  missing information needed to proceed.
- If appetite status is "Eligible": confirm the account is being moved into the \
  quoting process, and if there are data gaps, ask for them before a quote can be finalized.

Keep it under 150 words, professional and warm, no subject line, no placeholder \
brackets like [Name] - address the broker generically as "there" if no name is given.

Named insured: {named_insured}
Appetite status: {status}
Appetite reasons: {reasons}
Risk tier: {risk_tier}
Data gaps: {data_gaps}
"""


def draft_response(extracted: dict, appetite_result: dict, risk_result: dict) -> str:
    prompt = RESPONSE_PROMPT.format(
        named_insured=extracted.get("named_insured") or "the applicant",
        status=appetite_result["status"],
        reasons="; ".join(r["message"] for r in appetite_result["reasons"]),
        risk_tier=risk_result.get("risk_tier", "Unknown"),
        data_gaps="; ".join(risk_result.get("data_gaps", [])) or "None",
    )
    return call_claude(prompt, max_tokens=512).strip()


def load_appetite_rules(path: str = "appetite_rules.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
