"""TI-ONE enricher — SDK lacks training task APIs; all resources treated as ghost."""


def enrich_tione(cred, region, resource_ids):
    # No intl API available to verify training tasks — return empty dict
    # so all TI-ONE resources are filtered as ghosts by the ghost filter.
    if resource_ids:
        print(f"  [TI-ONE] 0 valid, {len(resource_ids)} ghost resources: {resource_ids[:5]}")
    return {}
