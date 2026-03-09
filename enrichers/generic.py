"""Generic enricher — fallback when no specific enricher exists."""


def enrich_generic(cred, region, resource_ids):
    """Returns empty enrichment data — resource still appears in CSV with tags."""
    return {rid: {
        "ResourceType": "",
        "PaymentModel": "",
        "Status": "",
        "Name": "",
        "CreationDate": "",
    } for rid in resource_ids}
