"""TI-ONE enricher — SDK lacks training task APIs; keep resources as-is."""


def enrich_tione(cred, region, resource_ids):
    result = {}
    for rid in resource_ids:
        result[rid] = {
            "ResourceType": "",
            "PaymentModel": "",
            "Status": "",
            "Name": "",
            "CreationDate": "",
        }
    return result
