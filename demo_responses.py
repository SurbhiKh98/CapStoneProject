"""Pre-generated Claude outputs for the 4 built-in sample submissions.

These are genuine Claude reasoning outputs for the extraction/risk/drafting
prompts in aura_engine.py (produced once, offline, following the exact same
prompts documented in PROMPTS.md) - captured here so the app has a working
demo mode when no ANTHROPIC_API_KEY is configured. When a key IS set,
server.py ignores this file entirely and calls the live Anthropic API for
every request instead.

Keys match the keys in sample_submissions.SAMPLE_SUBMISSIONS exactly.
"""

DEMO_RESPONSES = {
    "1. Clean retail account (expect: Eligible / Low risk)": {
        "extracted": {
            "named_insured": "Maple & Vine Kitchen Supply LLC",
            "industry_description": "Retail store selling kitchenware, small appliances, and cookware; no on-site food preparation",
            "state": "WI",
            "years_in_business": 7,
            "tiv": 1200000,
            "annual_revenue": 2100000,
            "coverage_requested": ["General Liability", "Commercial Property"],
            "losses_last_3_years": 0,
            "loss_narrative": "No claims filed in the last 3 years.",
            "prior_carrier_status": "Non-renewed by Hanover Insurance due to carrier exiting the state, not for cause",
            "requested_effective_date": "2026-09-01",
            "missing_fields": [],
        },
        "risk": {
            "risk_tier": "Low",
            "rationale": [
                "Clean loss history with zero claims in the past three years",
                "Established business with 7 years of operating history",
                "Low-hazard retail class with no on-site food preparation or heavy equipment",
                "Prior non-renewal was due to carrier market exit, not underwriting concerns",
            ],
            "data_gaps": [],
        },
        "email": (
            "Hi there,\n\n"
            "Thank you for the submission on Maple & Vine Kitchen Supply LLC. Based on our initial "
            "review, this account fits well within our underwriting appetite - a well-established "
            "retail operation with a clean loss history over the past three years.\n\n"
            "We're moving this submission into our quoting process now and will follow up shortly "
            "with terms for the General Liability and Commercial Property coverage requested, "
            "targeting your September 1 effective date.\n\n"
            "Thanks for bringing us this opportunity - we look forward to working together on this one.\n\n"
            "Best regards,\nAURA Underwriting Team"
        ),
    },
    "2. Borderline contractor (expect: Refer / Medium risk)": {
        "extracted": {
            "named_insured": "Coastal Roofing & Exteriors Inc.",
            "industry_description": "Residential and light commercial roofing contractor; also performs gutter and siding installation; uses subcontracted labor for approximately 40% of jobs",
            "state": "FL",
            "years_in_business": 3,
            "tiv": 6200000,
            "annual_revenue": 4800000,
            "coverage_requested": ["General Liability", "Commercial Property"],
            "losses_last_3_years": 1,
            "loss_narrative": "2024 general liability claim, $85,000 paid, fall-from-height injury during a residential job.",
            "prior_carrier_status": "Declined renewal after the claim",
            "requested_effective_date": "2026-09-15",
            "missing_fields": [],
        },
        "risk": {
            "risk_tier": "Medium",
            "rationale": [
                "Property TIV exceeds the state's coastal wind exposure threshold, appropriately triggering senior underwriter referral",
                "One prior liability claim (fall-from-height, $85K) indicates a jobsite safety exposure common to roofing risks",
                "Heavy reliance on subcontracted labor (40% of jobs) adds exposure that depends on subcontractor insurance and vetting practices",
                "Relatively young business (3 years) with limited loss history to fully validate risk quality",
            ],
            "data_gaps": [
                "Subcontractor certificates of insurance and vetting practices not provided",
                "Details on safety program or fall-protection protocols adopted since the 2024 claim not provided",
            ],
        },
        "email": (
            "Hi there,\n\n"
            "Thank you for the submission on Coastal Roofing & Exteriors Inc. Given the property's "
            "total insured value in a coastal wind-exposed area, this submission is being referred to "
            "one of our senior underwriters for a closer review alongside the loss history on file.\n\n"
            "To help move things along, could you also provide the subcontractor certificates of "
            "insurance/vetting practices and any details on safety or fall-protection protocols put in "
            "place since the 2024 claim? That information will help us finalize our assessment.\n\n"
            "We'll be back in touch as soon as the senior underwriter review is complete.\n\n"
            "Best regards,\nAURA Underwriting Team"
        ),
    },
    "3. Restricted risk - over authority (expect: Ineligible or Refer / High risk)": {
        "extracted": {
            "named_insured": "Summit Peak Fireworks Distribution LLC",
            "industry_description": "Wholesale distribution of consumer fireworks to retail stands; seasonal storage of product in a leased warehouse",
            "state": "NV",
            "years_in_business": 5,
            "tiv": 18500000,
            "annual_revenue": 9300000,
            "coverage_requested": ["General Liability", "Property", "Products Liability"],
            "losses_last_3_years": 2,
            "loss_narrative": "2023 warehouse fire, $1.2M paid; 2022 products liability claim, $340,000 paid.",
            "prior_carrier_status": "Non-renewed for cause (loss history)",
            "requested_effective_date": "2026-08-25",
            "missing_fields": [],
        },
        "risk": {
            "risk_tier": "High",
            "rationale": [
                "Industry falls within an explicitly excluded class (fireworks distribution/storage) due to explosive and fire hazard",
                "Two losses in the past three years, including a $1.2M warehouse fire, indicate significant hazard control weaknesses",
                "TIV of $18.5M also exceeds binding authority, compounding the exposure",
                "Non-renewal for cause by the prior carrier confirms an adverse loss trend",
            ],
            "data_gaps": [],
        },
        "email": (
            "Hi there,\n\n"
            "Thank you for thinking of us for Summit Peak Fireworks Distribution LLC. After reviewing "
            "the submission, this risk falls outside our current underwriting appetite, and we're not "
            "able to offer terms at this time.\n\n"
            "We appreciate you bringing the opportunity to us and wish you success in placing this "
            "coverage elsewhere.\n\n"
            "Best regards,\nAURA Underwriting Team"
        ),
    },
    "4. Incomplete submission (expect: data-gap flags, cannot fully triage)": {
        "extracted": {
            "named_insured": "Redline Auto Detailing",
            "industry_description": "Mobile auto detailing service",
            "state": "OH",
            "years_in_business": None,
            "tiv": None,
            "annual_revenue": None,
            "coverage_requested": ["General Liability"],
            "losses_last_3_years": None,
            "loss_narrative": 'Broker states client reports "no major issues" but no loss runs have been provided to confirm.',
            "prior_carrier_status": None,
            "requested_effective_date": "ASAP",
            "missing_fields": [
                "years_in_business",
                "tiv",
                "annual_revenue",
                "losses_last_3_years",
                "prior_carrier_status",
            ],
        },
        "risk": {
            "risk_tier": "Medium",
            "rationale": [
                "Insufficient data to properly assess risk - financial size, tenure, and loss history are all unconfirmed",
                "Mobile auto detailing is generally a low-to-moderate hazard class, but auto liability and care-custody-control exposures need TIV/revenue context to price appropriately",
                'Broker\'s informal assurance of "no major issues" is not a substitute for actual loss runs',
            ],
            "data_gaps": [
                "Confirmed years in business",
                "Total insured value / business personal property value",
                "Annual revenue",
                "Signed loss runs for the last 3 years",
                "Prior carrier name and renewal status",
                "Specific city/location within Ohio",
            ],
        },
        "email": (
            "Hi there,\n\n"
            "Thanks for the quick submission on Redline Auto Detailing. To move this forward, we'll "
            "need a bit more information before we can complete our review: confirmed years in "
            "business, total insured value or business personal property value, annual revenue, "
            "signed loss runs for the past three years, prior carrier name/renewal status, and the "
            "specific city within Ohio where the business operates.\n\n"
            "Once we have those details, we can complete our assessment quickly. We understand the "
            "effective date is time-sensitive and will prioritize this as soon as the information "
            "comes in.\n\n"
            "Best regards,\nAURA Underwriting Team"
        ),
    },
}
