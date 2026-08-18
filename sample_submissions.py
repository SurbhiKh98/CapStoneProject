"""Synthetic broker submissions used to demo the AURA pipeline end-to-end.

These are fictional accounts written to exercise four distinct paths through
the eligibility/risk engine: clean accept, borderline refer, hard decline,
and an incomplete submission that should trigger data-gap flags.
"""

SAMPLE_SUBMISSIONS = {
    "1. Clean retail account (expect: Eligible / Low risk)": """\
From: Dana Whitfield, Whitfield & Cross Insurance Brokers
Subject: New Business Submission - Maple & Vine Kitchen Supply LLC

Please find submission details for a new commercial package quote:

Named Insured: Maple & Vine Kitchen Supply LLC
Business Description: Retail store selling kitchenware, small appliances, and
cookware. Single storefront location, no on-site food preparation.
Years in Business: 7
State/Location: 214 Birch St, Madison, WI
Requested Coverage: General Liability + Commercial Property
Total Insured Value (TIV): $1,200,000 (building contents + business personal property)
Annual Revenue: $2.1M
Loss History (last 3 years): No claims filed.
Prior Carrier: Hanover Insurance (non-renewed due to carrier exiting the state, not for cause)
Requested Effective Date: 2026-09-01
""",
    "2. Borderline contractor (expect: Refer / Medium risk)": """\
From: Marcus Ibe, Ibe Risk Partners
Subject: Submission - Coastal Roofing & Exteriors Inc.

Submitting for quote consideration:

Named Insured: Coastal Roofing & Exteriors Inc.
Business Description: Residential and light commercial roofing contractor,
also performs occasional gutter and siding installation. Uses subcontracted
labor for approximately 40% of jobs.
Years in Business: 3
State/Location: Tampa, FL
Requested Coverage: General Liability + Commercial Property (owned warehouse)
Total Insured Value (TIV): $6,200,000
Annual Revenue: $4.8M
Loss History (last 3 years): One general liability claim in 2024 - $85,000
paid, fall-from-height injury during a residential job. No other claims.
Prior Carrier: Declined renewal after the claim.
Requested Effective Date: 2026-09-15
""",
    "3. Restricted risk - over authority (expect: Ineligible or Refer / High risk)": """\
From: Priya Anand, Anand & Fields Brokerage
Subject: New Submission - Summit Peak Fireworks Distribution LLC

New business submission:

Named Insured: Summit Peak Fireworks Distribution LLC
Business Description: Wholesale distribution of consumer fireworks to retail
stands, seasonal storage of product in a leased warehouse.
Years in Business: 5
State/Location: Reno, NV
Requested Coverage: General Liability + Property + Products Liability
Total Insured Value (TIV): $18,500,000
Annual Revenue: $9.3M
Loss History (last 3 years): Two claims - a 2023 warehouse fire ($1.2M paid)
and a 2022 products liability claim ($340,000 paid).
Prior Carrier: Non-renewed for cause (loss history).
Requested Effective Date: 2026-08-25
""",
    "4. Incomplete submission (expect: data-gap flags, cannot fully triage)": """\
From: Jordan Lee, Lee & Park Insurance Services
Subject: Quick submission - need fast turnaround

Hi, client needs coverage ASAP, here's what I have so far:

Named Insured: Redline Auto Detailing
Business Description: Mobile auto detailing service.
Requested Coverage: General Liability
State/Location: Ohio (exact city TBD, client is relocating)
Loss History: Client says "no major issues" but no loss runs provided yet.
TIV / Revenue: Not yet provided by client.
Years in Business: Unknown - client mentioned "a few years."
Requested Effective Date: ASAP
""",
}
