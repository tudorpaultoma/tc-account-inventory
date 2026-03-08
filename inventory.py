#!/usr/bin/env python3
"""
Tencent Cloud Account Inventory Generator (SCF Handler)

Discovers all resources across all regions using the Tag API (GetResources),
enriches them with service-specific details (type, payment model, status),
outputs a CSV inventory file and uploads it to COS.

SCF Entry point: inventory.main_handler
"""

import os
import csv
import time
import json
from datetime import datetime, timezone
from collections import defaultdict
from io import StringIO

import config
from discovery import get_credentials, get_regions, get_all_resources
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


def generate_inventory(cred):
    """Core logic: discover, enrich, return CSV string + stats."""

    # 1. Get all regions
    print("[*] Fetching regions...")
    regions = get_regions(cred)
    print(f"    Found {len(regions)} regions")

    # 2. Discover resources per region via Tag GetResources
    all_resources = []
    for region in regions:
        print(f"[*] Scanning region: {region}")
        resources = get_all_resources(cred, region)
        print(f"    Found {len(resources)} resources")
        all_resources.extend(resources)
        time.sleep(config.API_SLEEP)

    # Also scan global (no region) for services like COS, CCN, PrivateDNS
    print("[*] Scanning global resources (no region)...")
    global_resources = get_all_resources(cred, region=None)
    print(f"    Found {len(global_resources)} global resources")
    all_resources.extend(global_resources)

    print(f"\n[*] Total discovered: {len(all_resources)} resources")

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
    print("[*] TC Account Inventory — SCF invocation started")
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
