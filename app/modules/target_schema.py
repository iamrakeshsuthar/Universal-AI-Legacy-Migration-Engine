"""
target_schema.py
Default modern cloud-native PAS target schema definition.
"""

DEFAULT_TARGET_SCHEMA = [
    {"field": "policyId", "type": "string", "description": "Unique policy identifier"},
    {"field": "policyHolder.fullName", "type": "string", "description": "Full legal name of policyholder"},
    {"field": "vehicle.model", "type": "string", "description": "Vehicle make/model"},
    {"field": "coverage.amount", "type": "decimal", "description": "Total coverage amount"},
    {"field": "premium.baseAmount", "type": "decimal", "description": "Base premium amount"},
    {"field": "status", "type": "string", "description": "Policy status"},
    {"field": "expirationDate", "type": "date(ISO-8601)", "description": "Expiration date"},
    {"field": "claims[].claimId", "type": "string", "description": "Claim ID"},
    {"field": "claims[].amount", "type": "decimal", "description": "Claim amount"},
    {"field": "metadata.sourceSystem", "type": "string", "description": "Source identifier"}
]
