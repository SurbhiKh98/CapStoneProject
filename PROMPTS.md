# AI Prompts Used in AURA

All prompts below are defined as constants in [`aura_engine.py`](aura_engine.py) and sent to Claude via a direct REST call to the Anthropic Messages API (`call_claude()`, standard library `urllib` only — no SDK dependency). This file documents them for reviewers, per the capstone submission requirements.

## 1. Extraction — `EXTRACTION_PROMPT`

**Purpose:** convert unstructured broker submission text (email + application details, inconsistent format) into a strict JSON object of underwriting fields, explicitly instructed to use `null` rather than guessing when information is absent — this is what lets later stages flag data gaps instead of silently fabricating facts.

The JSON shape in the prompt is not hand-typed — it's generated from `EXTRACTED_FIELDS`, a list of 12 `{id, type_hint, description}` entries at the top of `aura_engine.py`. That list is also served as-is via `GET /api/reference` and rendered as the "Fields AURA Extracts" collapsible section in the UI, so the documented fields and the actual prompt can never drift apart.

**Used by:** `extract_submission(raw_text)`

## 2. Risk Triage — `RISK_PROMPT`

**Purpose:** given the extracted facts *and* the deterministic appetite-check result, produce a Low/Medium/High risk tier with rationale bullets and a list of data gaps. The prompt explicitly states the appetite result is authoritative and must not be overridden.

Same pattern as extraction: the criteria Claude is told to weigh are a named list, `RISK_CRITERIA` in `aura_engine.py`, rendered directly into the prompt (and served via `/api/reference` as "Risk Triage Criteria" in the UI):

| Criterion id | What it means |
|---|---|
| `LOSS_NARRATIVE_SEVERITY` | Nature, frequency, and cost of past claims described in the submission |
| `INDUSTRY_HAZARD` | Inherent hazard level of the business's industry or operations |
| `DATA_COMPLETENESS` | How much required information is missing, ambiguous, or unconfirmed |
| `THIRD_PARTY_EXPOSURE` | Reliance on subcontracted labor or third parties, where applicable |
| `BUSINESS_TENURE` | Years in business as a proxy for operational stability |
| `APPETITE_RESULT_FLOOR` | The eligibility verdict as an authoritative floor — Claude must not contradict it (enforced separately by `rationale_rules.py`) |

**Used by:** `assess_risk(extracted, appetite_result)`

## 3. Broker Response Drafting — `RESPONSE_PROMPT`

**Purpose:** draft a short, professional broker email whose tone and content depend on the eligibility outcome (decline / refer-to-senior-underwriter / proceed-to-quote), and that explicitly asks for missing information when data gaps were flagged.

**Used by:** `draft_response(extracted, appetite_result, risk_result)`

## Why the appetite check itself is NOT a prompt

Eligibility against the carrier's rules (`appetite_rules.json`) is implemented as deterministic Python logic in `check_appetite()`, not as an LLM call. Underwriting eligibility gates need to be consistent and auditable every time given the same inputs — that's a poor fit for LLM judgment, and a good fit for plain rule evaluation. Claude's role is everything around that gate: understanding messy input, and communicating the result well.

## The eligibility rule engine — `appetite_rules.json`

Rather than a fixed sequence of `if` statements, eligibility is a list of named rules in `appetite_rules.json`, each with an `id`, a `type` (`industry_exclusion`, `max_value`, `min_value`, `state_max_value`, `text_contains`, `missing_fields_threshold`), and a `severity` (`Refer` or `Ineligible`). `check_appetite()` in `aura_engine.py` evaluates every rule generically by dispatching on `type`, and returns each triggered rule's `id` alongside its message. This is what makes the verdict traceable: every reason shown in the UI names the exact rule that produced it, and the same rule ids are reused by the rationale-consistency checks below.

Current rules: `EXCLUDED_INDUSTRY`, `OVER_AUTHORITY_TIV`, `STATE_TIV_RESTRICTION`, `MIN_YEARS_IN_BUSINESS`, `MAX_LOSSES`, `MIN_ANNUAL_REVENUE`, `NON_RENEWED_FOR_CAUSE`, `MISSING_FIELDS`.

## Checking Claude's rationale — `rationale_rules.py`

This is a second, independent layer that runs *after* Claude produces its risk triage, checking the rationale itself rather than the verdict. It doesn't decide anything — it flags when Claude's narrative might be wrong, inconsistent, or ungrounded, which matters for any AI output an underwriter is expected to trust:

| Check | What it catches |
|---|---|
| `RATIONALE_MIN_LENGTH` | A rationale too thin to be useful |
| `TIER_CONSISTENT_WITH_INELIGIBLE` | An Ineligible account reported as anything but High risk |
| `TIER_NOT_LOW_ON_REFER` | A Refer account reported as Low risk |
| `DATA_GAPS_COVER_MISSING` | Extraction found missing fields but the rationale didn't flag them as data gaps |
| `RATIONALE_GROUNDED_FIGURES` | A dollar figure in the rationale that doesn't trace back to any extracted value (a lightweight hallucination check) |
| `RATIONALE_ADDRESSES_TRIGGERED_RULES` | A triggered appetite rule (e.g. `EXCLUDED_INDUSTRY`) that the rationale never actually discusses |

Results are returned as `rationale_checks` in the `/api/analyze` response and rendered in the UI as a pass/fail checklist (see `renderResults()` in `static/app.js`). This check runs identically in demo mode and live mode, since it's deterministic Python — it isn't cached alongside the demo responses.
