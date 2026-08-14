"""
target_schema.py
Pre-built target PAS templates.
"""

DEFAULT_TARGET_SCHEMA = [
    {"field": "policyId", "type": "string", "description": "Unique policy identifier"},
    {"field": "policyHolder.fullName", "type": "string", "description": "Full legal name of the policyholder"},
    {"field": "coverage.amount", "type": "decimal", "description": "Total coverage amount"},
    {"field": "premium.baseAmount", "type": "decimal", "description": "Base premium before surcharges"},
    {"field": "status", "type": "string", "description": "Current policy status"},
]

GUIDEWIRE_TEMPLATE = [
    {"field": "PolicyPeriod.PublicID", "type": "string", "description": "GW internal ID"},
    {"field": "PolicyPeriod.PrimaryNamedInsured", "type": "string", "description": "Account holder"},
    {"field": "PolicyPeriod.TotalPremiumRPT", "type": "decimal", "description": "Total Premium"},
]

DUCK_CREEK_TEMPLATE = [
    {"field": "Policy.Reference", "type": "string", "description": "DC Policy Reference"},
    {"field": "Party.Name", "type": "string", "description": "Party Name"},
    {"field": "Line.Premium", "type": "decimal", "description": "Line Premium"},
]

SCHEMA_TEMPLATES = {
    "Default Modern PAS": DEFAULT_TARGET_SCHEMA,
    "Guidewire PolicyCenter": GUIDEWIRE_TEMPLATE,
    "Duck Creek PAS": DUCK_CREEK_TEMPLATE
}
