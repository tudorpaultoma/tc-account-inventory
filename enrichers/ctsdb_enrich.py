"""CTSDB enricher — extract creation dates for CTSDB instances."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ctsdb.v20230202 import ctsdb_client, models


def enrich_ctsdb(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "ctsdb.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = ctsdb_client.CtsdbClient(cred, region, cp)

    result = {}

    try:
        req = models.DescribeClustersRequest()
        req.from_json_string(json.dumps({
            "PageNumber": 1,
            "PageSize": 100,
            "Filters": [{"Name": "cluster_id", "Values": resource_ids}],
        }))
        resp = client.DescribeClusters(req)
        for c in (resp.Clusters or []):
            result[c.ClusterID] = {
                "ResourceType": "instance",
                "PaymentModel": "",
                "Status": str(c.Status) if c.Status is not None else "",
                "Name": c.Name or "",
                "CreationDate": c.CreatedAt or "",
            }
    except TencentCloudSDKException as e:
        print(f"  [WARN] CTSDB DescribeClusters error: {e}")

    # Fill missing
    for rid in resource_ids:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
