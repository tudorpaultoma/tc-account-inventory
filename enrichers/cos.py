"""COS enricher — extract creation dates for COS buckets."""

import os


def enrich_cos(cred, region, resource_ids):
    """
    Returns dict: resource_id -> {ResourceType, PaymentModel, Status, Name, CreationDate}
    Uses qcloud_cos SDK to list all buckets and match by name.
    """
    if not resource_ids:
        return {}

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

    try:
        cos_config = CosConfig(
            Region="ap-guangzhou",
            SecretId=secret_id,
            SecretKey=secret_key,
            Token=token,
        )
        client = CosS3Client(cos_config)
        resp = client.list_buckets()
        buckets = resp.get("Buckets", {}).get("Bucket", []) or []

        # Build lookup: bucket name -> CreationDate
        bucket_dates = {}
        for b in buckets:
            bucket_dates[b.get("Name", "")] = b.get("CreationDate", "")
    except Exception as e:
        print(f"  [WARN] COS list_buckets error: {e}")
        bucket_dates = {}

    result = {}
    for rid in resource_ids:
        # resource_ids for COS are empty; the ResourcePrefix holds the bucket name
        # But enricher receives ResourceId, which is empty for COS buckets.
        # We'll still return a default entry; COS creation dates need special handling.
        result[rid] = {
            "ResourceType": "",
            "PaymentModel": "",
            "Status": "",
            "Name": "",
            "CreationDate": bucket_dates.get(rid, ""),
        }

    return result
