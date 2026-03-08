#!/usr/bin/env python3
"""
Tencent Cloud Account Inventory Generator (SCF Handler)

Discovers all resources across all regions using the Tag API (GetResources),
enriches them with service-specific details (type, payment model, status),
outputs a CSV inventory file and uploads it to COS.

SCF Entry point: inventory.main_handler
Version: 2.1.0 — single global discovery + dedup
"""

import os
import csv
import time
import json
from datetime import datetime, timezone
from collections import defaultdict
from io import StringIO

import config
from discovery import get_credentials, get_all_resources
from enrichers import get_enricher


CSV_HEADERS = [
    "Region",
    "ServiceType",
    "ResourcePrefix",
    "ResourceId",
    "ResourceName",
    "ResourceType",
    "PaymentModel",
    "Status",
    "Tags",
    "ResourceArn",
]


def deduplicate_resources(resources):
    """
    Remove duplicate resources that appear under multiple service types.
    Uses canonical service mapping to decide which entry to keep.
    Also filters out ghost resources (e.g. eks-* under cvm).
    """

    # Canonical service for resource ID prefixes — when the same resource ID
    # appears under multiple services, prefer the one listed here.
    CANONICAL_SERVICE = {
        "eip-": "cvm",
        "cls-": "tke",
        "sg-":  "cvm",
    }

    # Alias services to always drop in favor of the canonical
    ALIAS_SERVICES = {"ccs", "ci"}  # ccs → tke, ci → cos

    # Resource ID prefixes that are invalid under a given service type
    GHOST_PREFIXES = {
        "cvm": ["eks-"],  # EKS virtual nodes, not real CVM instances
    }

    # Step 1: Filter ghost resources
    filtered = []
    for r in resources:
        svc = r["ServiceType"]
        rid = r["ResourceId"]
        ghost_list = GHOST_PREFIXES.get(svc, [])
        if any(rid.startswith(prefix) for prefix in ghost_list):
            continue
        filtered.append(r)

    removed_ghosts = len(resources) - len(filtered)
    if removed_ghosts:
        print(f"    [DEDUP] Removed {removed_ghosts} ghost resources (e.g. eks-* under cvm)")

    # Step 2: Drop alias services if canonical entry exists
    # Build lookup: (region, resource_id) -> list of entries
    # Use ResourcePrefix as fallback key when ResourceId is empty (e.g. COS buckets)
    seen = defaultdict(list)
    for r in filtered:
        rid = r["ResourceId"] or r["ResourcePrefix"]
        key = (r["Region"], rid)
        seen[key].append(r)

    deduped = []
    for key, entries in seen.items():
        if len(entries) == 1:
            deduped.append(entries[0])
            continue

        # Multiple entries for the same resource ID + region
        rid = key[1]

        # Determine canonical service from prefix mapping
        canonical = None
        for prefix, svc in CANONICAL_SERVICE.items():
            if rid.startswith(prefix):
                canonical = svc
                break

        kept = None
        for e in entries:
            svc = e["ServiceType"]
            if svc in ALIAS_SERVICES:
                continue
            if canonical and svc == canonical:
                kept = e
                break

        # If no canonical match, keep the first non-alias entry
        if kept is None:
            for e in entries:
                if e["ServiceType"] not in ALIAS_SERVICES:
                    kept = e
                    break

        if kept is None:
            kept = entries[0]

        dropped = [e["ServiceType"] for e in entries if e is not kept]
        print(f"    [DEDUP] {rid}: kept {kept['ServiceType']}, dropped {dropped}")
        deduped.append(kept)

    return deduped


def generate_inventory(cred):
    """Core logic: discover, enrich, return CSV string + stats."""

    # 1. Discover all resources via Tag GetResources (single global call)
    # The Tag API returns all resources across all regions regardless of
    # the region parameter, so a single call is sufficient. The region for
    # each resource is extracted from the six-segment ARN.
    print("[*] Discovering all resources (global Tag API call)...")
    all_resources = get_all_resources(cred, region=None)
    print(f"    Found {len(all_resources)} resources")

    # 2. Deduplicate — same ResourceId may appear under multiple service types
    all_resources = deduplicate_resources(all_resources)
    print(f"[*] After dedup: {len(all_resources)} unique resources")

    # 3. Group by (service_type, region) for batch enrichment
    grouped = defaultdict(list)
    for r in all_resources:
        key = (r["ServiceType"], r["Region"])
        grouped[key].append(r)

    # 4. Enrich each group
    print("[*] Enriching resources with service details...")
    enrichment_cache = {}

    for (service_type, region), items in grouped.items():
        resource_ids = [r["ResourceId"] for r in items if r["ResourceId"]]
        if not resource_ids:
            continue

        enricher = get_enricher(service_type)
        print(f"    Enriching {len(resource_ids)} {service_type} resources in {region or 'global'}...")

        try:
            enriched = enricher(cred, region, resource_ids)
            for rid, data in enriched.items():
                enrichment_cache[(service_type, region, rid)] = data
        except Exception as e:
            print(f"    [WARN] Enrichment failed for {service_type}/{region}: {e}")

        time.sleep(config.API_SLEEP)

    # 4b. Filter GAAP ghosts — resources not found by the GAAP API
    VALIDATED_SERVICES = {"gaap"}
    before = len(all_resources)
    all_resources = [
        r for r in all_resources
        if r["ServiceType"] not in VALIDATED_SERVICES
        or (r["ServiceType"], r["Region"], r["ResourceId"]) in enrichment_cache
    ]
    ghost_count = before - len(all_resources)
    if ghost_count:
        print(f"    [GHOST] Removed {ghost_count} ghost GAAP resources (not found in API)")

    # 5. Build CSV in memory
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
    writer.writeheader()

    for r in all_resources:
        key = (r["ServiceType"], r["Region"], r["ResourceId"])
        enriched = enrichment_cache.get(key, {})
        tags_str = "; ".join(f"{k}={v}" for k, v in r["Tags"].items()) if r["Tags"] else ""

        writer.writerow({
            "Region": r["Region"],
            "ServiceType": r["ServiceType"],
            "ResourcePrefix": r["ResourcePrefix"],
            "ResourceId": r["ResourceId"],
            "ResourceName": enriched.get("Name", ""),
            "ResourceType": enriched.get("ResourceType", ""),
            "PaymentModel": enriched.get("PaymentModel", ""),
            "Status": enriched.get("Status", ""),
            "Tags": tags_str,
            "ResourceArn": r["ResourceArn"],
        })

    csv_content = output.getvalue()
    output.close()

    return csv_content, len(all_resources)


def upload_to_cos(csv_content):
    """Upload CSV to COS bucket using cos-python-sdk-v5."""
    if not config.COS_BUCKET:
        print("[WARN] COS_BUCKET not set, skipping upload. Writing to /tmp only.")
        return None

    from qcloud_cos import CosConfig, CosS3Client

    secret_id = (
        os.environ.get("TENCENTCLOUD_SECRETID", "")
        or os.environ.get("TENCENTCLOUD_SECRET_ID", "")
    )
    secret_key = (
        os.environ.get("TENCENTCLOUD_SECRETKEY", "")
        or os.environ.get("TENCENTCLOUD_SECRET_KEY", "")
    )
    token = (
        os.environ.get("TENCENTCLOUD_SESSIONTOKEN", "")
        or os.environ.get("TENCENTCLOUD_SESSION_TOKEN", "")
    )

    cos_config = CosConfig(
        Region=config.COS_REGION,
        SecretId=secret_id,
        SecretKey=secret_key,
        Token=token,
    )
    cos_client = CosS3Client(cos_config)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    cos_key = f"{config.COS_KEY_PREFIX}inventory_{timestamp}.csv"

    tmp_path = config.OUTPUT_FILE
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    with open(tmp_path, "rb") as fp:
        cos_client.put_object(
            Bucket=config.COS_BUCKET,
            Body=fp,
            Key=cos_key,
            ContentType="text/csv",
        )

    print(f"[+] Uploaded to cos://{config.COS_BUCKET}/{cos_key} ({len(csv_content)} bytes)")
    return cos_key


def main_handler(event, context):
    """SCF entry point."""
    print("[*] TC Account Inventory — SCF invocation started (v2.1.0)")
    start = time.time()

    try:
        cred = get_credentials()

        csv_content, total = generate_inventory(cred)

        # Upload to COS (also writes to /tmp)
        cos_key = upload_to_cos(csv_content)

        # If COS upload was skipped, ensure local write
        if cos_key is None:
            with open(config.OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(csv_content)

        elapsed = round(time.time() - start, 1)
        result = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Inventory generated successfully",
                "total_resources": total,
                "elapsed_seconds": elapsed,
                "cos_key": cos_key,
                "local_path": config.OUTPUT_FILE,
            })
        }
        print(f"[+] Done in {elapsed}s — {total} resources inventoried")
        return result

    except Exception as e:
        print(f"[ERROR] {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# Allow local execution for testing
if __name__ == "__main__":
    result = main_handler({}, {})
    print(json.dumps(json.loads(result["body"]), indent=2))
